#!/usr/bin/env python3
"""
USB Site Lock - A digital wellbeing tool that blocks distracting websites
and only unblocks them when a specific USB drive is inserted.

Requirements:
    - Python 3.6+
    - pyudev (pip install pyudev)
    - Root/sudo access to modify /etc/hosts

Usage:
    sudo python3 usb_site_lock.py

Author: Benjamin Mast
"""

import os
import sys
import signal
import subprocess
import time
from pathlib import Path


# CONFIGURATION - MODIFY THESE VALUES
#-------------------------------------

# Your USB drive's UUID - find it with: lsblk -f
# or: sudo blkid | grep -i uuid
USB_UUID = "YOUR-USB-UUID-HERE"

# Websites to block (add more as needed)
BLOCKED_SITES = [
    "youtube.com",
    "www.youtube.com",
    "twitter.com",
    "www.twitter.com",
    "x.com",
    "www.x.com",
]

# Redirect IP (localhost)
REDIRECT_IP = "127.0.0.1"

# Marker comments for identifying our entries in /etc/hosts
MARKER_START = "# >>> USB_SITE_LOCK_START <<<"
MARKER_END = "# >>> USB_SITE_LOCK_END <<<"

# Paths
HOSTS_FILE = Path("/etc/hosts")
HOSTS_BACKUP = Path("/etc/hosts.usb_site_lock.backup")

# DEPENDENCY CHECK
#-------------------------------------

try:
    import pyudev
except ImportError:
    print("Error: pyudev is not installed.")
    print("Install it with: pip install pyudev")
    sys.exit(1)

# NOTIFICATION FUNCTIONS
#-------------------------------------

def send_notification(title: str, message: str, icon: str = "dialog-information"):
    """Send a desktop notification using notify-send."""
    try:
        # Get the actual user (not root) for proper notification delivery
        user = os.environ.get("SUDO_USER", "")
        
        if user and user != "root":
            # Find the user's UID for DBUS path
            result = subprocess.run(
                ["id", "-u", user],
                capture_output=True,
                text=True
            )
            uid = result.stdout.strip()
            
            # Build the command to run as the user with proper DBUS
            dbus_addr = f"unix:path=/run/user/{uid}/bus"
            cmd = f'DBUS_SESSION_BUS_ADDRESS="{dbus_addr}" notify-send -i "{icon}" "{title}" "{message}"'
            
            subprocess.Popen(
                ["su", user, "-c", cmd],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
        else:
            subprocess.Popen(
                ["notify-send", "-i", icon, title, message],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )
    except Exception as e:
        print(f"[Notification failed: {e}]")

# HOSTS FILE MANAGEMENT
#-------------------------------------

def read_hosts_file() -> str:
    """Read the current contents of /etc/hosts."""
    try:
        return HOSTS_FILE.read_text()
    except PermissionError:
        print("Error: Cannot read /etc/hosts. Run with sudo.")
        sys.exit(1)

def write_hosts_file(content: str):
    """Write content to /etc/hosts."""
    try:
        HOSTS_FILE.write_text(content)
    except PermissionError:
        print("Error: Cannot write to /etc/hosts. Run with sudo.")
        sys.exit(1)

def create_backup():
    """Create a backup of the original hosts file if one doesn't exist."""
    if not HOSTS_BACKUP.exists():
        content = read_hosts_file()
        # Remove any existing USB_SITE_LOCK entries before backing up
        clean_content = remove_block_entries(content)
        HOSTS_BACKUP.write_text(clean_content)
        print(f"✓ Backup created: {HOSTS_BACKUP}")

def remove_block_entries(content: str) -> str:
    """Remove our blocking entries from hosts content."""
    lines = content.split('\n')
    result = []
    in_block = False
    
    for line in lines:
        if MARKER_START in line:
            in_block = True
            continue
        elif MARKER_END in line:
            in_block = False
            continue
        elif not in_block:
            result.append(line)
    
    # Clean up multiple blank lines at end
    while result and result[-1] == '':
        result.pop()
    result.append('')  # Ensure single trailing newline
    
    return '\n'.join(result)

def add_block_entries(content: str) -> str:
    """Add our blocking entries to hosts content."""
    # First remove any existing entries
    content = remove_block_entries(content)
    
    # Build the block entries
    block_lines = [MARKER_START]
    for site in BLOCKED_SITES:
        block_lines.append(f"{REDIRECT_IP}\t{site}")
    block_lines.append(MARKER_END)
    
    # Ensure content ends with newline before adding our block
    if not content.endswith('\n'):
        content += '\n'
    
    return content + '\n'.join(block_lines) + '\n'

def is_blocked() -> bool:
    """Check if sites are currently blocked."""
    content = read_hosts_file()
    return MARKER_START in content

def block_sites():
    """Block the configured websites."""
    content = read_hosts_file()
    
    if MARKER_START in content:
        print("  (Already blocked)")
        return  # Already blocked
    
    new_content = add_block_entries(content)
    write_hosts_file(new_content)
    flush_dns_cache()
    
    # Verify the write worked
    verify_content = read_hosts_file()
    if MARKER_START in verify_content:
        print("🔒 Sites BLOCKED (verified)")
    else:
        print("⚠️  Sites BLOCKED but verification failed!")
    
    send_notification(
        "🔒 Sites Blocked",
        "YouTube and X are now blocked. Insert your USB key to unblock.",
        "security-high"
    )

def unblock_sites():
    """Unblock the configured websites."""
    content = read_hosts_file()
    
    if MARKER_START not in content:
        print("  (Already unblocked)")
        return  # Already unblocked
    
    new_content = remove_block_entries(content)
    write_hosts_file(new_content)
    flush_dns_cache()
    
    # Verify the write worked
    verify_content = read_hosts_file()
    if MARKER_START not in verify_content:
        print("🔓 Sites UNBLOCKED (verified)")
    else:
        print("⚠️  Sites UNBLOCKED but verification failed!")
    
    send_notification(
        "🔓 USB Key Accepted",
        "Sites are now unblocked. Remove USB to block again.",
        "security-low"
    )

def flush_dns_cache():
    """Flush DNS cache to make changes take effect immediately."""
    try:
        # Try systemd-resolved (common on Fedora with KDE)
        subprocess.run(
            ["systemctl", "restart", "systemd-resolved"],
            capture_output=True,
            timeout=10
        )
    except Exception:
        pass
    
    try:
        # Also try resolvectl
        subprocess.run(
            ["resolvectl", "flush-caches"],
            capture_output=True,
            timeout=10
        )
    except Exception:
        pass

# USB DETECTION
#-------------------------------------

def get_usb_uuids() -> set:
    """Get all currently connected USB drive UUIDs."""
    uuids = set()
    
    try:
        # Use lsblk to get UUIDs
        result = subprocess.run(
            ["lsblk", "-o", "UUID", "-n", "-l"],
            capture_output=True,
            text=True,
            timeout=10
        )
        for line in result.stdout.strip().split('\n'):
            uuid = line.strip()
            if uuid:
                uuids.add(uuid)
    except Exception as e:
        print(f"Warning: Could not get UUIDs via lsblk: {e}")
    
    try:
        # Also check /dev/disk/by-uuid directly
        by_uuid = Path("/dev/disk/by-uuid")
        if by_uuid.exists():
            for entry in by_uuid.iterdir():
                uuids.add(entry.name)
    except Exception as e:
        print(f"Warning: Could not read /dev/disk/by-uuid: {e}")
    
    return uuids

def is_key_usb_present() -> bool:
    """Check if the configured USB key is currently connected."""
    return USB_UUID in get_usb_uuids()

def monitor_usb_events():
    """Monitor USB events using pyudev."""
    context = pyudev.Context()
    monitor = pyudev.Monitor.from_netlink(context)
    monitor.filter_by(subsystem='block')
    
    print(f"\n👁️  Monitoring for USB key: {USB_UUID}")
    print("   (Press Ctrl+C to stop)\n")
    
    # Check initial state
    if is_key_usb_present():
        print("✓ USB key detected on startup")
        unblock_sites()
    else:
        print("✗ USB key not present - blocking sites")
        block_sites()
    
    # Monitor for changes
    for device in iter(monitor.poll, None):
        if device.action in ('add', 'remove'):
            # Small delay to let the system settle
            time.sleep(0.5)
            
            if is_key_usb_present():
                unblock_sites()
            else:
                block_sites()

# SIGNAL HANDLERS
#-------------------------------------

def cleanup_handler(signum, frame):
    """Handle shutdown signals gracefully."""
    print("\n\n⚠️  Shutting down...")
    print("   Sites will remain in their current state.")
    print(f"   Run 'sudo {sys.argv[0]}' to restart monitoring.")
    print(f"   Run 'sudo bash emergency_reset.sh' to force unblock.\n")
    sys.exit(0)

# MAIN
#-------------------------------------

def print_banner():
    """Print startup banner."""
    print("""
╔═══════════════════════════════════════════════════════════════╗
║              USB Site Lock - Digital Wellbeing Tool           ║
╠═══════════════════════════════════════════════════════════════╣
║  Block distracting sites until you insert your USB key        ║
╚═══════════════════════════════════════════════════════════════╝
""")

def print_config():
    """Print current configuration."""
    print("Configuration:")
    print(f"  USB UUID: {USB_UUID}")
    print(f"  Blocked sites: {', '.join(BLOCKED_SITES)}")
    print(f"  Hosts file: {HOSTS_FILE}")
    print(f"  Backup file: {HOSTS_BACKUP}")

def main():
    print_banner()
    
    # Check for root privileges
    if os.geteuid() != 0:
        print("Error: This script requires root privileges.")
        print("Please run with: sudo python3 usb_site_lock.py")
        sys.exit(1)
    
    # Check if UUID is configured
    if USB_UUID == "YOUR-USB-UUID-HERE":
        print("Error: USB UUID not configured!")
        print("\nTo find your USB drive's UUID:")
        print("  1. Insert your USB drive")
        print("  2. Run: lsblk -f")
        print("  3. Find your USB drive and copy its UUID")
        print("  4. Edit this script and set USB_UUID to your UUID")
        print("\nAlternatively, run: sudo blkid | grep -i usb")
        sys.exit(1)
    
    print_config()
    
    # Create backup of hosts file
    create_backup()
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, cleanup_handler)
    signal.signal(signal.SIGTERM, cleanup_handler)
    
    # Start monitoring
    try:
        monitor_usb_events()
    except KeyboardInterrupt:
        cleanup_handler(None, None)
    except Exception as e:
        print(f"\nError: {e}")
        print("Sites may be in an inconsistent state.")
        print("Run emergency_reset.sh to restore defaults.")
        sys.exit(1)

if __name__ == "__main__":
    main()


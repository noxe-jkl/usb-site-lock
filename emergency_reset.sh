#!/bin/bash
#
# Emergency Reset Script for USB Site Lock
# =========================================
# This script removes all blocking entries added by usb_site_lock.py
# and restores your /etc/hosts file to a clean state.
#
# Usage: sudo bash emergency_reset.sh
#

set -e

HOSTS_FILE="/etc/hosts"
BACKUP_FILE="/etc/hosts.usb_site_lock.backup"
MARKER_START="# >>> USB_SITE_LOCK_START <<<"
MARKER_END="# >>> USB_SITE_LOCK_END <<<"

echo "╔═══════════════════════════════════════╗"
echo "║     USB Site Lock Emergency Reset     ║"
echo "╚═══════════════════════════════════════╝"
echo

# Check for root privileges
if [ "$EUID" -ne 0 ]; then
    echo "Error: This script requires root privileges."
    echo "Please run with: sudo bash emergency_reset.sh"
    exit 1
fi

# Show current blocking status
if grep -q "$MARKER_START" "$HOSTS_FILE" 2>/dev/null; then
    echo "Current status: Sites are BLOCKED"
else
    echo "Current status: Sites are NOT blocked"
    echo "No action needed."
    exit 0
fi

echo

# Option 1: Restore from backup if it exists
if [ -f "$BACKUP_FILE" ]; then
    echo "Backup file found: $BACKUP_FILE"
    read -p "Restore from backup? (y/n): " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        cp "$BACKUP_FILE" "$HOSTS_FILE"
        echo "✓ Restored /etc/hosts from backup"
        echo "✓ Sites are now UNBLOCKED"
        
        # Flush DNS cache
        systemctl restart systemd-resolved 2>/dev/null || true
        resolvectl flush-caches 2>/dev/null || true
        
        exit 0
    fi
fi

# Option 2: Remove only our entries (preserving other customizations)
echo "Removing USB Site Lock entries from /etc/hosts..."

# Use sed to remove everything between (and including) our markers
sed -i "/$MARKER_START/,/$MARKER_END/d" "$HOSTS_FILE"

echo "✓ Removed blocking entries"
echo "✓ Sites are now UNBLOCKED"

# Flush DNS cache
echo "Flushing DNS cache..."
systemctl restart systemd-resolved 2>/dev/null || true
resolvectl flush-caches 2>/dev/null || true

echo
echo "Done! Your /etc/hosts file has been cleaned."
echo
echo "If you want to see the current state:"
echo "  cat /etc/hosts"
echo
echo "If sites are still blocked, try:"
echo "  1. Close and reopen your browser"
echo "  2. Clear your browser's DNS cache (chrome://net-internals/#dns in Chrome)"

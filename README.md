# USB Site Lock

This is a small project I built for myself to deal with distractions in a way that *actually sticks*.

**USB Site Lock** blocks selected websites at the system level and only unlocks them when a specific USB drive is plugged in. No apps, no browser extensions, no accounts — just a physical key you have to consciously insert.

---

## Why I made this

I noticed that most blockers don't work for me because they’re too easy to bypass.
So I tried flipping the problem aroun. What if access required a *physical action*?

The result is a simple script that treats a USB drive like a permission key.
If the key isn’t present, distracting sites are blocked. If it is, they’re allowed.

It’s intentionally boring and local — which is exactly the point.

---

## How it works (briefly)

* Watches for USB insert/remove events
* Modifies `/etc/hosts` to block or unblock sites
* Sends a desktop notification when the state changes
* Creates a backup of your hosts file on first run

That’s it. No background services, no cloud, no UI.

---

## What systems it works on

This should on most **modern desktop Linux distros**, including:

* Ubuntu / Mint / Pop!_OS
* Debian
* Fedora
* Arch / Manjaro
* openSUSE

If your system has:

* systemd + udev
* Python 3.6+
* a writable `/etc/hosts`

…it should be fine. (I only tested it on my own machine, which runs Fedora KDE Plasma)

(It won’t work as-is on NixOS or immutable systems.)

---

## Setup

1. Install dependency:

   ```bash
   pip install pyudev
   ```

2. Find your USB UUID:

   ```bash
   lsblk -f
   ```

3. Edit `usb_site_lock.py` and set:

   ```python
   USB_UUID = "YOUR-USB-UUID"
   ```

4. Run it:

   ```bash
   sudo python3 usb_site_lock.py
   ```

Remove USB → sites blocked
Insert USB → sites unblocked

---

## Safety

* Your original `/etc/hosts` is backed up automatically
* All changes are clearly marked
* An `emergency_reset.sh` script is included just in case

---

## Status

This is a personal tool. It’s not meant to be polished or universal — just useful.

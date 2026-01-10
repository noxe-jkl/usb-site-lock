#!/bin/bash
#
# Toggle USB Site Lock on/off
# Bind this to a keyboard shortcut for easy control
#

SCRIPT_PATH="$HOME/scripts/usb_site_lock.py"

if pgrep -f "usb_site_lock.py" > /dev/null; then
    # Running - stop it
    pkexec pkill -f "usb_site_lock.py"
    notify-send -i "security-low" "🔓 Site Lock Disabled" "USB Site Lock has been stopped"
else
    # Not running - start it
    nohup pkexec /usr/bin/python3 "$SCRIPT_PATH" > /tmp/usb_site_lock.log 2>&1 &
    sleep 1
    if pgrep -f "usb_site_lock.py" > /dev/null; then
        notify-send -i "security-high" "🔒 Site Lock Enabled" "USB Site Lock is now running"
    else
        notify-send -i "dialog-error" "❌ Failed" "Site Lock failed to start. Check /tmp/usb_site_lock.log"
    fi
fi

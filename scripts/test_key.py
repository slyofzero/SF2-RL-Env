#!/usr/bin/env python3
"""
Test direct evdev input on Android.
"""
import sys
import time
import subprocess
from common import find_adb, get_connected_device

adb = find_adb()
dev = get_connected_device(adb)

# Test keyboard KEY_J (code 36) on /dev/input/event2
print("[*] Sending KEY_J (down) to /dev/input/event2...")
cmd_down = "sendevent /dev/input/event2 1 36 1 && sendevent /dev/input/event2 0 0 0"
subprocess.run([adb, "-s", dev, "shell", cmd_down])

time.sleep(0.08)

print("[*] Sending KEY_J (up) to /dev/input/event2...")
cmd_up = "sendevent /dev/input/event2 1 36 0 && sendevent /dev/input/event2 0 0 0"
subprocess.run([adb, "-s", dev, "shell", cmd_up])

print("[OK] Dispatched KEY_J without mouse/screen tap!")

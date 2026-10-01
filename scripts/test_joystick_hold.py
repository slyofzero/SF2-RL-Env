#!/usr/bin/env python3
"""
Test holding joystick right for 1.5s via /dev/input/event4
"""
import sys
import time
import subprocess
from common import find_adb, get_connected_device

adb = find_adb()
dev = get_connected_device(adb)

# Joystick Right: X=340, Y=800 -> normalized: X=5802, Y=24271
x_ev = 5802
y_ev = 24271

# Touch DOWN on slot 0:
cmds_down = [
    f"sendevent /dev/input/event4 3 47 0",    # ABS_MT_SLOT 0
    f"sendevent /dev/input/event4 3 57 10",   # ABS_MT_TRACKING_ID 10
    f"sendevent /dev/input/event4 3 53 {x_ev}", # ABS_MT_POSITION_X
    f"sendevent /dev/input/event4 3 54 {y_ev}", # ABS_MT_POSITION_Y
    f"sendevent /dev/input/event4 1 330 1",   # BTN_TOUCH 1
    f"sendevent /dev/input/event4 0 0 0"      # SYN_REPORT
]

# Touch UP on slot 0:
cmds_up = [
    f"sendevent /dev/input/event4 3 47 0",    # ABS_MT_SLOT 0
    f"sendevent /dev/input/event4 3 57 -1",   # ABS_MT_TRACKING_ID -1
    f"sendevent /dev/input/event4 1 330 0",   # BTN_TOUCH 0
    f"sendevent /dev/input/event4 0 0 0"      # SYN_REPORT
]

cmd_down_str = " && ".join(cmds_down)
cmd_up_str = " && ".join(cmds_up)

print("[*] Holding Joystick RIGHT...")
subprocess.run([adb, "-s", dev, "shell", cmd_down_str], check=True)
time.sleep(1.5)
print("[*] Releasing Joystick RIGHT...")
subprocess.run([adb, "-s", dev, "shell", cmd_up_str], check=True)
print("[OK] Held and released!")

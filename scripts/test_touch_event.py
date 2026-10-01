#!/usr/bin/env python3
"""
Test high-speed raw event injection to /dev/input/event4
"""
import sys
import time
import subprocess
from common import find_adb, get_connected_device

adb = find_adb()
dev = get_connected_device(adb)

# Punch coordinates: X=1800, Y=770 -> normalized 32767 scale: X=30719, Y=23351
x_ev = 30719
y_ev = 23351

# In Android multi-touch protocol B:
# Touch DOWN:
# 3 57 tracking_id (e.g. 1)
# 3 53 x (0x0035 = ABS_MT_POSITION_X)
# 3 54 y (0x0036 = ABS_MT_POSITION_Y)
# 1 330 1 (BTN_TOUCH down)
# 0 0 0 (SYN_REPORT)
cmds_down = [
    f"sendevent /dev/input/event4 3 57 1",
    f"sendevent /dev/input/event4 3 53 {x_ev}",
    f"sendevent /dev/input/event4 3 54 {y_ev}",
    f"sendevent /dev/input/event4 1 330 1",
    f"sendevent /dev/input/event4 0 0 0"
]

# Touch UP:
# 3 57 -1 (tracking_id -1)
# 1 330 0 (BTN_TOUCH up)
# 0 0 0 (SYN_REPORT)
cmds_up = [
    f"sendevent /dev/input/event4 3 57 -1",
    f"sendevent /dev/input/event4 1 330 0",
    f"sendevent /dev/input/event4 0 0 0"
]

cmd_full = " && ".join(cmds_down) + f" && sleep 0.05 && " + " && ".join(cmds_up)
print("[*] Executing raw kernel touch event on /dev/input/event4...")
subprocess.run([adb, "-s", dev, "shell", cmd_full], check=True)
print("[OK] Kernel touch event dispatched!")

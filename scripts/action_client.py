#!/usr/bin/env python3
"""
High-Speed Action Controller for Shadow Fight 2 (Cat Blasters 9k).
Dispatches non-tap actions, multi-hit combos, and timed direction holds
directly to the Android input subsystem via persistent ADB connection.

Supports:
  - 'punch' / 'punch <N>'
  - 'kick' / 'kick <N>'
  - 'hold <direction> <duration>' (e.g. 'hold right 2s', 'hold down 500ms')
  - Directional attacks: 'forward punch', 'down kick', 'up kick', etc.
  - Presets: 'resume', 'pause', 'exit_match'
"""

import sys
import os
import time
import re
import subprocess
from typing import Optional

try:
    from scripts.common import find_adb, get_connected_device
except ImportError:
    from common import find_adb, get_connected_device

# Exact tested coordinates from tap.py (1920x1080 Viewport)
BUTTONS = {
    # Combat Attacks
    "punch": (1769, 802),
    "kick": (1699, 935),
    "shadow": (1615, 803),
    "magic": (1615, 803),
    "ranged": (1699, 684),

    # Fight Menu
    "pause": (960, 170),
    "resume": (1380, 700),
    "f-quit": (535, 700),
    "exit_match": (535, 700),
    "f-exit": (1150, 775),
    "confirm_exit": (1150, 775),

    # Map & Navigation
    "fight": (1627, 858),
    "tournament": (406, 450),
    "survival": (270, 640),
    "lynx": (710, 500),
    "menu-open": (211, 150),
    "menu-close": (237, 1021),
    "menu-dojo": (115, 190),
    "menu-map": (115, 350),
    "energy": (415, 45),
    "back": (80, 80),
    "dialog_ok": (400, 930),
    "center_ok": (960, 733),
    "ok": (400, 930),
}

JOYSTICK_CENTER = (225, 860)

# Joystick Directions (discrete tested coordinates from tap.py)
DIRECTIONS = {
    "up": (250, 750),
    "down": (250, 970),
    "left": (30, 850),
    "right": (420, 850),
    "up-right": (350, 750),
    "up-left": (50, 750),
    "down-left": (110, 950),
    "down-right": (330, 950),
    "center": (225, 860),
}

ALIASES = {
    # Direction aliases
    "u": "up",
    "d": "down",
    "l": "left",
    "r": "right",
    "ur": "up-right",
    "ul": "up-left",
    "dl": "down-left",
    "dr": "down-right",
    "upright": "up-right",
    "upleft": "up-left",
    "downleft": "down-left",
    "downright": "down-right",
    "forward": "right",
    "fwd": "right",
    "back": "left",
    "backward": "left",
    "jump": "up",
    "crouch": "down",
    "duck": "down",

    # Button aliases
    "p": "punch",
    "k": "kick",
    "s": "shadow",
    "f": "fight",
    "ok": "dialog_ok",
}

class ActionClient:
    def __init__(self, adb_path: Optional[str] = None, serial: Optional[str] = None):
        self.adb = adb_path or find_adb()
        self.serial = serial or get_connected_device(self.adb)
        
        # Start persistent ADB shell process
        self.proc = subprocess.Popen(
            [self.adb, "-s", self.serial, "shell"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1
        )

    def _exec(self, cmd: str):
        if self.proc and self.proc.stdin:
            self.proc.stdin.write(cmd + "\n")
            self.proc.stdin.flush()

    def tap(self, x: int, y: int):
        self._exec(f"input tap {x} {y}")

    def hold(self, x: int, y: int, duration_ms: int):
        self._exec(f"input swipe {x} {y} {x} {y} {duration_ms}")

    def punch(self, count: int = 1):
        x, y = BUTTONS["punch"]
        for i in range(count):
            self.tap(x, y)
            if i < count - 1:
                time.sleep(0.12)

    def kick(self, count: int = 1):
        x, y = BUTTONS["kick"]
        for i in range(count):
            self.tap(x, y)
            if i < count - 1:
                time.sleep(0.14)

    def hold_direction(self, direction: str, duration_sec: float):
        d = ALIASES.get(direction.lower(), direction.lower())
        if d not in DIRECTIONS:
            raise ValueError(f"Unknown direction: {direction}")
        jx, jy = DIRECTIONS[d]
        dur_ms = max(50, int(duration_sec * 1000))
        self.hold(jx, jy, dur_ms)

    def combo(self, direction: str, button: str, count: int = 1):
        """Simultaneous directional attack: holds direction on joystick while tapping attack button."""
        d = ALIASES.get(direction.lower(), direction.lower())
        if d not in DIRECTIONS:
            raise ValueError(f"Unknown direction: {direction}")
        jx, jy = DIRECTIONS[d]
        b = ALIASES.get(button.lower(), button.lower())
        bx, by = BUTTONS.get(b, BUTTONS["punch"])
        
        for i in range(count):
            # Swipe/hold joystick while tapping the attack button with 40ms offset
            cmd = f"input swipe {jx} {jy} {jx} {jy} 400 & (sleep 0.04 && input tap {bx} {by})"
            self._exec(cmd)
            if i < count - 1:
                time.sleep(0.35)

    def execute_command(self, cmd_str: str) -> str:
        cmd = cmd_str.strip().lower()
        if not cmd:
            return ""

        # Presets & direct button names
        btn_key = ALIASES.get(cmd, cmd)
        if btn_key in BUTTONS:
            x, y = BUTTONS[btn_key]
            self.tap(x, y)
            return f"[EXECUTED] Button tap: {btn_key}"

        # Natural number aliases
        cmd = re.sub(r'^double[- ]punch$', 'punch 2', cmd)
        cmd = re.sub(r'^triple[- ]punch$', 'punch 3', cmd)
        cmd = re.sub(r'^double[- ]kick$', 'kick 2', cmd)
        cmd = re.sub(r'^triple[- ]kick$', 'kick 3', cmd)

        # Check for natural directional attack combo before general chaining:
        # e.g. 'joystick to the right and then kick', 'right then punch', 'forward and then kick'
        m_nat_combo = re.match(
            r'^(?:(?:joystick\s+(?:to\s+the\s+|to\s+)?|move\s+))?([a-zA-Z\-]+)\s+(?:and\s+then|then|\s+)\s*(punch|kick|shadow|magic|ranged)(?:\s+(\d+))?$',
            cmd
        )
        if m_nat_combo:
            dir_raw, btn_raw, cnt = m_nat_combo.groups()
            d_lower = dir_raw.lower()
            if d_lower in DIRECTIONS or d_lower in ALIASES:
                count = int(cnt) if cnt else 1
                self.combo(dir_raw, btn_raw, count)
                return f"[EXECUTED] {dir_raw} {btn_raw} ({count}x)"

        # Support chaining via 'and then', 'then', ';', or ','
        chain_delims = re.split(r'\s+(?:and\s+then|then)\s+|[;,]', cmd)
        if len(chain_delims) > 1:
            results = []
            for sub_cmd in chain_delims:
                sub_res = self.execute_command(sub_cmd.strip())
                if sub_res:
                    results.append(sub_res)
                time.sleep(0.08)
            return " -> ".join(results)

        # Normalize common natural language prefixes
        cmd_clean = re.sub(r'^(?:joystick\s+(?:to\s+the\s+|to\s+)?|move\s+)', '', cmd).strip()

        # Pattern: [hold] <direction> <duration>
        # e.g. 'hold right 2s', 'hold right 2', 'left 2s', 'hold down 500ms', 'up-right 1s'
        m_hold = re.match(r'^(?:(hold)\s+)?([a-zA-Z\-]+)\s+([0-9.]+)\s*(s|sec|ms)?$', cmd_clean)
        if m_hold:
            has_hold, direction, dur_val, dur_unit = m_hold.groups()
            if has_hold or dur_unit:
                d_lower = direction.lower()
                if d_lower in DIRECTIONS or d_lower in ALIASES:
                    dur = float(dur_val)
                    if dur_unit == "ms":
                        dur = dur / 1000.0
                    self.hold_direction(direction, dur)
                    return f"[EXECUTED] hold {direction} for {dur:.2f}s"

        # Pattern: <direction> <count> (e.g. 'right 5', 'down-left 2', 'up 3' like tap.py)
        m_dir_count = re.match(r'^([a-zA-Z\-]+)\s+(\d+)$', cmd_clean)
        if m_dir_count:
            dir_raw, cnt = m_dir_count.groups()
            d = ALIASES.get(dir_raw.lower(), dir_raw.lower())
            if d in DIRECTIONS:
                count = int(cnt)
                x, y = DIRECTIONS[d]
                for i in range(count):
                    self.tap(x, y)
                    if i < count - 1:
                        time.sleep(0.18)
                return f"[EXECUTED] {d} tap ({count}x)"

        # Pattern: punch [<N>]
        m_punch = re.match(r'^punch(?:\s+(\d+))?$', cmd)
        if m_punch:
            count = int(m_punch.group(1)) if m_punch.group(1) else 1
            self.punch(count)
            return f"[EXECUTED] punch ({count}x)"

        # Pattern: kick [<N>]
        m_kick = re.match(r'^kick(?:\s+(\d+))?$', cmd)
        if m_kick:
            count = int(m_kick.group(1)) if m_kick.group(1) else 1
            self.kick(count)
            return f"[EXECUTED] kick ({count}x)"

        # Pattern: directional combos (e.g. 'forward punch', 'down kick 2', 'up kick', 'right kick')
        m_combo = re.match(r'^(forward|back|backward|up|down|right|left|up-right|up-left|down-right|down-left)\s+(punch|kick)(?:\s+(\d+))?$', cmd)
        if m_combo:
            direction, button, cnt = m_combo.groups()
            count = int(cnt) if cnt else 1
            self.combo(direction, button, count)
            return f"[EXECUTED] {direction} {button} ({count}x)"

        # Simple directions (single tap, e.g. 'up-right', 'up', 'right', 'left')
        d = ALIASES.get(cmd_clean, cmd_clean)
        if d in DIRECTIONS:
            x, y = DIRECTIONS[d]
            self.tap(x, y)
            return f"[EXECUTED] {d} tap"

        return f"[ERROR] Unrecognized command: '{cmd_str}'"

    def close(self):
        if self.proc:
            try:
                if self.proc.stdin:
                    self.proc.stdin.flush()
                time.sleep(0.08)
                self.proc.terminate()
            except Exception:
                pass

def main():
    client = ActionClient()
    print("============================================================")
    print(" Shadow Fight 2 — Interactive Action Controller (v5)")
    print("============================================================")
    print(" Direct sub-millisecond input engine active")
    print(" Supported commands:")
    print("   punch              - Single punch")
    print("   punch <N>          - Multi-punch combo (e.g. punch 2, punch 3)")
    print("   kick               - Single kick")
    print("   kick <N>           - Multi-kick combo (e.g. kick 2)")
    print("   hold <dir> <dur>   - Hold direction (e.g. hold right 2s, hold left 1.5s)")
    print("   <dir> <punch/kick> - Directional attack (e.g. forward punch, down kick)")
    print("   pause / resume     - Pause or resume combat")
    print("   exit_match         - Return to world map")
    print("   exit / quit        - Exit controller")
    print("------------------------------------------------------------")

    try:
        while True:
            try:
                line = input("SF2 > ").strip()
            except EOFError:
                break
            if not line:
                continue
            if line.lower() in ("exit", "quit", "q"):
                break
            res = client.execute_command(line)
            print(res)
    finally:
        client.close()
        print("\n[OK] Action client closed.")

if __name__ == "__main__":
    main()

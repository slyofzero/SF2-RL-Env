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

import re
import struct
import subprocess
import time

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
    def __init__(self, adb_path: str | None = None, serial: str | None = None):
        self.adb = adb_path or find_adb()
        self.serial = serial or get_connected_device(self.adb)

        # Start persistent ADB shell process for standard UI commands
        self.proc = subprocess.Popen(
            [self.adb, "-s", self.serial, "shell"],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True,
            bufsize=1,
        )

        # Start persistent binary event pipe to /dev/input/event4 for sub-millisecond kernel multi-touch
        self.pipe_proc = subprocess.Popen(
            [self.adb, "-s", self.serial, "shell", "cat > /dev/input/event4"], stdin=subprocess.PIPE, bufsize=0
        )

        # Double-tap timing configuration (in seconds)
        # tap_hold: duration the attack button stays pressed down
        # tap_gap: delay between releasing tap 1 and pressing tap 2
        self.double_tap_hold = 0.03  # 30ms hold
        self.double_tap_gap = 0.015  # 15ms true double-tap gap (sub-millisecond hardware precision)

    def _exec(self, cmd: str):
        if self.proc and self.proc.stdin:
            self.proc.stdin.write(cmd + "\n")
            self.proc.stdin.flush()

    def _ev(self, type_: int, code: int, val: int) -> bytes:
        """Pack a 24-byte Linux kernel input_event struct (x86_64)."""
        return struct.pack("<qqHHi", 0, 0, type_, code, val)

    def _write_ev(self, events: list):
        """Write raw binary events directly to the kernel event stream with microsecond latency."""
        if self.pipe_proc and self.pipe_proc.stdin:
            buf = b"".join(self._ev(t, c, v) for t, c, v in events)
            try:
                self.pipe_proc.stdin.write(buf)
                self.pipe_proc.stdin.flush()
            except Exception:
                pass

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

    def to_ev(self, x: int, y: int) -> tuple:
        """Convert 1920x1080 screen pixels to BlueStacks Virtual Touch 32767 scale."""
        return int(x * 32767 / 1920), int(y * 32767 / 1080)

    def reset_touch_slots(self):
        """Release any potentially stuck multi-touch slots on /dev/input/event4."""
        self._write_ev([(3, 47, 0), (3, 57, -1), (3, 47, 1), (3, 57, -1), (1, 330, 0), (0, 0, 0)])

    def hold_direction(self, direction: str, duration_sec: float):
        """Hold a joystick direction via direct binary kernel touch event on Slot 0."""
        d = ALIASES.get(direction.lower(), direction.lower())
        if d not in DIRECTIONS:
            raise ValueError(f"Unknown direction: {direction}")
        jx, jy = DIRECTIONS[d]
        jx_ev, jy_ev = self.to_ev(jx, jy)
        dur = max(0.05, duration_sec)

        self._write_ev([(3, 47, 0), (3, 57, 10), (3, 53, jx_ev), (3, 54, jy_ev), (1, 330, 1), (0, 0, 0)])
        time.sleep(dur)
        self._write_ev([(3, 47, 0), (3, 57, -1), (1, 330, 0), (0, 0, 0)])

    def combo(self, direction: str, button: str, count: int = 1):
        """
        True multi-touch directional attack via direct binary stream:
        Holds joystick direction on Slot 0 while tapping attack button on Slot 1.
        """
        d = ALIASES.get(direction.lower(), direction.lower())
        if d not in DIRECTIONS:
            raise ValueError(f"Unknown direction: {direction}")
        jx, jy = DIRECTIONS[d]
        b = ALIASES.get(button.lower(), button.lower())
        bx, by = BUTTONS.get(b, BUTTONS["punch"])

        jx_ev, jy_ev = self.to_ev(jx, jy)
        bx_ev, by_ev = self.to_ev(bx, by)

        # 1. Simultaneous Initial DOWN: Slot 0 + Slot 1 in ONE atomic frame
        self._write_ev(
            [
                (3, 47, 0),
                (3, 57, 10),
                (3, 53, jx_ev),
                (3, 54, jy_ev),
                (3, 47, 1),
                (3, 57, 11),
                (3, 53, bx_ev),
                (3, 54, by_ev),
                (1, 330, 1),
                (0, 0, 0),
            ]
        )
        time.sleep(0.06)
        self._write_ev([(3, 47, 1), (3, 57, -1), (0, 0, 0)])

        # 2. Subsequent hits while joystick remains held
        for i in range(1, count):
            time.sleep(0.12)
            tid = 11 + i
            self._write_ev([(3, 47, 1), (3, 57, tid), (3, 53, bx_ev), (3, 54, by_ev), (0, 0, 0)])
            time.sleep(0.06)
            self._write_ev([(3, 47, 1), (3, 57, -1), (0, 0, 0)])

        time.sleep(0.02)
        self._write_ev([(3, 47, 0), (3, 57, -1), (1, 330, 0), (0, 0, 0)])

    def directional_double_attack(
        self, direction: str, button: str = "punch", gap_sec: float | None = None, hold_sec: float | None = None
    ):
        """
        True sub-millisecond rapid double-tap combo (D, J+J / A, K+K):
        Streams raw binary struct input_event directly to /dev/input/event4.
        ZERO subprocess overhead, exact microsecond precision.
        """
        d = ALIASES.get(direction.lower(), direction.lower())
        if d not in DIRECTIONS:
            raise ValueError(f"Unknown direction: {direction}")
        jx, jy = DIRECTIONS[d]
        b = ALIASES.get(button.lower(), button.lower())
        bx, by = BUTTONS.get(b, BUTTONS["punch"])

        jx_ev, jy_ev = self.to_ev(jx, jy)
        bx_ev, by_ev = self.to_ev(bx, by)

        tap_hold = hold_sec if hold_sec is not None else getattr(self, "double_tap_hold", 0.03)
        tap_gap = gap_sec if gap_sec is not None else getattr(self, "double_tap_gap", 0.015)

        # 1. Hold Joystick (Slot 0) + Tap 1 (Slot 1) simultaneously in ONE frame
        self._write_ev(
            [
                (3, 47, 0),
                (3, 57, 10),
                (3, 53, jx_ev),
                (3, 54, jy_ev),
                (3, 47, 1),
                (3, 57, 11),
                (3, 53, bx_ev),
                (3, 54, by_ev),
                (1, 330, 1),
                (0, 0, 0),
            ]
        )
        time.sleep(tap_hold)

        # 2. Release Tap 1 (Slot 1) while Joystick (Slot 0) stays firmly held
        self._write_ev([(3, 47, 1), (3, 57, -1), (0, 0, 0)])
        time.sleep(tap_gap)

        # 3. Tap 2 (Slot 1) rapid follow-up with tracking ID 12
        self._write_ev([(3, 47, 1), (3, 57, 12), (3, 53, bx_ev), (3, 54, by_ev), (0, 0, 0)])
        time.sleep(tap_hold)

        # 4. Release Tap 2 (Slot 1)
        self._write_ev([(3, 47, 1), (3, 57, -1), (0, 0, 0)])
        time.sleep(0.02)

        # 5. Release Joystick (Slot 0)
        self._write_ev([(3, 47, 0), (3, 57, -1), (1, 330, 0), (0, 0, 0)])

    def execute_command(self, cmd_str: str) -> str:
        cmd = cmd_str.strip().lower()
        if not cmd:
            return ""

        if cmd in ("reset", "clear_touch", "reset_touch"):
            self.reset_touch_slots()
            return "[EXECUTED] Multi-touch slots reset"

        # Runtime Timing Configuration (e.g. 'gap 15ms', 'set gap 0.02', 'hold 25ms', 'timing')
        m_set_gap = re.match(r"^(?:set\s+)?gap\s+([0-9.]+)\s*(ms|s)?$", cmd)
        if m_set_gap:
            val, unit = m_set_gap.groups()
            sec = float(val) / 1000.0 if unit == "ms" or float(val) >= 1.0 else float(val)
            self.double_tap_gap = max(0.001, sec)
            return f"[TIMING] Double-tap gap set to {self.double_tap_gap * 1000:.1f}ms ({self.double_tap_gap:.3f}s)"

        m_set_hold = re.match(r"^(?:set\s+)?hold(?:_dur)?\s+([0-9.]+)\s*(ms|s)?$", cmd)
        if m_set_hold:
            val, unit = m_set_hold.groups()
            sec = float(val) / 1000.0 if unit == "ms" or float(val) >= 1.0 else float(val)
            self.double_tap_hold = max(0.001, sec)
            return f"[TIMING] Double-tap hold duration set to {self.double_tap_hold * 1000:.1f}ms ({self.double_tap_hold:.3f}s)"

        if cmd in ("timing", "get_timing", "delay"):
            return f"[TIMING] Gap between taps: {self.double_tap_gap * 1000:.1f}ms | Tap hold duration: {self.double_tap_hold * 1000:.1f}ms"

        # Shorthand notation (e.g. 'd, j+j', 'd j+j 15ms', 'a, k+k')
        KEY_DIR = {"w": "up", "a": "left", "s": "down", "d": "right"}
        KEY_ACT = {"j": "punch", "k": "kick"}
        m_short = re.match(r"^([wasd])[\s,]+([jk])\s*\+\s*([jk])(?:\s+([0-9.]+)\s*(ms|s)?)?$", cmd)
        if m_short:
            k_dir, b1, b2, dur_val, dur_unit = m_short.groups()
            direction = KEY_DIR[k_dir]
            button = KEY_ACT[b1]
            custom_gap = None
            if dur_val:
                custom_gap = float(dur_val) / 1000.0 if dur_unit == "ms" or float(dur_val) >= 1.0 else float(dur_val)
            self.directional_double_attack(direction, button, gap_sec=custom_gap)
            gap_used = custom_gap if custom_gap is not None else self.double_tap_gap
            return f"[EXECUTED] {direction} double-{button} ({k_dir.upper()}, {b1.upper()}+{b2.upper()}) [gap: {gap_used * 1000:.1f}ms]"

        # Directional double-attack (e.g. 'right double-punch', 'left double-punch 10ms', 'right double-kick')
        m_double = re.match(
            r"^(?:(?:joystick\s+(?:to\s+the\s+|to\s+)?|move\s+|hold\s+)?)([a-zA-Z\-]+)(?:\s*\+\s*|\s+(?:and\s+then|then|and|\&)?\s+|\s+)double[- ](punch|kick)(?:\s+([0-9.]+)\s*(ms|s)?)?$",
            cmd,
        )
        if m_double:
            direction, button, dur_val, dur_unit = m_double.groups()
            d_lower = direction.lower()
            if d_lower in DIRECTIONS or d_lower in ALIASES:
                custom_gap = None
                if dur_val:
                    custom_gap = (
                        float(dur_val) / 1000.0 if dur_unit == "ms" or float(dur_val) >= 1.0 else float(dur_val)
                    )
                self.directional_double_attack(direction, button, gap_sec=custom_gap)
                gap_used = custom_gap if custom_gap is not None else self.double_tap_gap
                return f"[EXECUTED] {direction} double-{button} [gap: {gap_used * 1000:.1f}ms]"

        # Reverse order (e.g. 'double-punch right', 'double kick left 15ms')
        m_rev_double = re.match(
            r"^double[- ](punch|kick)\s+(?:to\s+the\s+)?([a-zA-Z\-]+)(?:\s+([0-9.]+)\s*(ms|s)?)?$", cmd
        )
        if m_rev_double:
            button, direction, dur_val, dur_unit = m_rev_double.groups()
            d_lower = direction.lower()
            if d_lower in DIRECTIONS or d_lower in ALIASES:
                custom_gap = None
                if dur_val:
                    custom_gap = (
                        float(dur_val) / 1000.0 if dur_unit == "ms" or float(dur_val) >= 1.0 else float(dur_val)
                    )
                self.directional_double_attack(direction, button, gap_sec=custom_gap)
                gap_used = custom_gap if custom_gap is not None else self.double_tap_gap
                return f"[EXECUTED] {direction} double-{button} [gap: {gap_used * 1000:.1f}ms]"

        # Presets & direct button names
        btn_key = ALIASES.get(cmd, cmd)
        if btn_key in BUTTONS:
            x, y = BUTTONS[btn_key]
            self.tap(x, y)
            return f"[EXECUTED] Button tap: {btn_key}"

        # Natural number aliases
        cmd = re.sub(r"^double[- ]punch$", "punch 2", cmd)
        cmd = re.sub(r"^triple[- ]punch$", "punch 3", cmd)
        cmd = re.sub(r"^double[- ]kick$", "kick 2", cmd)
        cmd = re.sub(r"^triple[- ]kick$", "kick 3", cmd)

        # Check for natural directional attack combo before general chaining:
        # e.g. 'right punch', 'left punch', 'up kick', 'down punch 2', 'right + punch',
        #      'joystick to the right and punch', 'move left then kick'
        m_nat_combo = re.match(
            r"^(?:(?:joystick\s+(?:to\s+the\s+|to\s+)?|move\s+|hold\s+)?)([a-zA-Z\-]+)(?:\s*\+\s*|\s+(?:and\s+then|then|and|\&)?\s+|\s+)(punch|kick|shadow|magic|ranged)(?:\s+(\d+))?$",
            cmd,
        )
        if m_nat_combo:
            dir_raw, btn_raw, cnt = m_nat_combo.groups()
            d_lower = dir_raw.lower()
            if d_lower in DIRECTIONS or d_lower in ALIASES:
                count = int(cnt) if cnt else 1
                self.combo(dir_raw, btn_raw, count)
                return f"[EXECUTED] {dir_raw} {btn_raw} ({count}x) [multi-touch]"

        # Also support reverse order: e.g. 'punch right', 'kick left 2'
        m_rev_combo = re.match(
            r"^(punch|kick|shadow|magic|ranged)(?:\s*\+\s*|\s+(?:and\s+then|then|and|\&)?\s+|\s+)(?:(?:joystick\s+(?:to\s+the\s+|to\s+)?|move\s+|hold\s+)?)([a-zA-Z\-]+)(?:\s+(\d+))?$",
            cmd,
        )
        if m_rev_combo:
            btn_raw, dir_raw, cnt = m_rev_combo.groups()
            d_lower = dir_raw.lower()
            if d_lower in DIRECTIONS or d_lower in ALIASES:
                count = int(cnt) if cnt else 1
                self.combo(dir_raw, btn_raw, count)
                return f"[EXECUTED] {dir_raw} {btn_raw} ({count}x) [multi-touch]"

        # Support chaining via 'and then', 'then', ';', or ','
        chain_delims = re.split(r"\s+(?:and\s+then|then)\s+|[;,]", cmd)
        if len(chain_delims) > 1:
            results = []
            for sub_cmd in chain_delims:
                sub_res = self.execute_command(sub_cmd.strip())
                if sub_res:
                    results.append(sub_res)
                time.sleep(0.08)
            return " -> ".join(results)

        # Normalize common natural language prefixes
        cmd_clean = re.sub(r"^(?:joystick\s+(?:to\s+the\s+|to\s+)?|move\s+)", "", cmd).strip()

        # Pattern: [hold] <direction> <duration>
        # e.g. 'hold right 2s', 'hold right 2', 'left 2s', 'hold down 500ms', 'up-right 1s'
        m_hold = re.match(r"^(?:(hold)\s+)?([a-zA-Z\-]+)\s+([0-9.]+)\s*(s|sec|ms)?$", cmd_clean)
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
        m_dir_count = re.match(r"^([a-zA-Z\-]+)\s+(\d+)$", cmd_clean)
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
        m_punch = re.match(r"^punch(?:\s+(\d+))?$", cmd)
        if m_punch:
            count = int(m_punch.group(1)) if m_punch.group(1) else 1
            self.punch(count)
            return f"[EXECUTED] punch ({count}x)"

        # Pattern: kick [<N>]
        m_kick = re.match(r"^kick(?:\s+(\d+))?$", cmd)
        if m_kick:
            count = int(m_kick.group(1)) if m_kick.group(1) else 1
            self.kick(count)
            return f"[EXECUTED] kick ({count}x)"

        # Pattern: directional combos (e.g. 'forward punch', 'down kick 2', 'up kick', 'right kick')
        m_combo = re.match(
            r"^(forward|back|backward|up|down|right|left|up-right|up-left|down-right|down-left)\s+(punch|kick)(?:\s+(\d+))?$",
            cmd,
        )
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
        if hasattr(self, "pipe_proc") and self.pipe_proc:
            try:
                if self.pipe_proc.stdin:
                    self.pipe_proc.stdin.flush()
                    self.pipe_proc.stdin.close()
                self.pipe_proc.terminate()
            except Exception:
                pass
        if self.proc:
            try:
                if self.proc.stdin:
                    self.proc.stdin.flush()
                time.sleep(0.04)
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

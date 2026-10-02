#!/usr/bin/env python3
"""
Tap Simulation Helper Script for Shadow Fight 2 (Cat Blasters 9k).
Simulates screen taps on arbitrary coordinates or preset UI buttons via ADB.
Supports interactive multi-command inputs (e.g., 'up', 'down', 'right 5', 'down-left 2')
using Python's input() utility.
"""

import sys
import argparse
import time
import subprocess
import os
import re
from typing import Optional, Tuple

from common import find_adb, get_connected_device

# Known UI Coordinates for 1920x1080 resolution
PRESETS = {
    # Navigation & Map UI
    "fight": (1627, 858),        # Act 1 Map Stage 1 "FIGHT!" button
    "tournament": (406, 450),    # Tournament Map Pin
    "survival": (270, 640),      # Survival Map Pin
    "lynx": (710, 500),          # Lynx Map Pin
    "menu-open": (211, 150),     # Top-Left Menu Scroll
    "menu-close": (237, 1021),   # Top-Left Menu Scroll
    "menu-dojo": (115, 190),     # Top-Left Menu -> Dojo Pagoda icon
    "menu-map": (115, 350),      # Top-Left Menu -> Act Map icon
    "energy": (415, 45),         # Top Energy Bar / VIP Icon
    "back": (80, 80),            # Back Arrow / Escape
    "dialog_ok": (400, 930),     # Post-Match OK button
    "center_ok": (960, 733),     # Center modal OK button (e.g. reward dialogs)

    # Joystick Directions
    "up": (250, 750),
    "down": (250, 970),
    "left": (30, 850),
    "right": (420, 850),
    "up-right": (350, 750),
    "up-left": (50, 750),
    "down-left": (110, 950),
    "down-right": (330, 950),

    # Combat Attacks
    "punch": (1769, 802),
    "kick": (1699, 935),
    "shadow": (1615, 803),
    "ranged": (1699, 684),

    # Fight Menu
    "pause": (960, 170),
    "resume": (1380, 700),
    "f-quit": (535, 700),
    "f-exit": (1150, 775),
}

# Aliases for quick typing
ALIASES = {
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
    "p": "punch",
    "k": "kick",
    "f": "fight",
    "ok": "dialog_ok",
}


def tap(x: int, y: int, device: Optional[str] = None, adb: Optional[str] = None, delay: float = 0.0) -> bool:
    """Dispatches a touch tap event to (x, y) on the target device."""
    if delay > 0:
        time.sleep(delay)

    adb_bin = adb or find_adb()
    serial = device or get_connected_device(adb_bin)

    cmd = [adb_bin]
    if serial:
        cmd += ["-s", serial]
    cmd += ["shell", "input", "tap", str(x), str(y)]

    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        if res.returncode == 0:
            return True
        else:
            print(f"[Error] Tap command failed: {res.stderr.strip()}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"[Error] Failed to execute tap: {e}", file=sys.stderr)
        return False


def parse_command(cmd_str: str) -> Optional[Tuple[Tuple[int, int], int, str]]:
    """
    Parses a single command string into ((x, y), count, label).
    Supported formats:
      - 'up' -> ((250, 750), 1, 'up')
      - 'right 5' -> ((420, 850), 5, 'right')
      - 'down-left 2' -> ((110, 950), 2, 'down-left')
      - '1627 858' -> ((1627, 858), 1, 'coord(1627,858)')
      - '1627 858 3' -> ((1627, 858), 3, 'coord(1627,858)')
    """
    tokens = cmd_str.strip().split()
    if not tokens:
        return None

    # Case 1: 1 token -> preset or alias with count=1
    if len(tokens) == 1:
        key = ALIASES.get(tokens[0].lower(), tokens[0].lower())
        if key in PRESETS:
            return PRESETS[key], 1, key

    # Case 2: 2 tokens -> 'preset count' OR 'x y'
    elif len(tokens) == 2:
        key = ALIASES.get(tokens[0].lower(), tokens[0].lower())
        if key in PRESETS and tokens[1].isdigit():
            return PRESETS[key], int(tokens[1]), key
        elif tokens[0].isdigit() and tokens[1].isdigit():
            return (int(tokens[0]), int(tokens[1])), 1, f"coord({tokens[0]},{tokens[1]})"

    # Case 3: 3 tokens -> 'x y count'
    elif len(tokens) == 3:
        if tokens[0].isdigit() and tokens[1].isdigit() and tokens[2].isdigit():
            return (int(tokens[0]), int(tokens[1])), int(tokens[2]), f"coord({tokens[0]},{tokens[1]})"

    return None


def execute_subcommand(sub_cmd: str, adb: str, serial: str, interval: float = 0.25) -> bool:
    """Executes a parsed subcommand string."""
    parsed = parse_command(sub_cmd)
    if not parsed:
        print(f"[!] Unknown command: '{sub_cmd}'. Type 'help' to see presets.")
        return False

    (x, y), count, label = parsed
    print(f"[*] Running '{label}' ({x}, {y}) x{count} on {serial}...")

    for i in range(count):
        if i > 0 and interval > 0:
            time.sleep(interval)
        success = tap(x, y, device=serial, adb=adb)
        if not success:
            print(f"[Error] Failed at step {i + 1}/{count} for '{label}'.")
            return False

    print(f"[SUCCESS] Finished '{label}' x{count}.")
    return True


def show_help():
    print("\n--- Available Commands & Presets ---")
    print("Directions: up, down, left, right, up-left, up-right, down-left, down-right")
    print("Aliases:    u, d, l, r, ul, ur, dl, dr")
    print("Combat:     punch (p), kick (k), shadow, ranged")
    print("UI Buttons: fight (f), tournament, survival, lynx, menu-open, menu-close, energy, back, dialog_ok (ok)")
    print("Raw coords: <x> <y> [count]  (e.g., '1627 858 2')")
    print("Usage examples:")
    print("  up")
    print("  down")
    print("  right 5")
    print("  down-left 2")
    print("  punch 3")
    print("  exit / quit (to leave)\n")


def run_interactive(adb: str, serial: str, interval: float = 0.25):
    """
    Interactive command loop using Python's built-in input() function.
    Reads commands line-by-line or batch-pasted lines.
    """
    is_tty = sys.stdin.isatty()
    prompt = "tap> " if is_tty else ""

    if is_tty:
        print("=== Shadow Fight 2 Tap Controller ===")
        print(f"[*] Connected device: {serial}")
        print("Enter commands (e.g. 'up', 'down', 'right 5', 'down-left 2', or 'exit'):")

    while True:
        try:
            line = input(prompt)
        except (EOFError, KeyboardInterrupt):
            if is_tty:
                print("\nExiting.")
            break

        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if line.lower() in ("exit", "quit", "q"):
            if is_tty:
                print("Exiting.")
            break

        if line.lower() in ("help", "?"):
            show_help()
            continue

        # Support semicolon or newline chained commands
        commands = [c.strip() for c in re.split(r"[;\n]+", line) if c.strip()]
        for c in commands:
            execute_subcommand(c, adb, serial, interval=interval)


def main():
    parser = argparse.ArgumentParser(
        description="Simulate button pressing / tapping on any screen coordinate or preset."
    )
    parser.add_argument("x", nargs="?", type=int, help="Optional X coordinate (e.g. 1627)")
    parser.add_argument("y", nargs="?", type=int, help="Optional Y coordinate (e.g. 870)")
    parser.add_argument("--preset", choices=list(PRESETS.keys()), help="Named UI button preset")
    parser.add_argument("--delay", type=float, default=0.0, help="Seconds to wait before tapping")
    parser.add_argument("--repeat", type=int, default=1, help="Number of times to tap")
    parser.add_argument("--interval", type=float, default=0.25, help="Interval in seconds between repeated taps")
    parser.add_argument("-s", "--serial", default=None, help="Device serial")
    parser.add_argument("-c", "--command", type=str, default=None, help="Direct inline command (e.g. 'right 5')")
    args = parser.parse_args()

    adb = find_adb()
    device = args.serial or get_connected_device(adb)

    # If single inline command is provided via -c:
    if args.command:
        if args.delay > 0:
            time.sleep(args.delay)
        commands = [c.strip() for c in re.split(r"[;\n]+", args.command) if c.strip()]
        for c in commands:
            execute_subcommand(c, adb, device, interval=args.interval)
        return 0

    # If CLI coordinate or preset is specified directly:
    if args.preset:
        target_x, target_y = PRESETS[args.preset]
        label = args.preset
    elif args.x is not None and args.y is not None:
        target_x, target_y = args.x, args.y
        label = f"({target_x}, {target_y})"
    else:
        # Default behavior: Enter interactive input mode using Python's input()
        run_interactive(adb, device, interval=args.interval)
        return 0

    # Single-shot execution from CLI args
    if args.delay > 0:
        print(f"[*] Waiting {args.delay}s before dispatching tap...")
        time.sleep(args.delay)

    for i in range(args.repeat):
        if i > 0 and args.interval > 0:
            time.sleep(args.interval)
        success = tap(target_x, target_y, device=device, adb=adb)
        if not success:
            return 1
        print(f"[SUCCESS] Tapped {label} ({target_x}, {target_y}) [{i+1}/{args.repeat}].")

    return 0


if __name__ == "__main__":
    sys.exit(main())

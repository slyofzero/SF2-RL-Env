#!/usr/bin/env python3
"""
Boot Script for Shadow Fight 2 (Cat Blasters 9k).
Checks if the target package is installed. If available, it boots the app.
If not found, it warns the user and prompts them to run install.
"""

import argparse
import os
import sys
import time

from common import DEFAULT_PACKAGE, boot_app, find_adb, get_connected_device, is_installed


def main():
    parser = argparse.ArgumentParser(description="Check for SF2 installation and boot the app.")
    parser.add_argument("--package", default=DEFAULT_PACKAGE, help=f"Package to boot (default: {DEFAULT_PACKAGE})")
    parser.add_argument("-s", "--serial", default=None, help="Target device serial")
    parser.add_argument("--restart", action="store_true", help="Force stop before booting")
    parser.add_argument("--screenshot", action="store_true", help="Take a verification screenshot after booting")
    args = parser.parse_args()

    adb = find_adb()
    device = args.serial or get_connected_device(adb)
    print("============================================================")
    print(" Shadow Fight 2 — Boot / Launch Controller")
    print("============================================================")
    print(f" Target Device  : {device}")
    print(f" Target Package : {args.package}")
    print("------------------------------------------------------------")

    # Step 1: Check for installation
    installed = is_installed(package_name=args.package, device=device)
    if not installed:
        print(f"[ERROR] Package '{args.package}' is NOT installed on {device}!", file=sys.stderr)
        print("        Please install the game first by running:", file=sys.stderr)
        print("        -> make install", file=sys.stderr)
        print("============================================================", file=sys.stderr)
        return 1

    print(f"[OK] Installation found for '{args.package}'.")

    # Optional restart
    if args.restart:
        print(f"[*] Stopping existing instance of '{args.package}'...")
        import subprocess

        subprocess.run([adb, "-s", device, "shell", "am", "force-stop", args.package], capture_output=True)
        time.sleep(1)

    # Step 2: Boot app
    print(f"[*] Booting '{args.package}'...")
    success = boot_app(package_name=args.package, device=device)

    if success:
        print("------------------------------------------------------------")
        print(f"[SUCCESS] Boot signal dispatched to '{args.package}' on {device}!")
        print("          The game is now launching.")

        if args.screenshot:
            print("[*] Waiting 10s for scene loading before capturing screenshot...")
            time.sleep(10)
            try:
                root_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
                screenshot_script = os.path.join(
                    root_dir, ".agents", "skills", "bluestacks-instant-screenshot", "scripts", "screenshot.py"
                )
                if os.path.exists(screenshot_script):
                    import subprocess

                    subprocess.run([sys.executable, screenshot_script, "--artifact", "boot_verified"])
            except Exception as e:
                print(f"[Warning] Screenshot capture failed: {e}")

        print("============================================================")
        return 0
    else:
        print(f"[FAILED] Failed to boot '{args.package}'. Check ADB connection.", file=sys.stderr)
        print("============================================================", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Install Script for Shadow Fight 2 (Cat Blasters 9k).
Checks if the target package is already installed on the emulator/device.
If not found, it installs the specified APK (default: SF2_Modded_v4.apk).
"""

import sys
import argparse
import os

from common import is_installed, install_apk, get_connected_device, find_adb, DEFAULT_PACKAGE, DEFAULT_APK

def main():
    parser = argparse.ArgumentParser(description="Check for SF2 package and install APK if missing.")
    parser.add_argument("--apk", default=DEFAULT_APK, help=f"Path to APK file to install (default: {DEFAULT_APK})")
    parser.add_argument("--package", default=DEFAULT_PACKAGE, help=f"Package name to check (default: {DEFAULT_PACKAGE})")
    parser.add_argument("-f", "--force", action="store_true", help="Force reinstall even if already installed")
    parser.add_argument("-s", "--serial", default=None, help="Target device serial")
    args = parser.parse_args()

    adb = find_adb()
    device = args.serial or get_connected_device(adb)
    print(f"============================================================")
    print(f" Shadow Fight 2 — Installation Check & Setup")
    print(f"============================================================")
    print(f" Target Device  : {device}")
    print(f" Target Package : {args.package}")
    print(f" Source APK     : {os.path.basename(args.apk)}")
    print(f"------------------------------------------------------------")

    already_installed = is_installed(package_name=args.package, device=device)

    if already_installed and not args.force:
        print(f"[OK] Package '{args.package}' is already installed on {device}.")
        print(f"     No installation needed. Ready to boot (run 'make boot').")
        return 0

    if already_installed and args.force:
        print(f"[INFO] Package '{args.package}' is currently installed, but --force was specified. Reinstalling...")
    else:
        print(f"[INFO] No installation found for '{args.package}' on {device}.")
        print(f"[*] Starting installation from: {args.apk}")

    success = install_apk(apk_path=args.apk, device=device)
    if success:
        print(f"------------------------------------------------------------")
        print(f"[SUCCESS] '{args.package}' installed successfully on {device}!")
        print(f"          You can now boot the game with: make boot")
        print(f"============================================================")
        return 0
    else:
        print(f"------------------------------------------------------------")
        print(f"[FAILED] Installation of {os.path.basename(args.apk)} failed.", file=sys.stderr)
        print(f"============================================================", file=sys.stderr)
        return 1

if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Common ADB and BlueStacks automation utilities for Shadow Fight 2 (Cat Blasters 9k).
"""

import os
import sys
import subprocess
import time
from typing import Optional, Tuple

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APK_NAME = "SF2_Modded_v6.apk"
DEFAULT_APK = os.path.join(ROOT_DIR, "bluestacks", "apks", APK_NAME)
DEFAULT_PACKAGE = "com.nekki.catblasters"

DEFAULT_ADB_PATHS = [
    r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe",
    r"C:\Program Files (x86)\BlueStacks_nxt\HD-Adb.exe",
    "adb",
]

def find_adb() -> str:
    """Locates the ADB executable."""
    for p in DEFAULT_ADB_PATHS:
        if os.path.isabs(p) and os.path.exists(p):
            return p
    # Fallback to PATH search
    try:
        res = subprocess.run(["where", "adb"], capture_output=True, text=True)
        if res.returncode == 0:
            lines = res.stdout.strip().splitlines()
            if lines:
                return lines[0].strip()
    except Exception:
        pass
    return DEFAULT_ADB_PATHS[0]

def get_connected_device(adb: str) -> Optional[str]:
    """Finds an active device or connects to BlueStacks default port 5555."""
    try:
        res = subprocess.run([adb, "devices"], capture_output=True, text=True, timeout=15)
        lines = res.stdout.strip().splitlines()
        devices = []
        for line in lines[1:]:
            parts = line.strip().split()
            if len(parts) >= 2 and parts[1] == "device":
                devices.append(parts[0])
        
        if devices:
            # Prefer emulator-5554 or 127.0.0.1:5555
            for d in devices:
                if "5554" in d or "5555" in d:
                    return d
            return devices[0]
        
        # If no devices listed, try connecting to BlueStacks default 127.0.0.1:5555
        subprocess.run([adb, "connect", "127.0.0.1:5555"], capture_output=True, text=True, timeout=10)
        res = subprocess.run([adb, "devices"], capture_output=True, text=True, timeout=10)
        for line in res.stdout.strip().splitlines()[1:]:
            parts = line.strip().split()
            if len(parts) >= 2 and parts[1] == "device":
                return parts[0]
    except Exception as e:
        print(f"[Warning] Failed to query devices: {e}", file=sys.stderr)
    return "emulator-5554"

def is_installed(package_name: str = DEFAULT_PACKAGE, device: Optional[str] = None) -> bool:
    """Checks whether the specified Android package is installed on the device."""
    adb = find_adb()
    serial = device or get_connected_device(adb)
    try:
        cmd = [adb]
        if serial:
            cmd += ["-s", serial]
        cmd += ["shell", "pm", "list", "packages", package_name]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        target = f"package:{package_name}"
        for line in res.stdout.splitlines():
            if line.strip() == target:
                return True
    except Exception as e:
        print(f"[Error] Failed checking package installation: {e}", file=sys.stderr)
    return False

def install_apk(apk_path: str = DEFAULT_APK, device: Optional[str] = None) -> bool:
    """Installs or updates the specified APK on the target device."""
    if not os.path.exists(apk_path):
        print(f"[Error] APK file not found at: {apk_path}", file=sys.stderr)
        return False

    adb = find_adb()
    serial = device or get_connected_device(adb)
    print(f"[*] Installing {os.path.basename(apk_path)} on {serial}...")
    try:
        cmd = [adb]
        if serial:
            cmd += ["-s", serial]
        cmd += ["install", "-r", apk_path]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        output = (res.stdout + res.stderr).strip()
        if "Success" in output:
            return True
        else:
            print(f"[Error] Install output:\n{output}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"[Error] Installation command failed: {e}", file=sys.stderr)
        return False

def is_running(package_name: str = DEFAULT_PACKAGE, device: Optional[str] = None) -> bool:
    """Checks if the app package currently has a running process."""
    adb = find_adb()
    serial = device or get_connected_device(adb)
    try:
        cmd = [adb]
        if serial:
            cmd += ["-s", serial]
        cmd += ["shell", "pidof", package_name]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
        return bool(res.stdout.strip())
    except Exception:
        return False

def boot_app(package_name: str = DEFAULT_PACKAGE, device: Optional[str] = None) -> bool:
    """Launches the app on the target device via monkey or am start."""
    adb = find_adb()
    serial = device or get_connected_device(adb)
    try:
        cmd = [adb]
        if serial:
            cmd += ["-s", serial]
        cmd += ["shell", "monkey", "-p", package_name, "-c", "android.intent.category.LAUNCHER", "1"]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        output = (res.stdout + res.stderr).strip()
        if "Events injected: 1" in output or res.returncode == 0:
            return True
        else:
            print(f"[Warning] Monkey launch output:\n{output}", file=sys.stderr)
            return False
    except Exception as e:
        print(f"[Error] Failed to boot app: {e}", file=sys.stderr)
        return False

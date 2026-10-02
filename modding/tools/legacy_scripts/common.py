#!/usr/bin/env python3
"""
Common ADB, Emulator, and Frida automation utilities for Shadow Fight 2.
Fully emulator-agnostic: supports BlueStacks, Redroid (Docker), Waydroid,
Android Studio AVDs, Cuttlefish, and bare-metal Android devices.
"""

import os
import sys
import shutil
import subprocess
import time
from typing import Optional, Tuple

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
APK_NAME = "SF2_Modded_v8.apk"
DEFAULT_APK = os.path.join(ROOT_DIR, "bluestacks", "apks", APK_NAME)
DEFAULT_PACKAGE = "com.nekki.catblasters"
DEFAULT_FRIDA_PORT = 27042

# Known Windows fallback paths (only inspected if system adb is absent)
WINDOWS_ADB_FALLBACKS = [
    r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe",
    r"C:\Program Files (x86)\BlueStacks_nxt\HD-Adb.exe",
]


def find_adb() -> str:
    """
    Locates the ADB executable in an emulator- and OS-agnostic manner:
    1. Checks ADB_PATH / ADB_BIN environment variable.
    2. Searches system PATH via shutil.which('adb') (Linux, macOS, Windows, Docker).
    3. Searches ANDROID_HOME / ANDROID_SDK_ROOT platform-tools.
    4. Searches Windows emulator fallback paths.
    """
    # 1. Explicit environment variable override
    env_adb = os.environ.get("ADB_PATH") or os.environ.get("ADB_BIN")
    if env_adb and os.path.exists(env_adb):
        return env_adb

    # 2. System PATH lookup (universal across Linux, Docker, macOS, Windows)
    path_adb = shutil.which("adb")
    if path_adb:
        return path_adb

    # 3. Android SDK platform-tools
    sdk_root = os.environ.get("ANDROID_HOME") or os.environ.get("ANDROID_SDK_ROOT")
    if sdk_root:
        candidate = os.path.join(sdk_root, "platform-tools", "adb.exe" if sys.platform == "win32" else "adb")
        if os.path.exists(candidate):
            return candidate

    # 4. Windows emulator fallbacks
    if sys.platform == "win32":
        for p in WINDOWS_ADB_FALLBACKS:
            if os.path.exists(p):
                return p

    return "adb"


def get_connected_device(adb: Optional[str] = None) -> Optional[str]:
    """
    Discovers an active Android device or emulator serial:
    1. Checks ANDROID_SERIAL or ADB_DEVICE environment variable.
    2. Queries 'adb devices' and returns the first online device.
    3. Attempts connecting to ADB_CONNECT target (defaults to 127.0.0.1:5555).
    """
    # 1. Environment variable override
    env_serial = os.environ.get("ANDROID_SERIAL") or os.environ.get("ADB_DEVICE")
    if env_serial:
        return env_serial

    adb_bin = adb or find_adb()
    try:
        res = subprocess.run([adb_bin, "devices"], capture_output=True, text=True, timeout=10)
        lines = res.stdout.strip().splitlines()
        devices = []
        for line in lines[1:]:
            parts = line.strip().split()
            if len(parts) >= 2 and parts[1] == "device":
                devices.append(parts[0])

        if devices:
            return devices[0]

        # If no online devices, try auto-connecting to localhost / container target
        target = os.environ.get("ADB_CONNECT", "127.0.0.1:5555")
        subprocess.run([adb_bin, "connect", target], capture_output=True, text=True, timeout=5)
        res = subprocess.run([adb_bin, "devices"], capture_output=True, text=True, timeout=5)
        for line in res.stdout.strip().splitlines()[1:]:
            parts = line.strip().split()
            if len(parts) >= 2 and parts[1] == "device":
                return parts[0]
    except Exception as e:
        print(f"[Warning] Failed to query devices: {e}", file=sys.stderr)

    return None


def get_frida_endpoint() -> Tuple[str, int]:
    """
    Returns (host, port) for Frida Gadget connection.
    Supports remote containers / Docker IP without ADB port forwarding.
    """
    host = os.environ.get("FRIDA_HOST", "127.0.0.1")
    port = int(os.environ.get("FRIDA_PORT", str(DEFAULT_FRIDA_PORT)))
    return host, port


def ensure_frida_port_forward(port: int = DEFAULT_FRIDA_PORT, adb: Optional[str] = None, device: Optional[str] = None) -> bool:
    """
    Ensures ADB port forwarding to Frida Gadget is active if connecting locally.
    Skipped if FRIDA_DIRECT=1 (e.g. Docker container with exposed port).
    """
    if os.environ.get("FRIDA_DIRECT") == "1":
        return True

    adb_bin = adb or find_adb()
    serial = device or get_connected_device(adb_bin)
    try:
        cmd = [adb_bin]
        if serial:
            cmd += ["-s", serial]
        cmd += ["forward", f"tcp:{port}", f"tcp:{port}"]
        subprocess.run(cmd, capture_output=True, timeout=5)
        return True
    except Exception:
        return False


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
    print(f"[*] Installing {os.path.basename(apk_path)} on {serial or 'default device'}...")
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

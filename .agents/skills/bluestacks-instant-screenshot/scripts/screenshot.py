#!/usr/bin/env python3
"""
Instant Screenshot Utility for BlueStacks / Android Emulators.
Captures the raw Android framebuffer in ~300-450ms via direct ADB socket protocol,
bypassing disk I/O on device, avoiding subprocess overhead, and eliminating UTF-16
PowerShell redirection corruption and ADB startup banner noise.
"""

import argparse
import os
import socket
import subprocess
import sys
import time

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    pass

DEFAULT_ADB_PATHS = [
    r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe",
    r"C:\Program Files (x86)\BlueStacks_nxt\HD-Adb.exe",
    "adb",
]

DEFAULT_SERIAL = "emulator-5554"
ADB_HOST = "127.0.0.1"
ADB_PORT = 5037
PNG_HEADER = b"\x89PNG\r\n\x1a\n"


def get_artifact_dir() -> str:
    brain_base = os.path.expanduser(r"~/.gemini/antigravity/brain")
    if os.path.exists(brain_base):
        subdirs = [
            os.path.join(brain_base, d)
            for d in os.listdir(brain_base)
            if os.path.isdir(os.path.join(brain_base, d)) and d != "tempmediaStorage"
        ]
        if subdirs:

            def get_transcript_mtime(d):
                t = os.path.join(d, ".system_generated", "logs", "transcript.jsonl")
                return os.path.getmtime(t) if os.path.exists(t) else 0

            subdirs.sort(key=get_transcript_mtime, reverse=True)
            return subdirs[0]
    return os.getcwd()


ARTIFACT_DIR = get_artifact_dir()


def find_adb_binary() -> str:
    """Finds adb binary in an emulator- and OS-agnostic manner."""
    env_adb = os.environ.get("ADB_PATH") or os.environ.get("ADB_BIN")
    if env_adb and os.path.exists(env_adb):
        return env_adb

    import shutil

    path_adb = shutil.which("adb")
    if path_adb:
        return path_adb

    for p in DEFAULT_ADB_PATHS:
        if os.path.exists(p):
            return p

    return "adb"


def is_server_listening(host: str = ADB_HOST, port: int = ADB_PORT) -> bool:
    """Checks if the ADB daemon is already listening on port 5037."""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(0.2)
    try:
        s.connect((host, port))
        s.close()
        return True
    except Exception:
        return False


def ensure_adb_server(adb_bin: str = None) -> bool:
    """Ensures that the ADB server is listening on port 5037."""
    if is_server_listening():
        return True

    if adb_bin is None:
        adb_bin = find_adb_binary()

    if not os.path.exists(adb_bin) and adb_bin != "adb":
        return False

    # Start server with nodaemon in a detached background process
    creationflags = 0
    if sys.platform == "win32":
        creationflags = 0x08000000  # CREATE_NO_WINDOW

    try:
        subprocess.Popen(
            [adb_bin, "server", "nodaemon"],
            creationflags=creationflags,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except Exception:
        # Fallback to start-server
        subprocess.run([adb_bin, "start-server"], capture_output=True)

    # Wait up to 3 seconds for port to open
    t_end = time.time() + 3.0
    while time.time() < t_end:
        if is_server_listening():
            return True
        time.sleep(0.05)
    return is_server_listening()


def _send_adb_cmd(sock: socket.socket, cmd: str) -> None:
    """Encodes and sends an ADB protocol command (4-hex length + payload) and checks for OKAY."""
    msg = f"{len(cmd):04x}{cmd}".encode()
    sock.sendall(msg)
    resp = sock.recv(4)
    if resp != b"OKAY":
        try:
            err_len_raw = sock.recv(4)
            err_len = int(err_len_raw.decode("utf-8", "ignore"), 16)
            err = sock.recv(err_len).decode("utf-8", "ignore")
        except Exception:
            err = f"Unexpected response: {resp}"
        raise RuntimeError(f"ADB protocol error for command '{cmd}': {err}")


def get_connected_devices() -> list[str]:
    """Queries the ADB server for a list of connected device serials."""
    ensure_adb_server()
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2.0)
    try:
        s.connect((ADB_HOST, ADB_PORT))
        _send_adb_cmd(s, "host:devices")
        length_raw = s.recv(4)
        length = int(length_raw.decode("utf-8", "ignore"), 16)
        raw_devices = s.recv(length).decode("utf-8", "ignore")
        devices = []
        for line in raw_devices.strip().splitlines():
            parts = line.split()
            if len(parts) >= 2 and parts[1] == "device":
                devices.append(parts[0])
        return devices
    finally:
        s.close()


def capture_screenshot_bytes(serial: str = None, timeout: float = 5.0) -> tuple[bytes, float]:
    """
    Captures raw PNG screenshot bytes directly via ADB socket in ~350-450ms.
    Returns: (png_bytes, elapsed_seconds)
    """
    t0 = time.time()
    ensure_adb_server()

    if not serial:
        env_serial = os.environ.get("ANDROID_SERIAL") or os.environ.get("ADB_DEVICE")
        if env_serial:
            serial = env_serial
        else:
            devices = get_connected_devices()
            if devices:
                serial = devices[0]
            else:
                raise RuntimeError(
                    "No active Android device or emulator found on ADB. Ensure an emulator or container is running."
                )

    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((ADB_HOST, ADB_PORT))
        _send_adb_cmd(s, f"host:transport:{serial}")
        _send_adb_cmd(s, "exec:screencap -p")

        chunks = []
        while True:
            chunk = s.recv(65536)
            if not chunk:
                break
            chunks.append(chunk)
    finally:
        s.close()

    raw = b"".join(chunks)
    idx = raw.find(PNG_HEADER)
    if idx == -1:
        raise ValueError(f"No valid PNG signature found in screencap output ({len(raw)} bytes received)")

    png_data = raw[idx:]
    elapsed = time.time() - t0
    return png_data, elapsed


def capture_fallback(serial: str = DEFAULT_SERIAL) -> tuple[bytes, float]:
    """Subprocess fallback using HD-Adb.exe exec-out."""
    t0 = time.time()
    adb = find_adb_binary()
    res = subprocess.run([adb, "-s", serial, "exec-out", "screencap", "-p"], stdout=subprocess.PIPE, check=True)
    idx = res.stdout.find(PNG_HEADER)
    if idx == -1:
        raise ValueError("Invalid PNG received from fallback screencap")
    elapsed = time.time() - t0
    return res.stdout[idx:], elapsed


def save_screenshot(
    output_path: str = None, serial: str = None, crop_box: tuple[int, int, int, int] = None, quiet: bool = False
) -> tuple[str, float]:
    """
    Captures screenshot and writes to output_path.
    If output_path is None, writes to current_screen.png in artifact dir or cwd.
    Returns: (absolute_file_path, elapsed_seconds)
    """
    if not output_path:
        if os.path.exists(ARTIFACT_DIR):
            output_path = os.path.join(ARTIFACT_DIR, "current_screen.png")
        else:
            output_path = os.path.abspath("current_screen.png")
    else:
        output_path = os.path.abspath(output_path)

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    try:
        data, elapsed = capture_screenshot_bytes(serial=serial)
    except Exception as e:
        if not quiet:
            print(f"[Warning] Socket capture failed ({e}), falling back to exec-out...", file=sys.stderr)
        data, elapsed = capture_fallback(serial=serial or DEFAULT_SERIAL)

    if crop_box:
        import io

        from PIL import Image

        img = Image.open(io.BytesIO(data))
        cropped = img.crop(crop_box)
        cropped.save(output_path, "PNG")
    else:
        with open(output_path, "wb") as f:
            f.write(data)

    if not quiet:
        size_kb = len(data) / 1024
        print(f"Captured screenshot in {elapsed * 1000:.1f}ms ({size_kb:.1f} KB) -> {output_path}")

    return output_path, elapsed


def main():
    parser = argparse.ArgumentParser(description="Instantly capture BlueStacks / Android screen in <500ms.")
    parser.add_argument("output", nargs="?", default=None, help="Output PNG path (defaults to current_screen.png)")
    parser.add_argument("-s", "--serial", default=None, help=f"Device serial (default: {DEFAULT_SERIAL})")
    parser.add_argument("--crop", help="Crop box formatted as x1,y1,x2,y2")
    parser.add_argument("-q", "--quiet", action="store_true", help="Suppress console status messages")
    parser.add_argument("--artifact", help="Save directly into conversation artifact directory with this base name")

    args = parser.parse_args()

    crop = None
    if args.crop:
        parts = [int(p.strip()) for p in args.crop.split(",")]
        if len(parts) == 4:
            crop = tuple(parts)

    out_file = args.output
    if args.artifact:
        name = args.artifact if args.artifact.endswith(".png") else f"{args.artifact}.png"
        if os.path.exists(ARTIFACT_DIR):
            out_file = os.path.join(ARTIFACT_DIR, name)
        else:
            out_file = os.path.abspath(name)

    saved_path, elapsed = save_screenshot(output_path=out_file, serial=args.serial, crop_box=crop, quiet=args.quiet)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""
Shadow Fight 2 — Live In-Engine JSON Telemetry & Combat Event Streamer.
Connects directly to the embedded Frida Gadget runtime inside the game process.
Intercepts the master physics loop (FightScene.FixedUpdate) and combat event hooks to stream:
- Character & Opponent HP (decrypted IEEE 754 floats)
- Real-time 3D Vector coordinates (X, Y, Z) via native engine Vector3
- Distance & Spatial Facing direction
- Current movements & animations of both fighters (Player & Opponent)
- Precise Hit Types:
    * Clean hits (body/low damage)
    * Head hits (ShowHeadStrike)
    * Critical hits (ShowCritical)
    * Blocked hits (CallEventBlockHit / IsNoBlock=false)
    * Shock / Disarm (ShowShock)

Usage:
    python ./scripts/stream_telemetry.py             # Stream NDJSON (one JSON line per tick)
    python ./scripts/stream_telemetry.py --pretty    # Stream pretty-printed JSON blocks
    python ./scripts/stream_telemetry.py --hits-only # Only emit JSON when hit events occur
"""

import os
import sys
import time
import json
import argparse
import subprocess
import threading
import frida

def get_frida_endpoint() -> tuple:
    host = os.environ.get("FRIDA_HOST", "127.0.0.1")
    port = int(os.environ.get("FRIDA_PORT", "27042"))
    return host, port

def ensure_frida_port_forward(port: int = 27042):
    if os.environ.get("FRIDA_DIRECT") == "1":
        return
    import shutil
    adb = os.environ.get("ADB_PATH") or os.environ.get("ADB_BIN") or shutil.which("adb")
    if not adb and sys.platform == "win32":
        candidates = [
            r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe",
            r"C:\Program Files (x86)\BlueStacks_nxt\HD-Adb.exe",
        ]
        for c in candidates:
            if os.path.exists(c):
                adb = c
                break
    if not adb:
        adb = "adb"
    serial = os.environ.get("ANDROID_SERIAL") or os.environ.get("ADB_DEVICE")
    cmd = [adb]
    if serial:
        cmd += ["-s", serial]
    cmd += ["forward", f"tcp:{port}", f"tcp:{port}"]
    try:
        subprocess.run(cmd, capture_output=True, timeout=5)
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TELEMETRY_JS_PATH = os.path.join(SCRIPT_DIR, "frida", "telemetry_streamer.js")

def load_telemetry_script() -> str:
    with open(TELEMETRY_JS_PATH, "r", encoding="utf-8") as f:
        return f.read()

def main():
    default_host, default_port = get_frida_endpoint()
    parser = argparse.ArgumentParser(description="Live JSON Telemetry Streamer for Shadow Fight 2.")
    parser.add_argument("--interval", type=float, default=1.0, help="Stream interval in seconds (default: 1.0s). Use 0 for unthrottled live.")
    parser.add_argument("--rate", type=float, default=None, help="Updates per second (Hz). E.g. --rate 1 or --rate 5.")
    parser.add_argument("--live", action="store_true", help="Shortcut for unthrottled 60Hz tick-wise stream (every single physics tick)")
    parser.add_argument("--pretty", action="store_true", help="Pretty-print JSON objects instead of single-line NDJSON")
    parser.add_argument("--hits-only", action="store_true", help="Only stream frames when a hit event occurs")
    parser.add_argument("--log", "--save-log", dest="save_log", nargs="?", const="auto", default=None, help="Store live telemetry in a JSONL file under game-logs/ (auto timestamped if filename omitted)")
    parser.add_argument("--host", type=str, default=default_host, help="Frida Gadget host (default: from FRIDA_HOST or 127.0.0.1)")
    parser.add_argument("--port", type=int, default=default_port, help="Frida Gadget port (default: from FRIDA_PORT or 27042)")
    args = parser.parse_args()

    # Determine effective interval
    if args.live:
        effective_interval = 0.0
    elif args.rate is not None and args.rate > 0:
        effective_interval = 1.0 / args.rate
    else:
        effective_interval = max(0.0, args.interval)

    # Initialize live JSONL logging if requested
    log_file = None
    if args.save_log is not None:
        log_dir = os.path.join(os.getcwd(), "game-logs")
        os.makedirs(log_dir, exist_ok=True)
        if args.save_log == "auto":
            log_filename = f"telemetry_{time.strftime('%Y%m%d_%H%M%S')}.jsonl"
        else:
            log_filename = args.save_log if args.save_log.endswith(".jsonl") else f"{args.save_log}.jsonl"
        log_path = os.path.join(log_dir, log_filename)
        log_file = open(log_path, "a", encoding="utf-8", buffering=1)
        print(f"[*] Live logging active: {log_path}", file=sys.stderr)

    ensure_frida_port_forward(args.port)

    print(f"Connecting to Frida Gadget on {args.host}:{args.port}...", file=sys.stderr)
    try:
        device_manager = frida.get_device_manager()
        device = device_manager.add_remote_device(f"{args.host}:{args.port}")
        session = device.attach("Gadget")
    except Exception as e:
        if log_file:
            log_file.close()
        print(f"[ERROR] Could not attach to Frida Gadget: {e}", file=sys.stderr)
        print("Ensure Shadow Fight 2 (SF2_Modded_v8.apk) is running on the target Android device/container.", file=sys.stderr)
        sys.exit(1)

    latest_frame = None
    accumulated_hits = []
    lock = threading.Lock()

    def log_event(event_dict):
        """Always outputs lifecycle events (round_start, round_end) regardless of --hits-only."""
        if args.pretty:
            json_text = json.dumps(event_dict, indent=2)
            print(json_text)
            if log_file is not None:
                log_file.write(json_text + "\n\n")
                log_file.flush()
        else:
            json_text = json.dumps(event_dict)
            print(json_text)
            if log_file is not None:
                log_file.write(json_text + "\n")
                log_file.flush()
        sys.stdout.flush()

    def print_frame(frame, hits):
        if args.hits_only and not hits:
            return
        frame_copy = dict(frame)
        frame_copy["hits"] = hits
        if args.pretty:
            json_text = json.dumps(frame_copy, indent=2)
            print(json_text)
            if log_file is not None:
                log_file.write(json_text + "\n\n")
                log_file.flush()
        else:
            json_text = json.dumps(frame_copy)
            print(json_text)
            if log_file is not None:
                log_file.write(json_text + "\n")
                log_file.flush()
        sys.stdout.flush()

    def on_message(message, data):
        nonlocal latest_frame
        if message["type"] == "send":
            payload = message.get("payload", {})
            msg_type = payload.get("type")
            if msg_type == "EQUIPMENT_INFO":
                event_data = {
                    "event": "equipment_info",
                    "player": payload.get("player", {}),
                    "opponent": payload.get("opponent", {}),
                    "timestamp": payload.get("timestamp", time.time())
                }
                log_event(event_data)
            elif msg_type == "ROUND_START":
                event_data = {
                    "event": "round_start",
                    "round": payload.get("round", 1),
                    "timestamp": payload.get("timestamp", time.time())
                }
                log_event(event_data)
            elif msg_type == "ROUND_END":
                event_data = {
                    "event": "round_end",
                    "round": payload.get("round", 1),
                    "winner": payload.get("winner", "unknown"),
                    "reason": payload.get("reason", "normal"),
                    "timestamp": payload.get("timestamp", time.time())
                }
                log_event(event_data)
            elif msg_type == "TELEMETRY_FRAME":
                del payload["type"]
                new_hits = payload.get("hits", [])
                if effective_interval == 0.0:
                    # Unthrottled direct streaming
                    print_frame(payload, new_hits)
                else:
                    # Thread-safe buffer for interval sampling
                    with lock:
                        if new_hits:
                            accumulated_hits.extend(new_hits)
                        latest_frame = payload
            elif "status" in payload:
                print(f"[*] Engine Attached: {payload['status']} (Base: {payload.get('base')})", file=sys.stderr)
        elif message["type"] == "error":
            print(f"[JS ERROR] {message.get('stack', message)}", file=sys.stderr)

    script = session.create_script(load_telemetry_script())
    script.on("message", on_message)
    script.load()

    mode_desc = "unthrottled 60Hz tick-wise stream" if effective_interval == 0.0 else f"every {effective_interval}s"
    print(f"[SUCCESS] Telemetry streaming ({mode_desc}). Press Ctrl+C to stop.\n", file=sys.stderr)

    try:
        if effective_interval == 0.0:
            while True:
                time.sleep(1.0)
        else:
            waiting_shown = False
            last_printed_tick = -1
            while True:
                time.sleep(effective_interval)
                with lock:
                    if latest_frame is not None:
                        cur_tick = latest_frame.get("tick", -1)
                        if cur_tick != last_printed_tick:
                            hits_snapshot = list(accumulated_hits)
                            accumulated_hits.clear()
                            print_frame(latest_frame, hits_snapshot)
                            last_printed_tick = cur_tick
                            waiting_shown = False
                    elif not waiting_shown:
                        print("[INFO] Connected to engine. Waiting for combat scene to tick...", file=sys.stderr)
                        waiting_shown = True
    except (KeyboardInterrupt, SystemExit):
        print("\nStopping telemetry stream. Goodbye!", file=sys.stderr)
        session.detach()
    finally:
        if log_file is not None and not log_file.closed:
            log_file.close()

if __name__ == "__main__":
    main()

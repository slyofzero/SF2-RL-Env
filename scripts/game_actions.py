#!/usr/bin/env python3
r"""
Shadow Fight 2 — Native In-Engine Game Actions API.
Executes pause, resume, and exit_fight directly via IL2CPP method calls inside Unity's main thread.
Zero ADB or BlueStacks screen taps required. Fully headless-ready.

Usage:
    CLI:
        python scripts/game_actions.py resume
        python scripts/game_actions.py pause
        python scripts/game_actions.py exit
        python scripts/game_actions.py status

    Python API:
        from scripts.game_actions import SF2GameActions
        actions = SF2GameActions()
        actions.connect()
        actions.resume()
        actions.pause()
        actions.exit_fight()
        actions.disconnect()
"""

import os
import sys
import time
import argparse
import subprocess
import threading
from typing import Optional, Dict, Any

try:
    import frida
except ImportError:
    frida = None

ADB_PATH = r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe"
GADGET_PORT = 27042
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
HOOK_JS_PATH = os.path.join(SCRIPT_DIR, "frida", "game_actions.js")


class SF2GameActions:
    """Native controller for Shadow Fight 2 in-fight actions."""

    def __init__(self, port: int = GADGET_PORT):
        self.port = port
        self.session = None
        self.script = None
        self.is_connected = False
        self._action_event = threading.Event()
        self._last_event = None

    def _ensure_port_forward(self):
        """Ensures ADB port forwarding to Frida Gadget is active."""
        if os.path.exists(ADB_PATH):
            try:
                subprocess.run(
                    [ADB_PATH, "forward", f"tcp:{self.port}", f"tcp:{self.port}"],
                    capture_output=True,
                    timeout=5,
                )
            except Exception:
                pass

    def connect(self) -> bool:
        """Connects to Frida Gadget and loads the actions hook."""
        if frida is None:
            raise RuntimeError("Frida package is not installed. Run: uv pip install frida")

        self._ensure_port_forward()

        if not os.path.exists(HOOK_JS_PATH):
            raise FileNotFoundError(f"Frida hook script not found: {HOOK_JS_PATH}")

        with open(HOOK_JS_PATH, "r", encoding="utf-8") as f:
            js_code = f.read()

        try:
            device_manager = frida.get_device_manager()
            device = device_manager.add_remote_device(f"127.0.0.1:{self.port}")
            self.session = device.attach("Gadget")
            self.script = self.session.create_script(js_code)
            self.script.on("message", self._on_message)
            self.script.load()
            # Allow hook to initialize on next frame
            time.sleep(0.3)
            self.is_connected = True
            return True
        except Exception as e:
            print(f"[ERROR] Failed to attach to game engine on port {self.port}: {e}")
            self.is_connected = False
            return False

    def _on_message(self, message: Dict[str, Any], data: Any):
        if message.get("type") == "send":
            payload = message.get("payload", {})
            if isinstance(payload, dict) and payload.get("event") == "action_completed":
                self._last_event = payload
                self._action_event.set()

    def get_status(self) -> Dict[str, Any]:
        """Queries the engine's current state (scene, in_fight, is_paused, tick count)."""
        if not self.is_connected or not self.script:
            raise RuntimeError("Not connected to game engine.")
        return self.script.exports_sync.get_status()

    def pause(self, timeout: float = 2.0) -> bool:
        """Pauses the current fight natively via battleCtrl.OnPauseButton(0)."""
        if not self.is_connected or not self.script:
            raise RuntimeError("Not connected to game engine.")
        self._action_event.clear()
        res = self.script.exports_sync.pause()
        if not res.get("success"):
            print(f"[WARN] Pause command failed: {res.get('error')}")
            return False
        # Wait for execution inside Update() loop
        done = self._action_event.wait(timeout=timeout)
        time.sleep(0.2)
        return done

    def resume(self, timeout: float = 2.0) -> bool:
        """Resumes / unpauses the current fight natively via battleCtrl.OnPauseButton(2)."""
        if not self.is_connected or not self.script:
            raise RuntimeError("Not connected to game engine.")
        self._action_event.clear()
        res = self.script.exports_sync.resume()
        if not res.get("success"):
            print(f"[WARN] Resume command failed: {res.get('error')}")
            return False
        # Wait for execution inside Update() loop
        done = self._action_event.wait(timeout=timeout)
        time.sleep(0.2)
        return done

    def exit_fight(self, timeout: float = 3.0) -> bool:
        """Exits / surrenders the current fight natively via battleCtrl.LPIEJMLPFBF(-1)."""
        if not self.is_connected or not self.script:
            raise RuntimeError("Not connected to game engine.")
        self._action_event.clear()
        res = self.script.exports_sync.exit_fight()
        if not res.get("success"):
            print(f"[WARN] Exit fight command failed: {res.get('error')}")
            return False
        # Wait for execution inside Update() loop
        done = self._action_event.wait(timeout=timeout)
        time.sleep(0.5)
        return done

    def disconnect(self):
        """Detaches from the Frida session."""
        if self.script:
            try:
                self.script.unload()
            except Exception:
                pass
            self.script = None
        if self.session:
            try:
                self.session.detach()
            except Exception:
                pass
            self.session = None
        self.is_connected = False


def main():
    parser = argparse.ArgumentParser(description="Shadow Fight 2 Native Game Actions Controller")
    parser.add_argument("action", choices=["pause", "resume", "exit", "status"], help="Action to execute")
    args = parser.parse_args()

    controller = SF2GameActions()
    print("[INIT] Connecting to game engine...")
    if not controller.connect():
        sys.exit(1)

    try:
        status = controller.get_status()
        print(f"[STATUS] Scene: {status.get('scene')}, In-Fight: {status.get('in_fight')}, Is-Paused: {status.get('is_paused')}, Ticks: {status.get('ticks')}")

        if args.action == "status":
            pass
        elif args.action == "pause":
            print("[ACTION] Triggering native pause...")
            ok = controller.pause()
            print(f"[RESULT] Pause triggered: {ok}")
        elif args.action == "resume":
            print("[ACTION] Triggering native resume...")
            ok = controller.resume()
            print(f"[RESULT] Resume triggered: {ok}")
        elif args.action == "exit":
            print("[ACTION] Triggering native exit / surrender...")
            ok = controller.exit_fight()
            print(f"[RESULT] Exit triggered: {ok}")

        final_status = controller.get_status()
        print(f"[FINAL] Scene: {final_status.get('scene')}, In-Fight: {final_status.get('in_fight')}, Is-Paused: {final_status.get('is_paused')}")
    finally:
        controller.disconnect()


if __name__ == "__main__":
    main()

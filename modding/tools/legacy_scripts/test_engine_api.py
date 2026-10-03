#!/usr/bin/env python3
"""
Shadow Fight 2 — Native In-Engine Telemetry & State Streamer.
Connects directly to the embedded Frida Gadget runtime inside the game process,
intercepts the master physics loop (FightScene.FixedUpdate), decrypts anti-cheat
health floats, tracks fighter ground coordinates, facing directions, and hit events
with sub-millisecond latency.
"""

import sys
import threading
import time

import frida

try:
    from scripts.common import ensure_frida_port_forward, get_frida_endpoint
except ImportError:
    from common import ensure_frida_port_forward, get_frida_endpoint

_, GADGET_PORT = get_frida_endpoint()

JS_TELEMETRY_ENGINE = r"""
'use strict';

var ranges = Process.enumerateRanges('r-x');
var il2cppBase = null;
for (var i = 0; i < ranges.length; i++) {
    if (ranges[i].file && ranges[i].file.path.indexOf('libil2cpp.so') !== -1) {
        il2cppBase = ranges[i].base.sub(0x18b6000);
        break;
    }
}

if (!il2cppBase) {
    send({ error: "Could not find libil2cpp.so base in memory" });
} else {
    send({ status: "IL2CPP Base Found", base: il2cppBase.toString() });

    // Helper: Decrypt CodeStage ObscuredFloat (Anti-Cheat Encrypted Float)
    function decryptObscuredFloat(ptr) {
        try {
            var k = ptr.readS32();
            var v = ptr.add(4).readS32();
            var raw = k ^ v;
            var buf = Memory.alloc(4);
            buf.writeS32(raw);
            return buf.readFloat();
        } catch(e) {
            return 1.0;
        }
    }

    // 1. Hook Master Physics / Combat Tick: FightScene.FixedUpdate (RVA: 0x3237268)
    var fixedUpdateAddr = il2cppBase.add(0x3237268);
    var tick = 0;

    Interceptor.attach(fixedUpdateAddr, {
        onEnter: function(args) {
            try {
                var scene = args[0];
                var battleCtrl = scene.add(0x90).readPointer();
                if (battleCtrl.isNull()) return;

                // 2. Extract Fighters from battleCtrl.IILLHHPGGKA (offset 0x38)
                var listPtr = battleCtrl.add(0x38).readPointer();
                var itemsArray = listPtr.add(0x10).readPointer();
                var f1 = itemsArray.add(0x20).readPointer();
                var f2 = itemsArray.add(0x28).readPointer();

                // 3. Extract Player & Opponent Health Parameters (offset 0x98, 0xA0)
                var p1Param = battleCtrl.add(0x98).readPointer();
                var p2Param = battleCtrl.add(0xA0).readPointer();

                var p1_hp = 1.0;
                var p2_hp = 1.0;
                if (!p1Param.isNull()) {
                    p1_hp = decryptObscuredFloat(p1Param.add(0x15c));
                }
                if (!p2Param.isNull()) {
                    p2_hp = decryptObscuredFloat(p2Param.add(0x15c));
                }

                // 4. Extract Ground Positions & Facing Directions
                var p1_x = 0.0, p1_y = 0.0, p2_x = 0.0, p2_y = 0.0;
                var facing1 = "RIGHT", facing2 = "LEFT", dist = 0.0;

                if (!f1.isNull()) {
                    var comp1 = f1.add(0xE0).readPointer();
                    if (!comp1.isNull()) {
                        var pos1 = comp1.add(0x10).readPointer();
                        if (!pos1.isNull()) {
                            p1_x = pos1.add(0x10).readFloat();
                            p1_y = pos1.add(0x14).readFloat();
                        }
                    }
                }

                if (!f2.isNull()) {
                    var comp2 = f2.add(0xE0).readPointer();
                    if (!comp2.isNull()) {
                        var pos2 = comp2.add(0x10).readPointer();
                        if (!pos2.isNull()) {
                            p2_x = pos2.add(0x10).readFloat();
                            p2_y = pos2.add(0x14).readFloat();
                        }
                    }
                }

                if (p1_x !== 0.0 || p2_x !== 0.0) {
                    facing1 = (p1_x <= p2_x) ? "RIGHT" : "LEFT";
                    facing2 = (p2_x <= p1_x) ? "RIGHT" : "LEFT";
                    dist = Math.abs(p1_x - p2_x);
                }

                tick++;
                // Stream every 3 ticks (~20 updates/second)
                if (tick % 3 === 0) {
                    send({
                        type: "STATE_TICK",
                        tick: tick,
                        player_hp: Math.min(1.0, Math.max(0.0, p1_hp)),
                        opponent_hp: Math.min(1.0, Math.max(0.0, p2_hp)),
                        player_x: p1_x,
                        player_y: p1_y,
                        player_facing: facing1,
                        opponent_x: p2_x,
                        opponent_y: p2_y,
                        opponent_facing: facing2,
                        distance: dist
                    });
                }
            } catch(e) {
                // Ignore transient cleanup transitions
            }
        }
    });

    // 5. Hook Hit Event Triggers in ScreenModel
    // Critical Hit (RVA: 0x355DAB4)
    Interceptor.attach(il2cppBase.add(0x355DAB4), {
        onEnter: function(args) {
            var modelType = args[0].add(0x20).readInt();
            send({ type: "HIT_EVENT", badge: "CRITICAL", target: (modelType === 0 ? "PLAYER" : "OPPONENT") });
        }
    });

    // First Strike (RVA: 0x355DE0C)
    Interceptor.attach(il2cppBase.add(0x355DE0C), {
        onEnter: function(args) {
            var modelType = args[0].add(0x20).readInt();
            send({ type: "HIT_EVENT", badge: "FIRST_STRIKE", target: (modelType === 0 ? "PLAYER" : "OPPONENT") });
        }
    });

    // Shock / Disarm (RVA: 0x355E75C)
    Interceptor.attach(il2cppBase.add(0x355E75C), {
        onEnter: function(args) {
            var modelType = args[0].add(0x20).readInt();
            send({ type: "HIT_EVENT", badge: "SHOCK_DISARM", target: (modelType === 0 ? "PLAYER" : "OPPONENT") });
        }
    });

    // Blocked Hit (RVA: 0x355E6B8)
    Interceptor.attach(il2cppBase.add(0x355E6B8), {
        onEnter: function(args) {
            var isNoBlock = args[1].toInt32();
            if (isNoBlock === 0) {
                send({ type: "HIT_EVENT", badge: "BLOCKED_HIT" });
            }
        }
    });
}
"""


class SF2EngineTelemetry:
    def __init__(self, port=GADGET_PORT):
        self.port = port
        self.session = None
        self.script = None
        self.state = {
            "tick": 0,
            "player_hp": 1.0,
            "opponent_hp": 1.0,
            "player_x": 0.0,
            "player_facing": "RIGHT",
            "opponent_x": 0.0,
            "opponent_facing": "LEFT",
            "distance": 0.0,
            "last_hit": None,
            "hit_time": 0.0,
        }
        self.lock = threading.Lock()
        self._ensure_port_forward()

    def _ensure_port_forward(self):
        ensure_frida_port_forward(self.port)

    def on_message(self, message, data):
        if message["type"] == "send":
            payload = message["payload"]
            msg_type = payload.get("type")

            with self.lock:
                if msg_type == "STATE_TICK":
                    self.state["tick"] = payload.get("tick", 0)
                    self.state["player_hp"] = payload.get("player_hp", 1.0)
                    self.state["opponent_hp"] = payload.get("opponent_hp", 1.0)
                    self.state["player_x"] = payload.get("player_x", 0.0)
                    self.state["player_facing"] = payload.get("player_facing", "RIGHT")
                    self.state["opponent_x"] = payload.get("opponent_x", 0.0)
                    self.state["opponent_facing"] = payload.get("opponent_facing", "LEFT")
                    self.state["distance"] = payload.get("distance", 0.0)
                elif msg_type == "HIT_EVENT":
                    badge = payload.get("badge")
                    target = payload.get("target", "")
                    self.state["last_hit"] = f"{badge} on {target}" if target else badge
                    self.state["hit_time"] = time.time()
                elif "status" in payload:
                    print(f"[*] Engine Status: {payload['status']} (Base: {payload.get('base')})")
        elif message["type"] == "error":
            print(f"[JS ERROR] {message.get('description')}")

    def connect(self, timeout=15):
        print(f"Connecting to Frida Gadget inside Shadow Fight 2 (127.0.0.1:{self.port})...")
        start = time.time()
        while time.time() - start < timeout:
            try:
                device = frida.get_device_manager().add_remote_device(f"127.0.0.1:{self.port}")
                self.session = device.attach("Gadget")
                self.script = self.session.create_script(JS_TELEMETRY_ENGINE)
                self.script.on("message", self.on_message)
                self.script.load()
                print("[SUCCESS] Attached to live game engine! Streaming telemetry.\n")
                return True
            except Exception:
                time.sleep(0.5)
        print(f"[ERROR] Could not connect to game process on port {self.port} within {timeout}s.")
        return False

    def stream(self, duration=30):
        print("=" * 78)
        print(" Shadow Fight 2 — Native In-Engine Telemetry Stream (Phase 1 Verified)")
        print("=" * 78)
        print(f"{'TICK':<6} | {'SHADOW HP':<10} | {'FACING':<7} | {'MONKEY HP':<10} | {'DISTANCE':<9} | {'HIT EVENT'}")
        print("-" * 78)

        start = time.time()
        last_tick = -1

        while time.time() - start < duration:
            with self.lock:
                t = self.state["tick"]
                if t != last_tick and t > 0:
                    last_tick = t
                    p1_hp_str = f"{self.state['player_hp'] * 100:>5.1f}%"
                    p2_hp_str = f"{self.state['opponent_hp'] * 100:>5.1f}%"
                    facing = self.state["player_facing"]
                    dist = f"{self.state['distance']:>6.1f}px" if self.state["distance"] > 0 else "---"

                    hit = ""
                    if time.time() - self.state["hit_time"] < 1.2 and self.state["last_hit"]:
                        hit = f">> {self.state['last_hit']} <<"

                    print(f"{t:<6} | {p1_hp_str:<10} | {facing:<7} | {p2_hp_str:<10} | {dist:<9} | {hit}")
            time.sleep(0.05)


def main():
    duration = 30
    if len(sys.argv) > 1:
        try:
            duration = int(sys.argv[1])
        except ValueError:
            pass

    client = SF2EngineTelemetry()
    if client.connect():
        try:
            client.stream(duration=duration)
        except KeyboardInterrupt:
            print("\n[OK] Stream stopped by user.")


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
r"""
Shadow Fight 2 — Universal In-Engine Action Controller & Speed Harness.
Directly invokes native C++ / IL2CPP functions inside the game engine:
- Master Loop Hook: battleCtrl.FixedUpdate (RVA 0x33F2A54) -> Universal across Dojo & all Fights!
- Player Pointer: battleCtrl + 0xB0 (LAMENNMGPBN)
- Exact Spatial Facing: Calculated via player_x vs opponent_x coordinates
- Action Down: OLKKAIFGGAK.IKPHKLHDNMA (RVA 0x34E90D0)
- Action Up: OLKKAIFGGAK.IJDCCIGHPHJ (RVA 0x34F57E0)
- Movement Halt: IPCACEBFONO.DGLJCGNHLIG (RVA 0x34E1B54) + Stick.ReleaseInput (RVA 0x306A558)
- Simulation Speed: UnityEngine.Time.set_timeScale (RVA 0x3BFB9C0)

Run this interactively in your terminal while in the Dojo or any match:
    python ./scripts/engine_controller.py
"""

import sys
import time
import subprocess
import threading
import frida

ADB_PATH = r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe"
GADGET_PORT = 27042

JS_ENGINE_HARNESS = r"""
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
    send({ error: "Could not locate libil2cpp.so base in memory" });
} else {
    send({ status: "READY", base: il2cppBase.toString() });

    // 1. Native Action Down (OLKKAIFGGAK.IKPHKLHDNMA)
    var actDownAddr = il2cppBase.add(0x34E90D0);
    var actDown = new NativeFunction(actDownAddr, 'void', ['pointer', 'int']);

    // 2. Native Action Up / Release (OLKKAIFGGAK.IJDCCIGHPHJ)
    var actUpAddr = il2cppBase.add(0x34F57E0);
    var actUp = new NativeFunction(actUpAddr, 'void', ['pointer', 'int']);

    // 3. Queue Clear (IPCACEBFONO.DGLJCGNHLIG)
    var clearQueueAddr = il2cppBase.add(0x34E1B54);
    var clearQueueFunc = new NativeFunction(clearQueueAddr, 'void', ['pointer']);

    // 4. Stick Release (Stick.ReleaseInput)
    var getInstanceAddr = il2cppBase.add(0x3068B44);
    var getInstance = new NativeFunction(getInstanceAddr, 'pointer', []);
    var releaseAddr = il2cppBase.add(0x306A558);
    var releaseFunc = new NativeFunction(releaseAddr, 'void', ['pointer']);

    // 5. Simulation Speed (UnityEngine.Time.set_timeScale)
    var setTimeScaleAddr = il2cppBase.add(0x3BFB9C0);
    var setTimeScale = new NativeFunction(setTimeScaleAddr, 'void', ['float']);

    // 6. Universal Master Combat Loop (battleCtrl.FixedUpdate)
    var masterTickAddr = il2cppBase.add(0x33F2A54);

    var playerPtr = null;
    var battleCtrl = null;
    var lastHealthP1 = 1.0;
    var lastHealthP2 = 1.0;
    var isFacingLeft = false;

    // Movement state
    var activeMoveQuad = -1;
    var moveTicksRemaining = 0;
    var isContinuousHold = false;
    var moveJustStarted = false;

    // Fast Movement (Dash / Backflip) state
    var dashPhase = 0; // 0=idle, 1=tap1, 2=gap, 3=tap2_hold
    var dashQuad = 0;
    var dashWaitTicks = 0;

    // Attack combo state machine
    var attackPhase = 0; // 0=idle, 1=strike1, 2=hold_quad_wait, 3=combo_tap_wait
    var currentAttackAct = -1;
    var currentAttackQuad = 0;
    var currentEffectiveQuad = 0;
    var comboTotalTaps = 0;
    var comboTapIndex = 0;
    var comboWaitTicks = 0;
    var holdQuadTicks = 0;

    function decryptObscuredFloat(ptr) {
        try {
            var k = ptr.readS32();
            var v = ptr.add(4).readS32();
            var buf = Memory.alloc(4);
            buf.writeS32(k ^ v);
            return buf.readFloat();
        } catch(e) {
            return 1.0;
        }
    }

    function haltMovement() {
        if (!playerPtr || playerPtr.isNull()) return;
        playerPtr.add(0x220).writeS32(-1);
        actDown(playerPtr, 0);
        try {
            var q = playerPtr.add(0x258).readPointer();
            if (!q.isNull()) clearQueueFunc(q);
        } catch(e) {}
        try {
            var stick = getInstance();
            if (!stick.isNull()) releaseFunc(stick);
        } catch(e) {}
    }

    function resolveQuadrant(quad) {
        if (quad === -2) {
            // Relative Forward
            return isFacingLeft ? 7 : 3;
        } else if (quad === -3) {
            // Relative Backward
            return isFacingLeft ? 3 : 7;
        } else if (quad === -4) {
            // Relative Up-Forward (wd)
            return isFacingLeft ? 8 : 2;
        } else if (quad === -5) {
            // Relative Up-Backward (wa)
            return isFacingLeft ? 2 : 8;
        } else if (quad === -6) {
            // Relative Down-Forward (sd / roll fwd)
            return isFacingLeft ? 6 : 4;
        } else if (quad === -7) {
            // Relative Down-Backward (sa / roll back)
            return isFacingLeft ? 4 : 6;
        }
        return quad;
    }

    Interceptor.attach(masterTickAddr, {
        onEnter: function(args) {
            try {
                battleCtrl = args[0];
                if (battleCtrl.isNull()) return;

                playerPtr = battleCtrl.add(0xB0).readPointer();
                if (playerPtr.isNull()) return;

                // 1. Calculate Real-Time Spatial Facing Direction from Ground Positions
                try {
                    var listPtr = battleCtrl.add(0x38).readPointer();
                    if (!listPtr.isNull()) {
                        var items = listPtr.add(0x10).readPointer();
                        if (!items.isNull()) {
                            var f1 = items.add(0x20).readPointer();
                            var f2 = items.add(0x28).readPointer();
                            var p1_x = 0.0, p2_x = 0.0;
                            if (!f1.isNull()) {
                                var c1 = f1.add(0xE0).readPointer();
                                if (!c1.isNull()) {
                                    var pos1 = c1.add(0x10).readPointer();
                                    if (!pos1.isNull()) p1_x = pos1.add(0x10).readFloat();
                                }
                            }
                            if (!f2.isNull()) {
                                var c2 = f2.add(0xE0).readPointer();
                                if (!c2.isNull()) {
                                    var pos2 = c2.add(0x10).readPointer();
                                    if (!pos2.isNull()) p2_x = pos2.add(0x10).readFloat();
                                }
                            }
                            if (p1_x !== 0.0 || p2_x !== 0.0) {
                                isFacingLeft = (p1_x > p2_x);
                            }
                        }
                    }
                } catch(e) {}

                // 2. Read Health
                var p1Param = battleCtrl.add(0x98).readPointer();
                var p2Param = battleCtrl.add(0xA0).readPointer();
                if (!p1Param.isNull()) lastHealthP1 = decryptObscuredFloat(p1Param.add(0x15c));
                if (!p2Param.isNull()) lastHealthP2 = decryptObscuredFloat(p2Param.add(0xA0));

                // 3. Process Cardinal & Compound Movement (w, a, s, d, wa, wd, sa, sd)
                if (isContinuousHold) {
                    playerPtr.add(0x220).writeS32(activeMoveQuad);
                    if (moveJustStarted) {
                        moveJustStarted = false;
                        actDown(playerPtr, activeMoveQuad);
                    }
                } else if (moveTicksRemaining > 0) {
                    playerPtr.add(0x220).writeS32(activeMoveQuad);
                    if (moveJustStarted) {
                        moveJustStarted = false;
                        actDown(playerPtr, activeMoveQuad);
                    }
                    moveTicksRemaining--;
                    if (moveTicksRemaining === 0) {
                        haltMovement();
                        send({ type: "STEP_DONE", quad: activeMoveQuad });
                        activeMoveQuad = -1;
                    }
                }

                // 4. Process Fast Movements (dd = Dash, aa = Backflip)
                if (dashPhase === 1) {
                    // Tap 1
                    playerPtr.add(0x220).writeS32(dashQuad);
                    actDown(playerPtr, dashQuad);
                    actUp(playerPtr, dashQuad);
                    playerPtr.add(0x220).writeS32(-1);
                    dashWaitTicks = 4; // ~65ms inter-tap interval
                    dashPhase = 2;
                } else if (dashPhase === 2) {
                    dashWaitTicks--;
                    if (dashWaitTicks <= 0) {
                        // Tap 2 & Hold into Dash
                        playerPtr.add(0x220).writeS32(dashQuad);
                        actDown(playerPtr, dashQuad);
                        dashWaitTicks = 18; // Hold dash duration
                        dashPhase = 3;
                    }
                } else if (dashPhase === 3) {
                    dashWaitTicks--;
                    if (dashWaitTicks <= 0) {
                        actUp(playerPtr, dashQuad);
                        playerPtr.add(0x220).writeS32(-1);
                        haltMovement();
                        dashPhase = 0;
                        send({ type: "DASH_DONE", quad: dashQuad });
                    }
                }

                // 5. Process Combat Attacks (Basic, Compound, Multi-hit)
                if (attackPhase === 1) {
                    currentEffectiveQuad = resolveQuadrant(currentAttackQuad);
                    if (currentEffectiveQuad !== 0) {
                        playerPtr.add(0x220).writeS32(currentEffectiveQuad);
                        actDown(playerPtr, currentEffectiveQuad);
                    }
                    actDown(playerPtr, currentAttackAct);
                    actUp(playerPtr, currentAttackAct);

                    comboTapIndex = 1;
                    if (comboTapIndex < comboTotalTaps) {
                        comboWaitTicks = 9; // ~150ms weapon combo window
                        attackPhase = 3;
                    } else {
                        // Hold quadrant across 12 physics frames (~200ms) for the attack to register
                        holdQuadTicks = 12;
                        attackPhase = 2;
                    }
                } else if (attackPhase === 2) {
                    // Hold quadrant state
                    holdQuadTicks--;
                    if (holdQuadTicks <= 0) {
                        if (currentEffectiveQuad !== 0) {
                            actUp(playerPtr, currentEffectiveQuad);
                            playerPtr.add(0x220).writeS32(-1);
                        }
                        attackPhase = 0;
                        send({ type: "ATTACK_EXECUTED", action: currentAttackAct, quad: currentEffectiveQuad, hits: comboTotalTaps });
                    }
                } else if (attackPhase === 3) {
                    // Waiting for next combo tap
                    comboWaitTicks--;
                    if (comboWaitTicks <= 0) {
                        actDown(playerPtr, currentAttackAct);
                        actUp(playerPtr, currentAttackAct);
                        comboTapIndex++;
                        if (comboTapIndex < comboTotalTaps) {
                            comboWaitTicks = 9;
                        } else {
                            holdQuadTicks = 12;
                            attackPhase = 2; // Transition to hold state before releasing
                        }
                    }
                }
            } catch(e) {
                // Ignore transient frame errors
            }
        }
    });

    rpc.exports = {
        stepMove: function(quad, ticks) {
            isContinuousHold = false;
            activeMoveQuad = resolveQuadrant(quad);
            moveTicksRemaining = ticks;
            moveJustStarted = true;
            return true;
        },
        holdMove: function(quad) {
            isContinuousHold = true;
            activeMoveQuad = resolveQuadrant(quad);
            moveJustStarted = true;
            return true;
        },
        stopMove: function() {
            isContinuousHold = false;
            moveTicksRemaining = 0;
            activeMoveQuad = -1;
            moveJustStarted = false;
            dashPhase = 0;
            haltMovement();
            return true;
        },
        triggerDash: function(isFwd) {
            dashQuad = resolveQuadrant(isFwd ? -2 : -3);
            dashPhase = 1;
            return true;
        },
        triggerAttack: function(act, quad, hits) {
            currentAttackAct = act;
            currentAttackQuad = (quad !== undefined) ? quad : 0;
            comboTotalTaps = (hits !== undefined && hits > 1) ? hits : 1;
            comboTapIndex = 0;
            attackPhase = 1;
            return true;
        },
        setTimeScale: function(scale) {
            setTimeScale(scale);
            return true;
        },
        getStatus: function() {
            return {
                connected: playerPtr !== null && !playerPtr.isNull(),
                player_hp: lastHealthP1,
                opponent_hp: lastHealthP2,
                facing_left: isFacingLeft
            };
        }
    };
}
"""

class SF2EngineController:
    def __init__(self, port=GADGET_PORT):
        self.port = port
        self.session = None
        self.script = None
        self.is_connected = False
        self.step_done_event = threading.Event()
        self.dash_done_event = threading.Event()
        self.attack_done_event = threading.Event()

    def connect(self) -> bool:
        print(f"Connecting to Frida Gadget on 127.0.0.1:{self.port}...")
        try:
            device_manager = frida.get_device_manager()
            device = device_manager.add_remote_device(f"127.0.0.1:{self.port}")
            self.session = device.attach("Gadget")
            self.script = self.session.create_script(JS_ENGINE_HARNESS)
            self.script.on("message", self._on_message)
            self.script.load()
            time.sleep(0.4)
            self.is_connected = True
            print("[SUCCESS] Attached to live game engine!\n")
            return True
        except Exception as e:
            print(f"[ERROR] Could not connect to game on port {self.port}: {e}")
            return False

    def _on_message(self, message, data):
        if message["type"] == "send":
            payload = message.get("payload", {})
            p_type = payload.get("type")
            if p_type == "STEP_DONE":
                self.step_done_event.set()
            elif p_type == "DASH_DONE":
                self.dash_done_event.set()
            elif p_type == "ATTACK_EXECUTED":
                self.attack_done_event.set()
        elif message["type"] == "error":
            print(f"[ENGINE-ERR] {message.get('stack', message)}")

    def step(self, quad, ticks=18):
        if not self.is_connected or not self.script:
            return False
        try:
            self.step_done_event.clear()
            self.script.exports_sync.step_move(quad, ticks)
            timeout = (ticks * 0.016) + 0.35
            self.step_done_event.wait(timeout=timeout)
            return True
        except Exception as e:
            print(f"[ERROR] Step failed: {e}")
            return False

    def dash(self, is_fwd=True):
        if not self.is_connected or not self.script:
            return False
        try:
            self.dash_done_event.clear()
            self.script.exports_sync.trigger_dash(is_fwd)
            self.dash_done_event.wait(timeout=0.9)
            return True
        except Exception as e:
            print(f"[ERROR] Dash failed: {e}")
            return False

    def hold(self, quad):
        if not self.is_connected or not self.script:
            return False
        try:
            self.script.exports_sync.hold_move(quad)
            return True
        except Exception as e:
            print(f"[ERROR] Hold failed: {e}")
            return False

    def stop(self):
        if not self.is_connected or not self.script:
            return False
        try:
            self.script.exports_sync.stop_move()
            return True
        except Exception as e:
            print(f"[ERROR] Stop failed: {e}")
            return False

    def attack(self, act_id, quad=0, hits=1):
        if not self.is_connected or not self.script:
            return False
        try:
            self.attack_done_event.clear()
            self.script.exports_sync.trigger_attack(act_id, quad, hits)
            timeout = 0.45 + (hits * 0.35)
            self.attack_done_event.wait(timeout=timeout)
            return True
        except Exception as e:
            print(f"[ERROR] Attack failed: {e}")
            return False

    def set_speed(self, scale):
        if not self.is_connected or not self.script:
            return False
        try:
            self.script.exports_sync.set_time_scale(float(scale))
            return True
        except Exception as e:
            print(f"[ERROR] Set speed failed: {e}")
            return False

    def get_status(self):
        if not self.is_connected or not self.script:
            return None
        try:
            return self.script.exports_sync.get_status()
        except Exception:
            return None

def print_help():
    print("""
============================================================
 Shadow Fight 2 — Universal In-Engine Controller
============================================================
 Works in the DOJO, Tournaments, Survival, & Bosses!
 Direct C++ IL2CPP Engine Execution (Zero Touch Lag)

 Basic Movements:
   w                       - Jump Up
   s                       - Duck / Crouch
   a                       - Step Backward
   d                       - Step Forward

 Compound Movements:
   wd                      - Jump Forward (Up + Forward)
   wa                      - Jump Backward (Up + Backward)
   sd                      - Roll Forward (Down + Forward)
   sa                      - Roll Backward (Down + Backward)

 Fast Movements:
   dd                      - Forward Dash / Hop
   aa                      - Backward Dash / Backflip

 Basic Attacks:
   p                       - Single Neutral Punch / Knife Slash
   pp                      - Double Knife Slash Combo
   k                       - Single Kick
   kk                      - Double Kick Combo

 Compound Attacks: (w/a/s/d + p/k)
   dp                      - Forward Knife Slash
   ap                      - Spinning Back Slash
   sp                      - Low Knife Slash
   wp                      - Upward Rising Slash

   dk                      - Forward Step Kick
   ak                      - Spinning High Back Kick
   sk                      - Low Sweep Kick
   wk                      - Flying Jump Kick

 Double Attacks:
   dpp                     - Forward Double Slash (Super Slash!)
   app                     - Back Double Slash
   spp                     - Low Double Slash
   wpp                     - Upward Double Slash

   dkk                     - Forward Double Kick
   akk                     - Back Double Kick
   skk                     - Low Double Sweep
   wkk                     - Flying Double Kick

 Diagonal Kicks: (w/s)(d/a) + k
   wdk                     - Front Jump Kick (Up + Forward)
   wak                     - Up-Backward Kick (Up + Backward)
   sdk                     - Down-Forward Kick / Slide
   sak                     - Down-Backward Dodge Kick

 Continuous & Speed:
   hold d / hold a         - Continuous walk
   stop                    - Stop immediately
   speed <val>             - Simulation speed scale (e.g. speed 1.0, speed 2.0)
   status                  - Shadow HP & Facing status
   help                    - Show this menu
   q / quit / exit         - Exit
============================================================
""")

def repl():
    controller = SF2EngineController()
    if not controller.connect():
        sys.exit(1)

    print_help()

    while True:
        try:
            user_input = input("SF2-Engine > ").strip().lower()
            if not user_input:
                continue

            # Standardized command without spaces
            compact = user_input.replace(" ", "")

            if compact in ["q", "quit", "exit"]:
                controller.stop()
                print("Exiting engine controller. Goodbye!")
                break

            if compact == "help":
                print_help()
                continue

            if compact == "stop":
                controller.stop()
                print(" -> Movement Stopped & Halted (Neutral)")
                continue

            if compact == "status":
                st = controller.get_status()
                if st:
                    p1_hp = f"{st.get('player_hp', 1.0)*100:.1f}%"
                    facing = "LEFT" if st.get('facing_left') else "RIGHT"
                    print(f" -> Status: Engine Active | Shadow HP: {p1_hp} | Facing: {facing}")
                continue

            if user_input.startswith("speed "):
                parts = user_input.split()
                if len(parts) >= 2:
                    try:
                        val = float(parts[1])
                        controller.set_speed(val)
                        print(f" -> Simulation Speed set to {val}x")
                    except ValueError:
                        print(" -> Invalid speed value. Example: speed 1.5")
                continue

            # Continuous Hold
            if user_input in ["hold right", "hold d"] or compact == "holdd":
                controller.hold(-2)
                print(" -> Holding FORWARD (continuous walk). Type 'stop' to halt.")
                continue
            elif user_input in ["hold left", "hold a"] or compact == "holda":
                controller.hold(-3)
                print(" -> Holding BACKWARD (continuous walk). Type 'stop' to halt.")
                continue

            # 1. Fast Movements (dd = Dash, aa = Backflip)
            if compact in ["dd", "fwd_dash", "dash"]:
                controller.dash(is_fwd=True)
                print(" -> Fast Movement: FORWARD DASH / HOP (dd)")
                continue
            elif compact in ["aa", "back_dash", "backflip"]:
                controller.dash(is_fwd=False)
                print(" -> Fast Movement: BACKWARD DASH / BACKFLIP (aa)")
                continue

            # 2. Compound Movements (wa, wd, sa, sd)
            if compact in ["wd", "dw", "jf", "jump_fwd", "jumpforward"]:
                controller.step(-4, ticks=18)
                print(" -> Compound Movement: JUMP FORWARD (wd)")
                continue
            elif compact in ["wa", "aw", "jb", "jump_back", "jumpbackward"]:
                controller.step(-5, ticks=18)
                print(" -> Compound Movement: JUMP BACKWARD (wa)")
                continue
            elif compact in ["sd", "ds", "rf", "roll_fwd", "rollforward"]:
                controller.step(-6, ticks=22)
                print(" -> Compound Movement: ROLL FORWARD (sd)")
                continue
            elif compact in ["sa", "as", "rb", "roll_back", "rollbackward"]:
                controller.step(-7, ticks=22)
                print(" -> Compound Movement: ROLL BACKWARD (sa)")
                continue

            # 3. Basic Movements (w, a, s, d)
            if compact in ["w", "up", "jump"]:
                controller.step(1, ticks=14)
                print(" -> Basic Movement: JUMP UP (w)")
                continue
            elif compact in ["s", "down", "duck"]:
                controller.step(5, ticks=16)
                print(" -> Basic Movement: DUCK / CROUCH (s)")
                continue
            elif compact in ["a", "left", "back"]:
                controller.step(-3, ticks=18)
                print(" -> Basic Movement: STEP BACKWARD (a)")
                continue
            elif compact in ["d", "right", "fwd", "forward"]:
                controller.step(-2, ticks=18)
                print(" -> Basic Movement: STEP FORWARD (d)")
                continue

            # 4. Double Attacks (dpp, app, skk, wkk, etc.)
            if compact in ["dpp", "fwdpp", "superslash", "super_slash"]:
                controller.attack(9, quad=-2, hits=2)
                print(" -> Double Attack: FORWARD DOUBLE SLASH / SUPER SLASH (dpp)")
                continue
            elif compact in ["app", "backpp"]:
                controller.attack(9, quad=-3, hits=2)
                print(" -> Double Attack: BACK DOUBLE SLASH (app)")
                continue
            elif compact in ["spp", "lowpp", "downpp"]:
                controller.attack(9, quad=5, hits=2)
                print(" -> Double Attack: LOW DOUBLE SLASH (spp)")
                continue
            elif compact in ["wpp", "uppp"]:
                controller.attack(9, quad=1, hits=2)
                print(" -> Double Attack: UPWARD DOUBLE SLASH (wpp)")
                continue

            elif compact in ["dkk", "fwdkk"]:
                controller.attack(10, quad=-2, hits=2)
                print(" -> Double Attack: FORWARD DOUBLE KICK (dkk)")
                continue
            elif compact in ["akk", "backkk"]:
                controller.attack(10, quad=-3, hits=2)
                print(" -> Double Attack: BACK DOUBLE KICK (akk)")
                continue
            elif compact in ["skk", "lowkk", "downkk", "doublesweep"]:
                controller.attack(10, quad=5, hits=2)
                print(" -> Double Attack: LOW DOUBLE SWEEP (skk)")
                continue
            elif compact in ["wkk", "upkk", "jumpdoublekick"]:
                controller.attack(10, quad=1, hits=2)
                print(" -> Double Attack: FLYING DOUBLE KICK (wkk)")
                continue

            # 5. Compound Attacks (wp, ap, sp, dp, wk, ak, sk, dk)
            if compact in ["dp", "fwdp", "fwd_punch", "forwardpunch"]:
                controller.attack(9, quad=-2, hits=1)
                print(" -> Compound Attack: FORWARD KNIFE SLASH (dp)")
                continue
            elif compact in ["ap", "backp", "back_punch", "backpunch"]:
                controller.attack(9, quad=-3, hits=1)
                print(" -> Compound Attack: SPINNING BACK SLASH (ap)")
                continue
            elif compact in ["sp", "downp", "lowpunch", "lowp"]:
                controller.attack(9, quad=5, hits=1)
                print(" -> Compound Attack: LOW KNIFE SLASH (sp)")
                continue
            elif compact in ["wp", "upp", "up_punch", "uppunch"]:
                controller.attack(9, quad=1, hits=1)
                print(" -> Compound Attack: UPWARD RISING SLASH (wp)")
                continue

            elif compact in ["dk", "fwdk", "fwd_kick", "forwardkick"]:
                controller.attack(10, quad=-2, hits=1)
                print(" -> Compound Attack: FORWARD STEP KICK (dk)")
                continue
            elif compact in ["ak", "backk", "back_kick", "backkick"]:
                controller.attack(10, quad=-3, hits=1)
                print(" -> Compound Attack: SPINNING HIGH BACK KICK (ak)")
                continue
            elif compact in ["sk", "downk", "lowkick", "lowk", "sweep"]:
                controller.attack(10, quad=5, hits=1)
                print(" -> Compound Attack: LOW SWEEP KICK (sk)")
                continue
            elif compact in ["wk", "upk", "up_kick", "jumpkick"]:
                controller.attack(10, quad=1, hits=1)
                print(" -> Compound Attack: FLYING JUMP KICK (wk)")
                continue

            # 5b. Diagonal Kicks: (w/s)(d/a)k — Up-Forward, Up-Backward, Down-Forward, Down-Backward
            elif compact in ["wdk", "upfwdk", "frontjumpkick"]:
                controller.attack(10, quad=-4, hits=1)
                print(" -> Diagonal Kick: FRONT JUMP KICK (wdk)")
                continue
            elif compact in ["wak", "upbackk", "upbackkick"]:
                controller.attack(10, quad=-5, hits=1)
                print(" -> Diagonal Kick: UP-BACKWARD KICK (wak)")
                continue
            elif compact in ["sdk", "downfwdk", "slidekick"]:
                controller.attack(10, quad=-6, hits=1)
                print(" -> Diagonal Kick: DOWN-FORWARD KICK / SLIDE (sdk)")
                continue
            elif compact in ["sak", "downbackk", "dodgekick"]:
                controller.attack(10, quad=-7, hits=1)
                print(" -> Diagonal Kick: DOWN-BACKWARD DODGE KICK (sak)")
                continue


            # 6. Basic Attacks & Combos (p, pp, k, kk)
            if compact in ["pp", "doublepunch"]:
                controller.attack(9, quad=0, hits=2)
                print(" -> Basic Combo: DOUBLE PUNCH (pp)")
                continue
            elif compact in ["p", "punch"]:
                controller.attack(9, quad=0, hits=1)
                print(" -> Basic Attack: NEUTRAL PUNCH (p)")
                continue

            elif compact in ["kk", "doublekick"]:
                controller.attack(10, quad=0, hits=2)
                print(" -> Basic Combo: DOUBLE KICK (kk)")
                continue
            elif compact in ["k", "kick"]:
                controller.attack(10, quad=0, hits=1)
                print(" -> Basic Attack: NEUTRAL KICK (k)")
                continue

            else:
                print(f" -> Unknown command: '{user_input}'. Type 'help' for instructions.")

        except (KeyboardInterrupt, EOFError):
            controller.stop()
            print("\nExiting.")
            break

if __name__ == "__main__":
    repl()

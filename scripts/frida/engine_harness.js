'use strict';

/**
 * Shadow Fight 2 — Native In-Engine Action Controller & Speed Harness.
 * Injected into the game process via Frida Gadget (port 27042).
 * Hooks FightScene.FixedUpdate to execute actions synchronously inside the physics tick.
 */

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

    // 1. Native Action Down (OLKKAIFGGAK.IKPHKLHDNMA - RVA 0x34E90D0)
    var actDownAddr = il2cppBase.add(0x34E90D0);
    var actDown = new NativeFunction(actDownAddr, 'void', ['pointer', 'int']);

    // 2. Native Action Up / Release (OLKKAIFGGAK.IJDCCIGHPHJ - RVA 0x34F57E0)
    var actUpAddr = il2cppBase.add(0x34F57E0);
    var actUp = new NativeFunction(actUpAddr, 'void', ['pointer', 'int']);

    // 3. Queue Clear (IPCACEBFONO.DGLJCGNHLIG - RVA 0x34E1B54)
    var clearQueueAddr = il2cppBase.add(0x34E1B54);
    var clearQueueFunc = new NativeFunction(clearQueueAddr, 'void', ['pointer']);

    // 4. Stick Release (Stick.ReleaseInput - RVA 0x306A558)
    var getInstanceAddr = il2cppBase.add(0x3068B44);
    var getInstance = new NativeFunction(getInstanceAddr, 'pointer', []);
    var releaseAddr = il2cppBase.add(0x306A558);
    var releaseFunc = new NativeFunction(releaseAddr, 'void', ['pointer']);

    // 5. Simulation Speed (UnityEngine.Time.set_timeScale - RVA 0x3BFB9C0)
    var setTimeScaleAddr = il2cppBase.add(0x3BFB9C0);
    var setTimeScale = new NativeFunction(setTimeScaleAddr, 'void', ['float']);

    // 6. Native ObscuredFloat decrypt function (ALBJPLAPOBO - RVA 0x1BC1F2C)
    var decryptNative = new NativeFunction(il2cppBase.add(0x1BC1F2C), 'float', ['pointer']);

    // 7. Universal Master Combat Loop (battleCtrl.FixedUpdate - RVA 0x33F2A54)
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
                var opponentPtr = battleCtrl.add(0xB8).readPointer();
                var p1Param = playerPtr.add(0x148).readPointer();
                if (p1Param.isNull()) p1Param = battleCtrl.add(0x10).readPointer();
                var p2Param = (!opponentPtr.isNull()) ? opponentPtr.add(0x148).readPointer() : null;
                if (!p2Param || p2Param.isNull()) p2Param = battleCtrl.add(0x18).readPointer();

                if (!p1Param.isNull()) {
                    var cur1 = decryptNative(p1Param.add(0x208));
                    var max1 = decryptNative(p1Param.add(0xF4));
                    if (max1 > 0) lastHealthP1 = Math.min(1.0, Math.max(0.0, cur1 / max1));
                }
                if (!p2Param.isNull()) {
                    var cur2 = decryptNative(p2Param.add(0x208));
                    var max2 = decryptNative(p2Param.add(0xF4));
                    if (max2 > 0) lastHealthP2 = Math.min(1.0, Math.max(0.0, cur2 / max2));
                }

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

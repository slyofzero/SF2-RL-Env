'use strict';

/**
 * Shadow Fight 2 — Master Tick Controller Hook.
 * Consolidates all physics timing, stepping, freezing, and simulation speed controls:
 * 1. Tick freeze / unfreeze via Interceptor.replace on battleCtrl.FixedUpdate (RVA 0x33F2A54).
 * 2. Deterministic step-by-step frame execution (step N).
 * 3. Simulation speedup (1x - 100x) via UnityEngine.Time.set_timeScale (RVA 0x3BFB9C0).
 * 4. Auto-freeze on fight/round start via ViewerFight.Play (RVA 0x35BE050).
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

    // 1. Native Action Functions
    var actDownAddr = il2cppBase.add(0x34E90D0);
    var actDown = new NativeFunction(actDownAddr, 'void', ['pointer', 'int']);

    var actUpAddr = il2cppBase.add(0x34F57E0);
    var actUp = new NativeFunction(actUpAddr, 'void', ['pointer', 'int']);

    // 2. Simulation Speed (UnityEngine.Time.set_timeScale - RVA 0x3BFB9C0)
    var setTimeScaleAddr = il2cppBase.add(0x3BFB9C0);
    var setTimeScale = new NativeFunction(setTimeScaleAddr, 'void', ['float']);

    // 3. ObscuredFloat Decrypt (ALBJPLAPOBO - RVA 0x1BC1F2C)
    var decryptNative = new NativeFunction(il2cppBase.add(0x1BC1F2C), 'float', ['pointer']);

    // 4. Helper: Decrypt ObscuredInt
    function decryptObscuredInt(ptr) {
        try {
            if (!ptr || ptr.isNull()) return 0;
            var k = ptr.readS32();
            var v = ptr.add(4).readS32();
            return (k ^ v);
        } catch(e) {
            return 0;
        }
    }

    // 5. Master Combat Loop (battleCtrl.FixedUpdate - RVA 0x33F2A54)
    var fixedUpdateAddr = il2cppBase.add(0x33F2A54);
    var origFixedUpdate = new NativeFunction(fixedUpdateAddr, 'void', ['pointer']);

    // State
    var isFrozen = false;
    var ticksBudget = 0;
    var totalTicksExecuted = 0;
    var currentSpeed = 1.0;
    var autoFreezeOnRoundStart = false;

    var battleCtrlPtr = null;
    var pendingAction = null;

    // Helper: Read IL2CPP UTF-16 String
    function readIl2cppString(ptr) {
        try {
            if (!ptr || ptr.isNull()) return null;
            var len = ptr.add(0x10).readS32();
            return ptr.add(0x14).readUtf16String(len);
        } catch(e) {
            return null;
        }
    }

    // Native Vector3 position getter from fighter+0x250 component (RVA 0x342F0CC)
    var getPosFunc = new NativeFunction(il2cppBase.add(0x342F0CC), 'pointer', ['pointer']);

    var p1CurrentMove = "StanceIdle";
    var p2CurrentMove = "StanceIdle";
    var pendingHits = [];
    var lastP1Hp = -1.0;
    var lastP2Hp = -1.0;

    // Hook Animation & Move Selector (PlayMove - RVA 0x34EC600)
    var playMoveAddr = il2cppBase.add(0x34EC600);
    Interceptor.attach(playMoveAddr, {
        onEnter: function(args) {
            try {
                var fighter = args[0];
                var moveDef = args[1];
                if (moveDef.isNull() || !battleCtrlPtr || battleCtrlPtr.isNull()) return;
                var moveName = readIl2cppString(moveDef.add(0x68).readPointer());
                if (!fighter.isNull() && moveName) {
                    var playerPtr = battleCtrlPtr.add(0xB0).readPointer();
                    var oppPtr = battleCtrlPtr.add(0xB8).readPointer();
                    if (!playerPtr.isNull() && fighter.equals(playerPtr)) {
                        p1CurrentMove = moveName;
                    } else if (!oppPtr.isNull() && fighter.equals(oppPtr)) {
                        p2CurrentMove = moveName;
                    }
                }
            } catch(e) {}
        }
    });

    // Hook Hit Badge Event Handlers in ScreenModel
    // Head Hit (RVA 0x355EE8C)
    Interceptor.attach(il2cppBase.add(0x355EE8C), {
        onEnter: function(args) {
            try {
                var isPlayer = (args[0].add(0x20).readInt() === 0);
                pendingHits.push({
                    type: "head_hit",
                    target: isPlayer ? "player" : "opponent",
                    attacker: isPlayer ? "opponent" : "player",
                    damage: 0.0
                });
            } catch(e) {}
        }
    });

    // Critical Hit (RVA 0x355DAB4)
    Interceptor.attach(il2cppBase.add(0x355DAB4), {
        onEnter: function(args) {
            try {
                var isPlayer = (args[0].add(0x20).readInt() === 0);
                pendingHits.push({
                    type: "critical_hit",
                    target: isPlayer ? "player" : "opponent",
                    attacker: isPlayer ? "opponent" : "player",
                    damage: 0.0
                });
            } catch(e) {}
        }
    });

    // Shock / Disarm (RVA 0x355E75C)
    Interceptor.attach(il2cppBase.add(0x355E75C), {
        onEnter: function(args) {
            try {
                var isPlayer = (args[0].add(0x20).readInt() === 0);
                pendingHits.push({
                    type: "shock",
                    target: isPlayer ? "player" : "opponent",
                    attacker: isPlayer ? "opponent" : "player",
                    damage: 0.0
                });
            } catch(e) {}
        }
    });

    // Blocked Hit: CallEventBlockHit (RVA 0x355EDD4)
    Interceptor.attach(il2cppBase.add(0x355EDD4), {
        onEnter: function(args) {
            try {
                var isPlayer = (args[0].add(0x20).readInt() === 0);
                pendingHits.push({
                    type: "blocked_hit",
                    target: isPlayer ? "player" : "opponent",
                    attacker: isPlayer ? "opponent" : "player",
                    damage: 0.0
                });
            } catch(e) {}
        }
    });

    function readState() {
        if (!battleCtrlPtr || battleCtrlPtr.isNull()) {
            return {
                type: "TELEMETRY_FRAME",
                tick: totalTicksExecuted,
                timestamp: Date.now() / 1000.0,
                time_left: 99.0,
                player: {
                    hp: 1.0,
                    x: 0.0,
                    y: 0.0,
                    z: 0.0,
                    facing: "RIGHT",
                    action: "StanceIdle"
                },
                opponent: {
                    hp: 1.0,
                    x: 0.0,
                    y: 0.0,
                    z: 0.0,
                    facing: "LEFT",
                    action: "StanceIdle"
                },
                distance: 0.0,
                hits: [],
                in_fight: false,
                frozen: isFrozen,
                speed: currentSpeed,
                player_hp: 1.0,
                opponent_hp: 1.0
            };
        }

        var p1_hp = 1.0, p2_hp = 1.0;
        var timeLeft = 99.0;
        var p1_x = 0.0, p1_y = 0.0, p1_z = 0.0;
        var p2_x = 0.0, p2_y = 0.0, p2_z = 0.0;
        var p1Facing = "RIGHT";
        var p2Facing = "LEFT";
        var distance = 0.0;

        try {
            var playerPtr = battleCtrlPtr.add(0xB0).readPointer();
            var oppPtr = battleCtrlPtr.add(0xB8).readPointer();

            if (!playerPtr.isNull()) {
                var pParam = playerPtr.add(0x148).readPointer();
                if (!pParam.isNull()) {
                    var curHp = decryptNative(pParam.add(0x208));
                    var maxHp = decryptNative(pParam.add(0xF4));
                    if (maxHp > 0.0) p1_hp = Math.max(0.0, Math.min(1.0, curHp / maxHp));
                }
                var posComp1 = playerPtr.add(0x250).readPointer();
                if (!posComp1.isNull()) {
                    var v1 = getPosFunc(posComp1);
                    if (!v1.isNull()) {
                        p1_x = parseFloat(v1.add(0x10).readFloat().toFixed(2));
                        p1_y = parseFloat(v1.add(0x14).readFloat().toFixed(2));
                        p1_z = parseFloat(v1.add(0x18).readFloat().toFixed(2));
                    }
                }
            }

            if (!oppPtr.isNull()) {
                var oParam = oppPtr.add(0x148).readPointer();
                if (!oParam.isNull()) {
                    var curHp = decryptNative(oParam.add(0x208));
                    var maxHp = decryptNative(oParam.add(0xF4));
                    if (maxHp > 0.0) p2_hp = Math.max(0.0, Math.min(1.0, curHp / maxHp));
                }
                var posComp2 = oppPtr.add(0x250).readPointer();
                if (!posComp2.isNull()) {
                    var v2 = getPosFunc(posComp2);
                    if (!v2.isNull()) {
                        p2_x = parseFloat(v2.add(0x10).readFloat().toFixed(2));
                        p2_y = parseFloat(v2.add(0x14).readFloat().toFixed(2));
                        p2_z = parseFloat(v2.add(0x18).readFloat().toFixed(2));
                    }
                }
            }

            distance = parseFloat(Math.abs(p1_x - p2_x).toFixed(2));
            p1Facing = (p1_x <= p2_x) ? "RIGHT" : "LEFT";
            p2Facing = (p2_x <= p1_x) ? "RIGHT" : "LEFT";

            // Check Damage Deltas
            if (lastP1Hp >= 0.0 && p1_hp < lastP1Hp - 0.0005) {
                var dmg1 = parseFloat((lastP1Hp - p1_hp).toFixed(4));
                var tagged1 = false;
                for (var i = 0; i < pendingHits.length; i++) {
                    if (pendingHits[i].target === "player" && pendingHits[i].damage === 0.0) {
                        pendingHits[i].damage = dmg1;
                        tagged1 = true;
                        break;
                    }
                }
                if (!tagged1) {
                    pendingHits.push({ type: "hit", target: "player", attacker: "opponent", damage: dmg1 });
                }
            }
            if (lastP2Hp >= 0.0 && p2_hp < lastP2Hp - 0.0005) {
                var dmg2 = parseFloat((lastP2Hp - p2_hp).toFixed(4));
                var tagged2 = false;
                for (var j = 0; j < pendingHits.length; j++) {
                    if (pendingHits[j].target === "opponent" && pendingHits[j].damage === 0.0) {
                        pendingHits[j].damage = dmg2;
                        tagged2 = true;
                        break;
                    }
                }
                if (!tagged2) {
                    pendingHits.push({ type: "hit", target: "opponent", attacker: "player", damage: dmg2 });
                }
            }
            lastP1Hp = p1_hp;
            lastP2Hp = p2_hp;

            var preFightPtr = battleCtrlPtr.add(0x198).readPointer();
            if (!preFightPtr.isNull()) {
                var viewerFightPtr = preFightPtr.add(0x80).readPointer();
                if (!viewerFightPtr.isNull()) {
                    var framesLeft = decryptObscuredInt(viewerFightPtr.add(0x90));
                    timeLeft = parseFloat((framesLeft / 60.0).toFixed(2));
                }
            }
        } catch(e) {}

        var hitsBatch = pendingHits.slice(0);
        pendingHits = [];

        return {
            type: "TELEMETRY_FRAME",
            tick: totalTicksExecuted,
            timestamp: Date.now() / 1000.0,
            time_left: timeLeft,
            player: {
                hp: parseFloat(p1_hp.toFixed(4)),
                x: p1_x,
                y: p1_y,
                z: p1_z,
                facing: p1Facing,
                action: p1CurrentMove
            },
            opponent: {
                hp: parseFloat(p2_hp.toFixed(4)),
                x: p2_x,
                y: p2_y,
                z: p2_z,
                facing: p2Facing,
                action: p2CurrentMove
            },
            distance: distance,
            hits: hitsBatch,
            in_fight: true,
            frozen: isFrozen,
            speed: currentSpeed,
            player_hp: parseFloat(p1_hp.toFixed(4)),
            opponent_hp: parseFloat(p2_hp.toFixed(4))
        };
    }

    // Shared In-Memory Process Synchronization Slot for telemetry_streamer
    var sharedTickStateAddr = il2cppBase.add(0x445f000);
    // [0x0]: is_frozen (int32), [0x4]: total_ticks (int32), [0x8]: speed (float)
    sharedTickStateAddr.writeS32(0);
    sharedTickStateAddr.add(4).writeS32(0);
    sharedTickStateAddr.add(8).writeFloat(1.0);

    // Intercept Master Combat Loop
    var customFixedUpdate = new NativeCallback(function(thisPtr) {
        battleCtrlPtr = thisPtr;

        // If not frozen, execute normally at 60 Hz
        if (!isFrozen) {
            totalTicksExecuted++;
            sharedTickStateAddr.writeS32(0);
            sharedTickStateAddr.add(4).writeS32(totalTicksExecuted);
            origFixedUpdate(thisPtr);
            return;
        }

        // When frozen: only execute if ticks are in budget
        if (ticksBudget > 0) {
            // Apply queued action if any
            if (pendingAction !== null) {
                try {
                    var playerPtr = battleCtrlPtr.add(0xB0).readPointer();
                    if (!playerPtr.isNull()) {
                        var pInput = playerPtr.add(0x150).readPointer();
                        if (!pInput.isNull()) {
                            if (pendingAction.quad > 0) actDown(pInput, pendingAction.quad);
                            if (pendingAction.button > 0) actDown(pInput, pendingAction.button);
                        }
                    }
                } catch(e) {}
                pendingAction = null;
            }

            ticksBudget--;
            totalTicksExecuted++;
            // Write updated tick to shared memory so telemetry_streamer knows a tick executed
            sharedTickStateAddr.writeS32(1);
            sharedTickStateAddr.add(4).writeS32(totalTicksExecuted);
            origFixedUpdate(thisPtr);

            if (ticksBudget === 0) {
                var st = readState();
                send({ event: "step_done", total_ticks: totalTicksExecuted, state: st });
            }
        } else {
            // Frozen: ensure flag is 1
            sharedTickStateAddr.writeS32(1);
        }
        // If ticksBudget == 0: skip call, game stays frozen!
    }, 'void', ['pointer']);

    try {
        Interceptor.revert(fixedUpdateAddr);
    } catch(e) {}
    try {
        Interceptor.replace(fixedUpdateAddr, customFixedUpdate);
    } catch(e) {}

    // Auto-freeze on Round Start (ViewerFight.Play - RVA 0x35BE050)
    var roundStartAddr = il2cppBase.add(0x35BE050);
    Interceptor.attach(roundStartAddr, {
        onEnter: function(args) {
            if (autoFreezeOnRoundStart) {
                isFrozen = true;
                ticksBudget = 0;
                sharedTickStateAddr.writeS32(1);
                send({ event: "auto_frozen_on_round_start", state: readState() });
            }
        }
    });

    rpc.exports = {
        freeze: function() {
            isFrozen = true;
            ticksBudget = 0;
            sharedTickStateAddr.writeS32(1);
            return { success: true, frozen: isFrozen };
        },
        unfreeze: function() {
            isFrozen = false;
            ticksBudget = 0;
            sharedTickStateAddr.writeS32(0);
            return { success: true, frozen: isFrozen };
        },
        step: function(numTicks, quad, button) {
            if (!isFrozen) {
                isFrozen = true;
                sharedTickStateAddr.writeS32(1);
            }
            if (quad > 0 || button > 0) {
                pendingAction = { quad: quad, button: button };
            } else {
                pendingAction = null;
            }
            ticksBudget += numTicks;
            return { success: true, budget: ticksBudget };
        },
        setSpeed: function(scale) {
            currentSpeed = scale;
            setTimeScale(scale);
            return { success: true, speed: currentSpeed };
        },
        setAutoFreeze: function(enabled) {
            autoFreezeOnRoundStart = enabled;
            return { success: true, auto_freeze: autoFreezeOnRoundStart };
        },
        getState: function() {
            return readState();
        }
    };
}

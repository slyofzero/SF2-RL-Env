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

    function readState() {
        if (!battleCtrlPtr || battleCtrlPtr.isNull()) {
            return {
                in_fight: false,
                frozen: isFrozen,
                speed: currentSpeed,
                tick: totalTicksExecuted,
                time_left: 99.0,
                player_hp: 1.0,
                opponent_hp: 1.0
            };
        }

        var p1_hp = 1.0, p2_hp = 1.0;
        var timeLeft = 99.0;

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
            }

            if (!oppPtr.isNull()) {
                var oParam = oppPtr.add(0x148).readPointer();
                if (!oParam.isNull()) {
                    var curHp = decryptNative(oParam.add(0x208));
                    var maxHp = decryptNative(oParam.add(0xF4));
                    if (maxHp > 0.0) p2_hp = Math.max(0.0, Math.min(1.0, curHp / maxHp));
                }
            }

            var preFightPtr = battleCtrlPtr.add(0x198).readPointer();
            if (!preFightPtr.isNull()) {
                var viewerFightPtr = preFightPtr.add(0x80).readPointer();
                if (!viewerFightPtr.isNull()) {
                    var framesLeft = decryptObscuredInt(viewerFightPtr.add(0x90));
                    timeLeft = parseFloat((framesLeft / 60.0).toFixed(2));
                }
            }
        } catch(e) {}

        return {
            in_fight: true,
            frozen: isFrozen,
            speed: currentSpeed,
            tick: totalTicksExecuted,
            player_hp: parseFloat(p1_hp.toFixed(4)),
            opponent_hp: parseFloat(p2_hp.toFixed(4)),
            time_left: timeLeft
        };
    }

    // Intercept Master Combat Loop
    var customFixedUpdate = new NativeCallback(function(thisPtr) {
        battleCtrlPtr = thisPtr;

        // If not frozen, execute normally at 60 Hz
        if (!isFrozen) {
            totalTicksExecuted++;
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
            origFixedUpdate(thisPtr);

            if (ticksBudget === 0) {
                var st = readState();
                send({ event: "step_done", total_ticks: totalTicksExecuted, state: st });
            }
        }
        // If ticksBudget == 0: skip call, game stays frozen!
    }, 'void', ['pointer']);

    Interceptor.replace(fixedUpdateAddr, customFixedUpdate);

    // Auto-freeze on Round Start (ViewerFight.Play - RVA 0x35BE050)
    var roundStartAddr = il2cppBase.add(0x35BE050);
    Interceptor.attach(roundStartAddr, {
        onEnter: function(args) {
            if (autoFreezeOnRoundStart) {
                isFrozen = true;
                ticksBudget = 0;
                send({ event: "auto_frozen_on_round_start", state: readState() });
            }
        }
    });

    rpc.exports = {
        freeze: function() {
            isFrozen = true;
            ticksBudget = 0;
            return { success: true, frozen: isFrozen };
        },
        unfreeze: function() {
            isFrozen = false;
            ticksBudget = 0;
            return { success: true, frozen: isFrozen };
        },
        step: function(numTicks, quad, button) {
            if (!isFrozen) {
                isFrozen = true;
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

'use strict';

/**
 * Shadow Fight 2 — Native In-Engine Game Actions Hook.
 * Executes pause, resume, and exit_fight synchronously inside Unity's main-thread Update loop.
 * Zero ADB / screen taps required. Fully headless compatible.
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

    // FCJBEKHDLAF.OANGGKCBAOJ(battleCtrl, int actionId) - RVA 0x33F3AD8
    // actionId: 0 = ButtonPause, 1 = ButtonPauseSurrender, 2 = ButtonPausePlay
    var onButtonAction = new NativeFunction(il2cppBase.add(0x33F3AD8), 'void', ['pointer', 'int']);

    // FCJBEKHDLAF.LPIEJMLPFBF(battleCtrl, int gameOverType) - RVA 0x33EE838
    // gameOverType: -1 = GAME_OVER_SURRENDER
    var surrenderAction = new NativeFunction(il2cppBase.add(0x33EE838), 'void', ['pointer', 'int']);

    var currentScene = null;
    var currentSceneName = "Unknown";
    var battleCtrl = null;
    var preFight = null;
    var isPaused = false;
    var inFight = false;
    var lastUpdateTick = 0;
    var pendingAction = null;
    var actionResult = null;

    // Hook Scene<object>.Update (RVA 0x296FD44) - Runs at 60Hz across all scenes
    var sceneUpdateAddr = il2cppBase.add(0x296FD44);
    Interceptor.attach(sceneUpdateAddr, {
        onEnter: function(args) {
            currentScene = args[0];
            lastUpdateTick++;

            try {
                // Determine active scene type via IL2CPP class reflection
                var klass = currentScene.readPointer();
                var namePtr = klass.add(0x10).readPointer();
                currentSceneName = namePtr.readCString();

                if (currentSceneName === "FightScene") {
                    inFight = true;
                    // In FightScene, 0x90 is battleCtrl (FCJBEKHDLAF) and 0x98 is PreFight
                    var bCtrl = currentScene.add(0x90).readPointer();
                    var pFight = currentScene.add(0x98).readPointer();

                    if (!bCtrl.isNull() && !pFight.isNull()) {
                        battleCtrl = bCtrl;
                        preFight = pFight;

                        // PauseScreen pointer is at preFight + 0x90
                        var pauseScreenPtr = preFight.add(0x90).readPointer();
                        isPaused = (!pauseScreenPtr.isNull());

                        // Execute queued action on the main thread
                        if (pendingAction !== null) {
                            var act = pendingAction;
                            pendingAction = null;

                            if (act === 'pause') {
                                // ButtonPause = 0
                                onButtonAction(battleCtrl, 0);
                                actionResult = { action: 'pause', success: true };
                                send({ event: 'action_completed', action: 'pause', success: true });
                            } else if (act === 'resume') {
                                // ButtonPausePlay = 2
                                onButtonAction(battleCtrl, 2);
                                actionResult = { action: 'resume', success: true };
                                send({ event: 'action_completed', action: 'resume', success: true });
                            } else if (act === 'exit') {
                                // Direct Surrender = -1 (Immediately terminates fight and exits to Map)
                                surrenderAction(battleCtrl, -1);
                                actionResult = { action: 'exit', success: true };
                                send({ event: 'action_completed', action: 'exit', success: true });
                            }
                        }
                    }
                } else {
                    inFight = false;
                    isPaused = false;
                    battleCtrl = null;
                    preFight = null;
                }
            } catch(e) {
                inFight = false;
                isPaused = false;
                battleCtrl = null;
                preFight = null;
            }
        }
    });

    rpc.exports = {
        pause: function() {
            if (!inFight || !battleCtrl || battleCtrl.isNull()) {
                return { success: false, error: "Not in active fight (current scene: " + currentSceneName + ")" };
            }
            actionResult = null;
            pendingAction = 'pause';
            return { success: true, queued: true };
        },
        resume: function() {
            if (!inFight || !battleCtrl || battleCtrl.isNull()) {
                return { success: false, error: "Not in active fight (current scene: " + currentSceneName + ")" };
            }
            actionResult = null;
            pendingAction = 'resume';
            return { success: true, queued: true };
        },
        exitFight: function() {
            if (!inFight || !battleCtrl || battleCtrl.isNull()) {
                return { success: false, error: "Not in active fight (current scene: " + currentSceneName + ")" };
            }
            actionResult = null;
            pendingAction = 'exit';
            return { success: true, queued: true };
        },
        getStatus: function() {
            return {
                scene: currentSceneName,
                in_fight: inFight,
                is_paused: isPaused,
                ticks: lastUpdateTick
            };
        }
    };
}

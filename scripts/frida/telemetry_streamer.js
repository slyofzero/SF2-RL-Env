'use strict';

/**
 * Shadow Fight 2 — Native In-Engine Telemetry & Hit Event Streamer.
 * Injected into the game process via Frida Gadget (port 27042).
 * Intercepts FightScene.FixedUpdate, PlayMove, and ScreenModel hit badges to stream:
 * - Decrypted Player & Opponent HP
 * - Native Vector3 3D positions (X, Y, Z) and distance
 * - Real-time actions / animations of both fighters
 * - Precise hit types: Clean hit, Head hit, Critical hit, Blocked hit, Shock
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

    // Helper: Decrypt CodeStage ObscuredFloat
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

    // Helper: Decrypt CodeStage ObscuredInt
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

    // Helper: Read Item Name from HOOAAGABMBL
    function readItemName(itemPtr) {
        if (!itemPtr || itemPtr.isNull()) return null;
        try {
            var strPtr = itemPtr.add(0x18).readPointer();
            return readIl2cppString(strPtr);
        } catch(e) {
            return null;
        }
    }

    // Native Vector3 position getter from fighter+0x250 component (RVA 0x342F0CC)
    var getPosFunc = new NativeFunction(il2cppBase.add(0x342F0CC), 'pointer', ['pointer']);

    // Master combat loop (FightScene.FixedUpdate - RVA 0x33F2A54)
    var masterTickAddr = il2cppBase.add(0x33F2A54);
    var playerPtr = null;
    var opponentPtr = null;

    var p1Name = "Shadow";
    var p2Name = "Opponent";
    var p1Weapon = "Fists";
    var p2Weapon = "Fists";

    var p1CurrentMove = "StanceIdle";
    var p2CurrentMove = "StanceIdle";
    var pendingHits = [];
    var lastP1Hp = -1.0;
    var lastP2Hp = -1.0;
    var tickIndex = 0;

    // 1. Hook Animation & Move Selector (PlayMove - RVA 0x34EC600)
    var playMoveAddr = il2cppBase.add(0x34EC600);
    Interceptor.attach(playMoveAddr, {
        onEnter: function(args) {
            try {
                var fighter = args[0];
                var moveDef = args[1];
                if (moveDef.isNull()) return;
                var moveName = readIl2cppString(moveDef.add(0x68).readPointer());
                if (!fighter.isNull() && moveName) {
                    if (playerPtr && fighter.equals(playerPtr)) {
                        p1CurrentMove = moveName;
                    } else if (opponentPtr && fighter.equals(opponentPtr)) {
                        p2CurrentMove = moveName;
                    }
                }
            } catch(e) {}
        }
    });

    // 2. Hook Hit Badge Event Handlers in ScreenModel
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

    // Blocked Hit: set_IsNoBlock(false) (RVA 0x355E6B8)
    Interceptor.attach(il2cppBase.add(0x355E6B8), {
        onEnter: function(args) {
            try {
                var isNoBlock = args[1].toInt32();
                if (isNoBlock === 0) {
                    var isPlayer = (args[0].add(0x20).readInt() === 0);
                    // Avoid duplicate if CallEventBlockHit also fired
                    var exists = false;
                    for (var i = 0; i < pendingHits.length; i++) {
                        if (pendingHits[i].type === "blocked_hit" && pendingHits[i].target === (isPlayer ? "player" : "opponent")) {
                            exists = true; break;
                        }
                    }
                    if (!exists) {
                        pendingHits.push({
                            type: "blocked_hit",
                            target: isPlayer ? "player" : "opponent",
                            attacker: isPlayer ? "opponent" : "player",
                            damage: 0.0
                        });
                    }
                }
            } catch(e) {}
        }
    });

    // 3. Hook Round Lifecycle Events
    var currentRound = 1;
    var lastBattleCtrl = null;
    var equipmentInfoSent = false;

    // Round Start: ViewerFight.Play (RVA 0x35BE050)
    Interceptor.attach(il2cppBase.add(0x35BE050), {
        onEnter: function(args) {
            try {
                send({
                    type: "ROUND_START",
                    round: currentRound,
                    timestamp: Date.now() / 1000.0
                });
            } catch(e) {}
        }
    });

    // Round End: FCJBEKHDLAF.DBNFJODELLP (RVA 0x33ECBA4)
    Interceptor.attach(il2cppBase.add(0x33ECBA4), {
        onEnter: function(args) {
            try {
                var endType = args[3].toInt32();
                var winner = "unknown";
                var reason = "normal";
                if (endType === 1) { winner = "player"; reason = "knockout"; }
                else if (endType === 2) { winner = "opponent"; reason = "knockout"; }
                else if (endType === 3) { winner = "timeout"; reason = "time_expired"; }
                else if (endType === 4) { reason = "ring_out"; }
                else if (endType === 5) { winner = "draw"; reason = "zero_health"; }

                send({
                    type: "ROUND_END",
                    round: currentRound,
                    winner: winner,
                    reason: reason,
                    timestamp: Date.now() / 1000.0
                });
                currentRound++;
            } catch(e) {}
        }
    });

    // Native ObscuredFloat decrypt function (ALBJPLAPOBO - RVA 0x1BC1F2C)
    var decryptNative = new NativeFunction(il2cppBase.add(0x1BC1F2C), 'float', ['pointer']);
    var getTimeScale = new NativeFunction(il2cppBase.add(0x3BFB998), 'float', []);
    var isGamePaused = false;

    // Hook Pause Dialog Lifecycle: Open (0x2FFE62C, 0x3037428) & Close (0x2FFDFC4)
    Interceptor.attach(il2cppBase.add(0x2FFE62C), {
        onEnter: function(args) { isGamePaused = true; }
    });
    Interceptor.attach(il2cppBase.add(0x3037428), {
        onEnter: function(args) { isGamePaused = true; }
    });
    Interceptor.attach(il2cppBase.add(0x2FFDFC4), {
        onEnter: function(args) { isGamePaused = false; }
    });

    function cleanFighterName(n) {
        return (n || "").replace(/^NAME_/, "");
    }

    // 4. Master Physics Interceptor
    Interceptor.attach(masterTickAddr, {
        onEnter: function(args) {
            try {
                // If game is paused or timeScale is 0, suppress all frame logs
                if (isGamePaused || getTimeScale() === 0.0) {
                    return;
                }

                var battleCtrl = args[0];
                if (battleCtrl.isNull()) return;

                if (!lastBattleCtrl || !lastBattleCtrl.equals(battleCtrl)) {
                    lastBattleCtrl = battleCtrl;
                    currentRound = 1;
                    equipmentInfoSent = false;
                    isGamePaused = false;
                }

                playerPtr = battleCtrl.add(0xB0).readPointer();
                opponentPtr = battleCtrl.add(0xB8).readPointer();
                if (playerPtr.isNull() || opponentPtr.isNull()) return;

                // Read and Decrypt Real Health and Equipment from fighter+0x148 (PJKHAJKEHEL)
                var p1Param = playerPtr.add(0x148).readPointer();
                if (p1Param.isNull()) p1Param = battleCtrl.add(0x10).readPointer();
                var p2Param = opponentPtr.add(0x148).readPointer();
                if (p2Param.isNull()) p2Param = battleCtrl.add(0x18).readPointer();

                // Emit singular EQUIPMENT_INFO at start before frames
                if (!equipmentInfoSent && !p1Param.isNull() && !p2Param.isNull()) {
                    var p1N = readIl2cppString(p1Param.add(0x188).readPointer()) || "Shadow";
                    var p1W = readItemName(p1Param.add(0xC0).readPointer()) || "Fists";
                    var p1A = readItemName(p1Param.add(0xC8).readPointer()) || "None";
                    var p1H = readItemName(p1Param.add(0xD0).readPointer()) || "None";
                    var p1R = readItemName(p1Param.add(0xD8).readPointer()) || "NoRanged";
                    var p1M = readItemName(p1Param.add(0xE0).readPointer()) || "NoMagic";

                    var p2N = readIl2cppString(p2Param.add(0x188).readPointer()) || "Opponent";
                    var p2W = readItemName(p2Param.add(0xC0).readPointer()) || "Fists";
                    var p2A = readItemName(p2Param.add(0xC8).readPointer()) || "None";
                    var p2H = readItemName(p2Param.add(0xD0).readPointer()) || "None";
                    var p2R = readItemName(p2Param.add(0xD8).readPointer()) || "NoRanged";
                    var p2M = readItemName(p2Param.add(0xE0).readPointer()) || "NoMagic";

                    send({
                        type: "EQUIPMENT_INFO",
                        timestamp: Date.now() / 1000.0,
                        player: {
                            name: cleanFighterName(p1N),
                            weapon: p1W,
                            armor: p1A,
                            helm: p1H,
                            ranged: p1R,
                            magic: p1M
                        },
                        opponent: {
                            name: cleanFighterName(p2N),
                            weapon: p2W,
                            armor: p2A,
                            helm: p2H,
                            ranged: p2R,
                            magic: p2M
                        }
                    });
                    equipmentInfoSent = true;
                }

                var p1_hp = 1.0, p2_hp = 1.0;
                if (!p1Param.isNull()) {
                    var cur1 = decryptNative(p1Param.add(0x208));
                    var max1 = decryptNative(p1Param.add(0xF4));
                    if (max1 > 0) p1_hp = Math.min(1.0, Math.max(0.0, cur1 / max1));
                }
                if (!p2Param.isNull()) {
                    var cur2 = decryptNative(p2Param.add(0x208));
                    var max2 = decryptNative(p2Param.add(0xF4));
                    if (max2 > 0) p2_hp = Math.min(1.0, Math.max(0.0, cur2 / max2));
                }

                // First tick baseline initialization
                if (lastP1Hp < 0) { lastP1Hp = p1_hp; lastP2Hp = p2_hp; }

                // Check Damage Deltas
                if (p1_hp < lastP1Hp - 0.0005) {
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
                        pendingHits.push({
                            type: "hit",
                            target: "player",
                            attacker: "opponent",
                            damage: dmg1
                        });
                    }
                }
                if (p2_hp < lastP2Hp - 0.0005) {
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
                        pendingHits.push({
                            type: "hit",
                            target: "opponent",
                            attacker: "player",
                            damage: dmg2
                        });
                    }
                }
                lastP1Hp = p1_hp;
                lastP2Hp = p2_hp;

                // Read 3D Vector Positions via native Vector3 struct
                var p1_x = 0.0, p1_y = 0.0, p1_z = 0.0;
                var p2_x = 0.0, p2_y = 0.0, p2_z = 0.0;
                var posComp1 = playerPtr.add(0x250).readPointer();
                var posComp2 = opponentPtr.add(0x250).readPointer();
                if (!posComp1.isNull() && !posComp2.isNull()) {
                    var v1 = getPosFunc(posComp1);
                    var v2 = getPosFunc(posComp2);
                    if (!v1.isNull() && !v2.isNull()) {
                        p1_x = parseFloat(v1.add(0x10).readFloat().toFixed(2));
                        p1_y = parseFloat(v1.add(0x14).readFloat().toFixed(2));
                        p1_z = parseFloat(v1.add(0x18).readFloat().toFixed(2));
                        p2_x = parseFloat(v2.add(0x10).readFloat().toFixed(2));
                        p2_y = parseFloat(v2.add(0x14).readFloat().toFixed(2));
                        p2_z = parseFloat(v2.add(0x18).readFloat().toFixed(2));
                    }
                }

                var distance = parseFloat(Math.abs(p1_x - p2_x).toFixed(2));
                var p1Facing = (p1_x <= p2_x) ? "RIGHT" : "LEFT";
                var p2Facing = (p2_x <= p1_x) ? "RIGHT" : "LEFT";

                tickIndex++;

                // Read remaining match round timer from ViewerFight (preFight+0x80)
                var timeLeft = 99.0;
                try {
                    var preFight = battleCtrl.add(0x198).readPointer();
                    if (!preFight.isNull()) {
                        var vf = preFight.add(0x80).readPointer();
                        if (!vf.isNull()) {
                            var framesLeft = decryptObscuredInt(vf.add(0x90));
                            if (framesLeft > 0) {
                                timeLeft = parseFloat((framesLeft / 60.0).toFixed(2));
                            } else {
                                var sec = decryptObscuredInt(vf.add(0xA0));
                                if (sec > 0) {
                                    timeLeft = parseFloat(sec.toFixed(2));
                                }
                            }
                        }
                    }
                } catch(e) {}

                // Stream every single physics tick (60 Hz) or immediately on hit events
                var hasHits = pendingHits.length > 0;
                var hitsBatch = pendingHits.slice(0);
                pendingHits = [];

                send({
                        type: "TELEMETRY_FRAME",
                        tick: tickIndex,
                        timestamp: Date.now() / 1000.0,
                        time_left: timeLeft,
                        player: {
                            hp: parseFloat(Math.min(1.0, Math.max(0.0, p1_hp)).toFixed(4)),
                            x: p1_x,
                            y: p1_y,
                            z: p1_z,
                            facing: p1Facing,
                            action: p1CurrentMove
                        },
                        opponent: {
                            hp: parseFloat(Math.min(1.0, Math.max(0.0, p2_hp)).toFixed(4)),
                            x: p2_x,
                            y: p2_y,
                            z: p2_z,
                            facing: p2Facing,
                            action: p2CurrentMove
                        },
                        distance: distance,
                        hits: hitsBatch
                    });
            } catch(e) {}
        }
    });
}

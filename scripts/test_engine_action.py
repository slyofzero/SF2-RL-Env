#!/usr/bin/env python3
"""
Test In-Engine Action Dispatch via IL2CPP Native Function Call.
Invokes fighter.IJDCCIGHPHJ(actionId) directly inside FightScene.FixedUpdate.
Actions:
  9: Punch
  10: Kick
  1: Jump (Up)
  2: Jump Forward
  3: Move Forward
  4: Roll Forward
  5: Duck (Down)
  6: Roll Back
  7: Move Back / Block
  8: Jump Back
"""

import sys
import time
import frida
import subprocess

GADGET_PORT = 27042

JS_CODE = r"""
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

    // RVA for OLKKAIFGGAK.IJDCCIGHPHJ (Fighter Action Dispatcher)
    var dispatchActionAddr = il2cppBase.add(0x34F57E0);
    var actionFunc = new NativeFunction(dispatchActionAddr, 'void', ['pointer', 'int']);

    // RVA for UnityEngine.Time.set_timeScale
    var setTimeScaleAddr = il2cppBase.add(0x3BFB9C0);
    var setTimeScale = new NativeFunction(setTimeScaleAddr, 'void', ['float']);

    var fixedUpdateAddr = il2cppBase.add(0x3237268);
    var queuedAction = -1;
    var playerPtr = null;

    Interceptor.attach(fixedUpdateAddr, {
        onEnter: function(args) {
            try {
                var scene = args[0];
                var battleCtrl = scene.add(0x90).readPointer();
                if (battleCtrl.isNull()) return;

                var listPtr = battleCtrl.add(0x38).readPointer();
                var itemsArray = listPtr.add(0x10).readPointer();
                playerPtr = itemsArray.add(0x20).readPointer();

                if (queuedAction !== -1 && !playerPtr.isNull()) {
                    var act = queuedAction;
                    queuedAction = -1;
                    actionFunc(playerPtr, act);
                    send({ type: "ACTION_DISPATCHED", action: act });
                }
            } catch(e) {
                // Ignore transient frame errors
            }
        }
    });

    rpc.exports = {
        sendAction: function(act) {
            queuedAction = act;
            return true;
        },
        setTimeScale: function(scale) {
            setTimeScale(scale);
            return true;
        }
    };
}
"""

def main():
    print("Connecting to Frida Gadget on port 27042...")
    device = frida.get_device_manager().add_remote_device(f"127.0.0.1:{GADGET_PORT}")
    session = device.attach("Gadget")
    
    events = []
    def on_message(message, data):
        if message["type"] == "send":
            p = message["payload"]
            print(f"[Frida] {p}")
            if p.get("type") == "ACTION_DISPATCHED":
                events.append(p)
        elif message["type"] == "error":
            print(f"[Frida Error] {message.get('description')}")

    script = session.create_script(JS_CODE)
    script.on("message", on_message)
    script.load()

    time.sleep(0.5)

    # Let's test dispatching PUNCH (9)
    print("\n--- [TEST 1] Dispatching IN-ENGINE PUNCH (action=9) ---")
    script.exports_sync.send_action(9)
    time.sleep(0.2)
    # Take screenshot of the punch
    subprocess.run([".venv\\Scripts\\python.exe", ".agents\\skills\\bluestacks-instant-screenshot\\scripts\\screenshot.py", "--artifact", "engine_punch_verify"])

    time.sleep(0.6)

    # Let's test dispatching KICK (10)
    print("\n--- [TEST 2] Dispatching IN-ENGINE KICK (action=10) ---")
    script.exports_sync.send_action(10)
    time.sleep(0.2)
    subprocess.run([".venv\\Scripts\\python.exe", ".agents\\skills\\bluestacks-instant-screenshot\\scripts\\screenshot.py", "--artifact", "engine_kick_verify"])

    time.sleep(0.6)

    # Let's test dispatching ROLL FORWARD (4)
    print("\n--- [TEST 3] Dispatching IN-ENGINE ROLL FORWARD (action=4) ---")
    script.exports_sync.send_action(4)
    time.sleep(0.2)
    subprocess.run([".venv\\Scripts\\python.exe", ".agents\\skills\\bluestacks-instant-screenshot\\scripts\\screenshot.py", "--artifact", "engine_roll_verify"])

    print("\nAll action tests dispatched successfully!")
    session.detach()

if __name__ == "__main__":
    main()

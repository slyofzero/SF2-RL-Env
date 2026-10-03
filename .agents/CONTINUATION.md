# CONTINUATION.md — Shadow Fight 2 RL Environment Handoff
> **Last updated**: 2026-09-30 20:00 IST  
> **Status**: SF2_Modded_v3.apk built & verified live in BlueStacks with VIP Unlimited Energy.  
> **Current Installed APK**: `SF2_Modded_v3.apk` (333.20 MB)  
> **Target Package**: `com.nekki.catblasters` on BlueStacks `emulator-5554`

---

## 1. Executive Summary & Status

### The Winning Architecture (v3 APK + External Harness Tap)
1. **`SF2_Modded_v3.apk` is the active milestone build**:
   - Built on top of pristine `SF2_Modded_v2.apk`.
   - Direct boot from Splash $\to$ Loader $\to$ **Act 1 Tournament Map (Scene 5)** in ~10 seconds.
   - Stage 1/24 (Monkey) is automatically selected.
   - The **"FIGHT!"** button is rendered and waiting at coordinates `(1632, 864)`.
   - **VIP Unlimited Energy**: Top-left energy bar displays permanent winged lightning symbol; energy never depletes and fights are never blocked.
2. **Auto-Fight Dispatch**:
   - Dispatched via ADB / RL harness: `adb shell input tap 1632 864`.
   - **Verified Live**: Tapping `(1632, 864)` transitions immediately into the pre-fight screen ("SHADOW vs MONKEY") and into active combat within 2 seconds.

---

## 2. Verified Live State on BlueStacks

- **Package**: `com.nekki.catblasters`
- **Active APK**: `bluestacks/apks/SF2_Modded_v3.apk` (333.20 MB)
- **Energy**: Infinite VIP Unlimited Energy (winged gold icon).
- **Controls**: Full WASD movement, `J` punch, `K` kick (`com.nekki.catblasters.cfg` loaded in BlueStacks InputMapper).
- **Saved Profile**: Level 3, Knives equipped, punchbag & tutorial opponents cleared.
- **Offline Assets**: All 34 offline packs pre-bundled in `/sdcard/Android/data/com.nekki.catblasters/files/gamedata/` — zero CDN download prompts.

---

## 3. The Next Immediate Tasks

### Task 1: Infinite Energy Patch (COMPLETED ✅)
Patched 5 energy routines in `libil2cpp.so` (`0x3063e1c`, `0x344aec8`, `0x305aaa4`, `0x3057bfc`, `0x3057964`) and signed as `SF2_Modded_v3.apk`. Verified live.

### Task 2: Auto-Tap Launcher Harness (Python)
Instead of smali threads, use a clean 10-line Python helper or RL environment `reset()` routine:
```python
import subprocess, time

HD_ADB = r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe"


def start_tournament_fight():
    # 1. Launch game
    subprocess.run(
        [
            HD_ADB,
            "-s",
            "emulator-5554",
            "shell",
            "monkey",
            "-p",
            "com.nekki.catblasters",
            "-c",
            "android.intent.category.LAUNCHER",
            "1",
        ]
    )
    # 2. Wait for map screen (10-12s)
    time.sleep(12)
    # 3. Tap FIGHT! button at (1632, 864)
    subprocess.run([HD_ADB, "-s", "emulator-5554", "shell", "input", "tap", "1632", "864"])
    print("Tournament fight started!")
```

### Task 3: 10,000 Rounds Per Fight
The user requested:
> "change the number of rounds per fight to some extremely high number like 10k"
- In normal Shadow Fight 2 tournament matches, it is "Best of 3" (first to win 2 rounds).
- Search `dump.cs` for round count fields in:
  - `FightManager`
  - `BattleConfig` / `CombatConfig`
  - Or in the game data XML (`ZONE_1` tournament battle definitions).
- Patching the win threshold or max rounds to `10000` (`0x2710`) will allow endless continuous sparring for RL training without returning to the map.

---

## 4. Key File & Environment References

| Item | Path / Value |
|---|---|
| Python .venv | `c:\Users\Ishan\Personal\Porfolio\Shadow Fight 2\.venv\Scripts\python.exe` |
| ADB Binary | `C:\Program Files\BlueStacks_nxt\HD-Adb.exe` (always pass `-s emulator-5554`) |
| Baseline v2 APK | `bluestacks/apks/SF2_Modded_v2.apk` (Protected baseline) |
| Build Script | `modding/pipeline/build_cat_blasters.py` |
| IL2CPP Dump | `modding/build_cache/il2cpp_dump/dump.cs` |
| Target FIGHT Button | (x=1632, y=864) in 1920x1080 resolution |

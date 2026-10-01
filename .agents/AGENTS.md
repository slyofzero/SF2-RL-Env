# AGENTS.md - Shadow Fight 2 RL & Modding Environment

Welcome to the **Shadow Fight 2 Reinforcement Learning Environment** repository. This document serves as the single source of truth for AI agents, developers, and researchers working on reverse engineering, modding, and interfacing Shadow Fight 2 with an RL training harness.

---

## 0. Agent Rules of Engagement: Development & Operational Protocol

> [!IMPORTANT]
> **MANDATORY FOR ALL AGENTS AND CONTRIBUTORS**:
> Documentation and strict development discipline in this repository are **not optional or post-hoc**—they are the default operational loop. Every agent interacting with this workspace MUST adhere to the following rules:
>
> 1. **Single Goal Focus**: Only work towards **one goal per prompt**. If a user prompt specifies too many goals bundled together, decline with a proper, courteous explanation and ask the user to pick which single goal to tackle first.
> 2. **User-Friendly High-Level Feedback**: Throughout development and across all responses, provide clear, high-level, user-friendly feedback about what was accomplished. Avoid overwhelming the user with arcane technical jargon, raw hex dumps, or excessive internal details.
> 3. **Visual Verification via Instant Screenshot**: To test and verify game behaviors, screens, menus, and combat, ALWAYS take screenshots using the `bluestacks-instant-screenshot` skill (`.agents/skills/bluestacks-instant-screenshot/scripts/screenshot.py --artifact <name>`) and show the resulting screenshot to the user for visual confirmation.
> 4. **Fail-Fast & Transparent Obstacle Reporting**: Never aimlessly keep trying towards a failing goal. If you encounter too many obstacles or an approach hits a brick wall, stop immediately and explain to the user what isn't working, why, and what alternative solutions exist.
> 5. **Strict 20-Minute Step Limit & Mandatory ETA**: Each development step must NOT exceed **20 minutes**. Always provide an upfront ETA before beginning. If a task or build process might exceed 20 minutes, notify the user immediately and seek alignment before proceeding.
> 6. **Check Before Acting**: Before executing an exploratory script, reverse engineering tool, or APK repack, review the **Experimentation & Research Log (Section 7)** below to avoid repeating known failures.
> 7. **Document Every Experiment**: Whenever you try a new approach, reverse engineering tool, asset modification, memory scan, or hooking technique, record:
>    * **What was tried** (exact command, file modified, tool used).
>    * **What worked** (verified observable outputs, successful builds).
>    * **What failed & why** (exact error messages, root-cause analysis, and how to avoid it).
> 8. **Keep Architecture & Layout Synced**: If any file, directory, or script path changes, immediately update the directory tree in Section 2 and the respective sub-module README.
> 9. **APK Versioning & Immutability Protocol**: `SF2_Modded_v1.apk` and `SF2_Modded_v2.apk` are immutable baseline milestones. They MUST NEVER be overwritten, replaced, or deleted. Any future modifications, asset changes, or binary patches MUST create a new versioned APK (`SF2_Modded_v3.apk`, `SF2_Modded_v4.apk`, etc.). The original untampered baseline APK is permanently preserved as `SF2_OG.apk`.

---

## 1. Project Vision & Architecture

The objective of this project is to train an autonomous Reinforcement Learning (RL) agent capable of playing *Shadow Fight 2* against various opponents (tournament fighters, bosses, and custom sparring dummies).

Training an RL model in a commercial game requires transforming a black-box mobile game into a standard **OpenAI Gymnasium (`gymnasium.Env`)** interface:
$$\text{Gym Interface}: \quad \text{step}(\mathbf{a}_t) \longrightarrow \left(\mathbf{s}_{t+1}, r_t, d_t, \text{info}\right)$$

### Core Technical Pillars:
1. **The Emulator Runtime (`bluestacks/`)**: An isolated Android runtime hosting the game, accepting action inputs (simulated joystick & button presses) and rendering frames.
2. **The Modding Pipeline (`modding/`)**: Asset extraction, patching, and signature injection to bypass restrictions (timer freezes, custom sparring opponents, endless rounds, visual indicators).
3. **The RL Interface (`rl_env/` - Upcoming)**: High-speed state capture, reward calculation, and action space dispatch.

---

## 2. Directory Layout

```text
Shadow Fight 2/
├── .agents/                           <-- Agent configuration, rules & reusable skills
│   ├── AGENTS.md                      <-- Comprehensive documentation (this file)
│   └── skills/                        <-- Reusable modding & reversing skills
│       ├── unity-texture-modding/     <-- UnityPy texture extraction & injection
│       ├── apk-split-merger/          <-- XAPK / split APK to monolithic merger
│       ├── il2cpp-binary-patcher/     <-- ARM64 IL2CPP assembly patcher
│       ├── apk-offline-asset-provisioner/ <-- Offline DLC & save self-extractor
│       ├── apk-rebranding-identity/   <-- Custom title, icon, & package rebrander
│       ├── bluestacks-game-harness/   <-- BlueStacks ADB & keymapper harness
│       ├── bluestacks-instant-screenshot/ <-- Sub-second ADB socket screen capture
│       └── game-content-downloader/   <-- Automated CDN & emulator pack downloader
├── Makefile                           <-- Automation Makefile (make install, make boot)
├── make.bat                           <-- Windows CMD/PowerShell make wrapper
├── scripts/                           <-- Lifecycle & ADB automation scripts
│   ├── common.py                      <-- Shared ADB detection, install & launch logic
│   ├── install.py                     <-- Checks installation & installs APK if missing
│   ├── boot.py                        <-- Checks installation & boots game
│   ├── tap.py                         <-- Interactive ADB touch/tap helper
│   ├── engine_controller.py           <-- Native IL2CPP action controller (Frida RPC)
│   ├── test_engine_api.py             <-- Live telemetry streamer (HP, position, hit events)
│   ├── stream_telemetry.py            <-- Live JSON telemetry & hit event streamer (NDJSON/Pretty)
│   └── frida/                         <-- Standalone JavaScript hooks loaded by Python
│       ├── engine_harness.js          <-- Action controller & physics tick hook
│       └── telemetry_streamer.js      <-- HP, 3D Vector3 positions, moves & hit badges
├── README.md                          <-- Quick-start overview
├── .venv/                             <-- Isolated Python 3.12 environment (uv managed)
│
├── bluestacks/                        <-- BLUESTACKS RUNTIME & APKS
│   ├── README.md                      <-- Emulator setup & configuration guide
│   ├── apks/                          <-- Ready-to-install standalone APKs
│   │   ├── SF2_OG.apk                 (162.75 MB - Untampered base game)
│   │   ├── SF2_Modded_v1.apk          (333.23 MB - Protected v1 milestone build)
│   │   ├── SF2_Modded_v2.apk          (333.23 MB - Protected v2 Act 1 Map boot build)
│   │   ├── SF2_Modded_v3.apk          (333.20 MB - Act 1 Map boot + VIP Infinite Energy build)
│   │   ├── SF2_Modded_v4.apk          (333.23 MB - Configurable arbitrary round control build: N rounds per match)
│   │   ├── SF2_Modded_v5.apk          (333.23 MB - Dojo sparring restoration build: native Dojo startup scene)
│   │   ├── SF2_Modded_v6.apk          (333.23 MB - Act 1 Map cold boot + Dojo menu restoration build)
│   │   ├── SF2_Modded_v7.apk          (342.91 MB - Embedded Frida Gadget milestone build)
│   │   ├── SF2_Modded_v8.apk          (342.90 MB - Unconditional Frida Gadget load on every boot)
│   │   └── SF2_Modded_v9.apk          (Target for future modded builds)
│   └── scripts/
│       └── install_apk.ps1            <-- PowerShell helper for automated ADB installs
│
└── modding/                           <-- MODDING & REVERSE ENGINEERING PIPELINE
    ├── README.md                      <-- Master documentation hub & quick-reference
    ├── docs/                          <-- In-depth technical guides by subsystem
    │   ├── 01_ARCHITECTURE_OVERVIEW.md
    │   ├── 02_TEXTURES_AND_GRAPHICS.md
    │   ├── 03_IL2CPP_AND_BINARY_PATCHING.md
    │   ├── 04_SAVE_PROFILES_AND_PROGRESSION.md
    │   ├── 05_OFFLINE_BUNDLES_AND_CDN.md
    │   ├── 06_STARTUP_SMALI_HOOK.md
    │   ├── 07_BUILD_AND_SIGNING_PIPELINE.md
    │   └── 08_ENGINE_CONTROLLER_AND_RL_HARNESS.md
    ├── packages/                      <-- Upstream and repacked packages
    │   ├── Shadow+Fight+2_2.46.0_APKPure.xapk      (Original multi-split XAPK)
    │   └── Shadow_Fight_2_Modded_Cyberpunk.xapk    (Modified multi-split XAPK)
    ├── pipeline/                      <-- Core automation scripts
    │   ├── build_cat_blasters.py      <-- Master builder, patcher, & signer
    │   ├── build_standalone_apk.py    <-- Split-to-monolithic APK builder & signer
    │   └── download_all_story_packs.py<-- Multi-threaded CDN pack downloader
    ├── assets/                        <-- Extracted & modified game textures, saves, & packs
    │   ├── downloaded_gamedata/       <-- 30 pre-bundled packages & packs.xml
    │   ├── userdata/                  <-- Pre-configured completed save & hashes
    │   ├── icons/                     <-- Custom launcher artwork (cat_blasters_icon_512.png)
    │   └── dummy_intro.mp4            <-- Instant-skip 0.04s video replacement
    └── tools/                         <-- Signing keys, dumpers, and packaging binaries
        ├── apktool.jar                <-- Manifest and resource decompiler/rebuilder
        ├── uber-apk-signer.jar        <-- Auto-zipalign & v1/v2/v3 signer
        ├── smali.jar                  <-- Smali bytecode assembler
        ├── Il2CppDumper/              <-- IL2CPP metadata extractor
        └── debug.keystore             <-- 2048-bit RSA debug keystore
```

---

## 3. Game Engine Architecture (SF2 v2.46.0)

When analyzing the game files, we confirmed that **Shadow Fight 2 v2.46.0 is built on Unity with IL2CPP**:
* **Runtime**: Unity Engine (`libunity.so`).
* **Game Logic Compilation**: Ahead-of-Time compiled C# via IL2CPP (`libil2cpp.so`).
* **Class & Symbol Metadata**: Encrypted/packed metadata table in `assets/bin/Data/Managed/Metadata/global-metadata.dat`.
* **Assets**: Unity Serialized Files and Asset Bundles in `assets/bin/Data/`.

### Why This Architecture Matters:
* **Standardized Formats**: Textures (`Texture2D`), sprites, audio, and text assets can be extracted and injected deterministically using Python (`UnityPy`).
* **IL2CPP Reflection**: All game classes, methods, fields, and memory offsets (`Character`, `Health`, `CombatController`, `FightManager`) can be recovered using metadata dumpers (`Il2CppDumper`).

---

## 4. BlueStacks Setup Guide

### The "Unsupported File Type" Problem & The Solution
* **The Problem**: Dragging an `.xapk` into BlueStacks triggers Android's default file viewer, which rejects `.xapk` as an unhandled file format. Furthermore, an `.xapk` contains **split APKs** (`com.nekki.shadowfight.apk`, `config.arm64_v8a.apk`, `config.armeabi_v7a.apk`). Android cannot install split APKs individually without split-installation tooling.
* **The Solution**: We engineered a merger script (`modding/pipeline/build_standalone_apk.py`) that extracts the architecture libraries (`lib/arm64-v8a` and `lib/armeabi-v7a`) from the config packages and embeds them directly into the base APK. The resulting APKs in `bluestacks/apks/` are **universal, monolithic, standalone APKs** signed with Android v1, v2, and v3 signatures.

### Installation Instructions
1. Launch **BlueStacks 5**.
2. Install the **Original** or **Modded** build:
   * **Method 1 (GUI)**: Drag either `bluestacks/apks/SF2_OG.apk` or `bluestacks/apks/SF2_Modded_v1.apk` directly into the BlueStacks window (or press `Ctrl + Shift + B`).
   * **Method 2 (PowerShell Script)**:
     ```powershell
     # To install modded build (v1):
     .\bluestacks\scripts\install_apk.ps1 -Target v1

     # To install original baseline build:
     .\bluestacks\scripts\install_apk.ps1 -Target original
     ```
   *(Note: If using ADB, enable Android Debug Bridge in BlueStacks: Settings -> Advanced -> Android Debug Bridge = ON).*

---

## 5. Modding Pipeline (Step-by-Step)

The modding pipeline provides fully reproducible workflows for extracting, modifying, and re-signing game assets.

### A. Asset Extraction & Mapping
Unity stores individual assets across hash-named files in `assets/bin/Data/`. The mapping for the starting arena (**The Dojo**) is:

| Unity File in APK | Texture Asset Name | Description |
| :--- | :--- | :--- |
| `assets/bin/Data/a270fac21f3177e428a9c49164a217c2` | `dojo_bg` | Outer mountain panorama (1024x512) |
| `assets/bin/Data/edba0f6b88dea6144baef9415426de20` | `dojo_bg_low` | Low-res fallback mountain panorama |
| `assets/bin/Data/78a8599a4223b28419c1b7417ca03a4d` | `dojo_atlas_layer1` | Cherry blossom tree silhouettes & branches |
| `assets/bin/Data/dd833943f1e94264e9b19dc78c3dd346` | `dojo_atlas_layer2` | Dojo interior room, floor, sliding shoji screens |
| `assets/bin/Data/ca5b9cfa51d2ed44cbbc5daf06b4589d` | `dojo_atlas_layer2_low` | Low-res interior shoji screen layer |
| `assets/bin/Data/835de2e8aa03eb5458bccaa42c4694c2` | `dojo_atlas_layer3` | Doorway sunlight/moonlight beam |
| `assets/bin/Data/a475dfa934fc5384ebc0f36e30bb7b30` | `dojo_atlas_layer3_low` | Low-res light beam layer |

### B. Texture Processing
Color transformations are applied using continuous HSV hue rotations via Pillow:
```python
# Rotate hue by 180 degrees (Warm peach/amber -> Cool Cyan/Sapphire)
h_val = (h_val + 180.0 / 360.0) % 1.0
```

### C. Unity Serialization & APK Signing
1. `UnityPy` re-serializes modified `Texture2D` objects into binary asset streams:
   ```python
   env = UnityPy.load(raw_bytes)
   # ... modify data.image ...
   data.save()
   new_raw_bytes = env.file.save()
   ```
2. `uber-apk-signer.jar` handles 4-byte zip alignment (`zipalign`) and writes APK signature scheme v1, v2, and v3 blocks using `modding/tools/debug.keystore`.

---

## 6. Next Steps: Setting Up the RL Environment

To transition from asset modding to the Reinforcement Learning environment:

### Milestone 1: IL2CPP Metadata Reverse Engineering
* Run `Il2CppDumper` on `libil2cpp.so` + `global-metadata.dat`.
* Generate `dump.cs` to locate:
  * `FightManager` / `BattleController`
  * `CharacterHealth` / `DamageReceiver`
  * `RoundTimer` / `TimerComponent`
  * `VirtualJoystick` / `InputReceiver`

### Milestone 2: Endless Sparring / Soft Reset Hook
* Identify the memory address of the match timer and freeze it at `99.0` (infinite time).
* Implement a soft episode reset: when `player_hp <= 0` or `enemy_hp <= 0`, rewrite HP to `1.0` in memory, bypassing the 15-second victory/defeat animation.

### Milestone 3: Gymnasium Environment (`ShadowFightEnv`)
* **Action Space**: `MultiDiscrete([9 directions, 3 button actions])` dispatched via virtual key injection into BlueStacks.
* **Observation Space**: High-frequency DXcam screen capture (stacked 84x84 grayscale frames) + Vector states (HP, player distance).
* **Reward Shaping**: Continuous damage delta, head-hit bonuses, critical bonuses, and time penalties.

---

## 7. Experimentation & Research Log (Living Document)

This log tracks every experiment, tool, and modification attempted in this workspace. All agents MUST append new entries when conducting experiments.

| # | What Was Tried | Outcome | What Worked | What Failed & Root Cause |
| :- | :--- | :--- | :--- | :--- |
| **01** | Global `pip install UnityPy` | ❌ Denied | User explicitly requested no global python package installs. | Global environment pollution prevented by user intervention. |
| **02** | Local environment creation via `uv venv .venv` | ✅ Succeeded | Created an isolated Python 3.12 virtual environment (`.venv`). Installed `UnityPy`, `Pillow`, `androguard`. | None. |
| **03** | Unpack and inspect `Shadow+Fight+2_2.46.0_APKPure.xapk` | ✅ Succeeded | Discovered game is built on **Unity + IL2CPP** (`libil2cpp.so` + `global-metadata.dat`). | Raw `.xapk` format is unsupported by standard Android installers. |
| **04** | Extracting Dojo textures using `UnityPy` | ✅ Succeeded | Located and extracted `dojo_bg`, `dojo_atlas_layer1`, `layer2`, `layer3`, and `moon_bg`. | Unity asset names are stored in hash-named serial files in `assets/bin/Data/`. |
| **05** | Dragging raw `.xapk` into BlueStacks | ❌ Failed | None. | BlueStacks Android file viewer rejected `.xapk` as "unsupported file type". |
| **06** | Direct ADB installation via `HD-Adb.exe` | ❌ Failed | ADB daemon started on port 5037. | BlueStacks default config has ADB disabled (`bst.enable_adb_access="0"` in `bluestacks.conf`), closing ADB connection. |
| **07** | Building standalone monolithic APK (`build_standalone_apk.py`) | ✅ Succeeded | Merged `lib/arm64-v8a` and `lib/armeabi-v7a` from config APKs into base APK. Android accepts it as a standard standalone APK. | None. |
| **08** | Running `uber-apk-signer` with `-o` and `--overwrite` | ❌ Failed | Signing command aborted. | `uber-apk-signer` throws an error if both output directory (`-o`) and in-place `--overwrite` flags are passed simultaneously. Removed `--overwrite`. |
| **09** | Re-signing merged APKs with Java 22 & `uber-apk-signer.jar` | ✅ Succeeded | Successfully generated `v1`, `v2`, and `v3` signatures with 4-byte zip alignment. Installs cleanly in BlueStacks. | None. |
| **10** | Dojo hue transformation mod (`mod_shadow_fight.py`) | ✅ Succeeded | Shifted Dojo mountains and lanterns 180° into a cool Cyan/Sapphire theme and injected back into Unity serialization. | None. |
| **11** | Independent App Identity & Rebranding ("Cat Blasters 9k") (`build_cat_blasters.py`) | ✅ Succeeded | Decoded APK with `apktool 2.10.0`. Changed `app_name` to "Cat Blasters 9k". Changed package & all provider authorities from `com.nekki.shadowfight` to `com.nekki.catblasters` (exact 21-byte match in `global-metadata.dat`). Injected custom neon Cat Blasters icon across all mipmaps and adaptive drawables. Successfully rebuilt & signed. | If package or provider authorities aren't changed, Android rejects side-by-side installs with `INSTALL_FAILED_CONFLICTING_PROVIDER`. |
| **12** | Live BlueStacks In-Game Verification | ✅ Succeeded | **Verified Live**: Cat Blasters 9k launched cleanly in BlueStacks. The custom Cyan/Sapphire Dojo textures, sliding shoji screens, mountain backdrop, and custom launcher icon rendered as designed. | Installing both APKs on the identical BlueStacks instance triggered an install dialog error (due to Android system internal data/UID or native lib cache). Documented that separate BlueStacks instances should be used if original comparison is required. |
| **13** | Analysis of In-Game DLC Downloads (13.12 MB / 12.5 MB) | ✅ Succeeded | Traced `dlgServiceDownloadDemand` via `libil2cpp.so` string cache (`0x4138f18`) and `PreFight` controller (`BEPJMNAHCAD$$GIENGNEGHPJ` at `0x3189440`). Confirmed the two packs are `ANIMATIONS` (6.35 MB) and `VERSIONAL_CONFIGS` (6.75 MB), totaling 13.11 MB (12.5 MiB). Pulled all assets locally to `modding/assets/downloaded_gamedata/`. | Without pre-populating `/sdcard/Android/data/<package>/files/gamedata/bundles/`, a freshly installed APK has an empty persistent data folder, triggering the CDN download prompt. |
| **14** | All-in-One Self-Extracting APK (`AssetExtractor.smali`) | ✅ Succeeded | Injected `AssetExtractor.smali` into `classes.dex` and hooked `MultiDexApplication.onCreate()`. Embedded offline bundles (`ANIMATIONS`, `VERSIONAL_CONFIGS`, configs) directly inside APK `assets/gamedata/`. Built, aligned, and signed standalone APK (`173.09 MB`). | Standard APK assets are compressed inside the package; Unity IL2CPP file APIs require unpacked files on external storage. The Java startup hook extracts them in ~250ms on first launch before Unity initialises, completely eliminating the download prompt. |
| **15** | BlueStacks Keymapping Binding for Rebranded Package (`com.nekki.catblasters.cfg`) | ✅ Succeeded | Copied default Shadow Fight 2 keymapper configuration (`WASD` Dpad, `J` punch, `K` kick) to `C:\ProgramData\BlueStacks_nxt\Engine\UserData\InputMapper\com.nekki.catblasters.cfg` and backed up to `bluestacks/configs/`. | BlueStacks keys its built-in input mapping profiles strictly by Android package name. Changing package to `com.nekki.catblasters` caused BlueStacks to load a blank default input profile. Supplying the named `.cfg` restores full keyboard controls. |
| **16** | Permanent Tutorial Bypass (Punchbag, Kenji, Knives, Shin) & Save Hash Bypass | ✅ Succeeded | Embedded pre-configured `users.xml` with Punching Bag, Kenji, and Shin (`ZONE_1|BOSS_LYNX|1`) marked beaten, Knives equipped, and Tournament/Survival unlocked. Patched XML hash validator `CFJANHACGMG.AMELFFLEPNF` (`0x3598568` in `libil2cpp.so`) to `mov w0, #1; ret` to permanently bypass save integrity checks. Extended `AssetExtractor.smali` to auto-provision this profile into `userdata/` on first launch. | Fresh installs previously wiped storage and regenerated empty tutorial-state saves. The self-extractor provisions the post-tutorial save before the engine boots, allowing the game to jump straight to the Act 1 Tournament map with no repetitive tutorials. |
| **17** | Pre-bundling Act 1 Assets (`ZONE_1` 36.54 MB) into Offline Assets | ✅ Succeeded | Captured `ZONE_1` bundle (36,541,298 bytes) downloaded when unlocking Act 1 Tournament & Survival. Embedded directly into APK `assets/gamedata/bundles/ZONE_1` alongside `ANIMATIONS` and `VERSIONAL_CONFIGS`. Synchronized `packs.xml`, `packs.xml.hash`, and `config_cdn.xml`. Extended `AssetExtractor.smali` to unpack `ZONE_1` during app initialization. | Setting Act 1 Tournament & Survival active triggered an in-game demand check for the 36.54 MB Act 1 asset pack. Bundling `ZONE_1` directly within the package and pre-extracting on boot eliminates the in-game download dialog completely. |
| **18** | Complete Neutralization of "Data Corrupted" Anti-Cheat (`EOOEOHKLOFJ`) | ✅ Succeeded | Traced "Your game data may be corrupted" dialog (`HackTitle`) via Unity logcat to anti-cheat controller `EOOEOHKLOFJ`. Patched `EOOEOHKLOFJ$$EOJDBAHODGK` (`0x30c3344` in `libil2cpp.so`) to `mov w0, #1; ret` (reports validation pass). Patched `EOOEOHKLOFJ$$MACGEGDGBOI` (`0x30c1250`) to `ret; nop` (neutralizes `HackTitle` dialog creation). Patched `EOOEOHKLOFJ$$HBGCPAEJCJJ` (`0x30c11d8`) to `mov w0, #0; ret` (reports zero hacks detected). Synchronized `users.xml` and `users_backup.xml` with matching MD5 hashes. | Bypassing only `AMELFFLEPNF` hash check left the secondary runtime anti-cheat validator active, which detected tampered currency values and invoked `MACGEGDGBOI` to force-quit the game. Patching all three levels of `EOOEOHKLOFJ` permanently disables the corruption panic routine. |
| **19** | Elimination of Intro Cutscene & Startup Popups (Google Play Warning & GDPR Modal) | ✅ Succeeded | Replaced opening cutscene (`assets/database/intro.mp4`) with a 0.04s (1-frame, 2KB) dummy black video for instantaneous splash transition. Patched startup operation `AGGMBMDDJIO.NKLGCNHLBAF` (`0x34377F4`) and `AGGMBMDDJIO.JFGBPBOCOIC` (`0x3437AFC`) to neutralize "Warning! Your game progress will be lost without Google Play Games". Patched `LJBDMDHNKFM.JFGBPBOCOIC` (`0x32D9388`) to `mov w0, #0; ret` to permanently eliminate the GDPR Terms of Use modal. | Cutscenes previously stalled the boot sequence, and startup dialogs blocked progression until manually dismissed. Patching these functions at assembly level completely silences them on every boot. |
| **20** | Elimination of Sensei Dialogs & Unlocking Act 1 Map Focus (`Tutorial="END_TUTORIAL"`) | ✅ Succeeded | Traced Sensei dialogue triggers to `JAKHNKEHNBE` state machine. Set `Tutorial="END_TUTORIAL"` (step 21) in `users.xml` and removed `StoryTutorialBossFight` from `<Quests />`. Configured `FightIDS="ZONE_1|Tournament|1"` and reordered `<Battles>` with Tournament and Survival before Lynx (`BOSS_LYNX`). Extended `AssetExtractor.smali` with `.provisioned_v2` marker to enforce clean profile delivery on install. | Empty `Tutorial` attribute previously caused the engine to revert to `STEP_WELCOME` ("Well, well... my vain disciple has returned") or `STEP_BOSS` (Sensei forcing Lynx challenge). Setting `END_TUTORIAL` permanently bypasses all Sensei tutorials, leaving the Act 1 map open with Tournament focused and full player freedom. |
| **21** | Bundling User-Completed Progress Save & Self-Provisioning (`.provisioned_v3`) | ✅ Succeeded | Pulled live user profile directly from emulator storage (`users.xml`, `users_backup.xml`, settings bins, and cryptographic MD5 hashes). Profile contains Level 3 progress, Double Sweep perk unlocked, all tutorial sequences permanently completed (`Tutorial="END"`), and Tournament map focused. Bumped self-extractor startup hook in `AssetExtractor.smali` to `.provisioned_v3`. Embedded all save files directly into APK `assets/userdata/` and rebuilt standalone APK. | Ensures that whenever the APK is freshly installed or uninstalled/reinstalled, it immediately deploys this exact completed save state, launching straight into Act 1 with zero setup or tutorials needed. |
| **22** | Pre-Bundling All Story Chapter Content & Neutralizing Missing Pack Checks (`.all_packs_v1`) | ✅ Succeeded | Downloaded all 13 game story and versional packs (`ANIMATIONS`, `VERSIONAL_CONFIGS`, `VERSIONAL_ASSETS`, `ZONE_1` through `ZONE_7_3`, and `ZONE_IM` totaling ~156 MB). Embedded all bundles and synced `packs.xml`/`packs.xml.hash` into APK assets. Updated `AssetExtractor.smali` to extract all 13 packs with marker `.all_packs_v1`. Patched IL2CPP pack check routine `AAPGCAPGBLG.MCFHOHANNDH` (`0x325bd24`) to `mov w0, #0; ret` so the engine never requests additional downloads. Successfully rebuilt & signed standalone APK (`307.02 MB`). | Completely eliminates the "LOADING REQUIRED! SIZE: 31.58 MB" and any future chapter download prompts across the entire story campaign. |
| **23** | Capturing 31.58 MB Live Events & Weekly Offers Packs & Provisioning Save v4 (`.all_packs_v2`, `.provisioned_v4`) | ✅ Succeeded | Identified that the exact 31.58 MB missing pack download was comprised of 5 `EVENTS` bundles (`MA_FEST_26`, `SUMMER_FEST_25/26/CHEST`, `EVENTS_COMMON` = 23.58 MB) and 12 `OFFERS` bundles (`WEEKLY_OFFER_12` through `22`, `AGNISSEAL_OFFER` = 8.05 MB). Pulled all 17 event/offer bundles and live user save (level 52 equipment access) directly from BlueStacks. Updated `AssetExtractor.smali` to extract all 34 bundles + configs with marker `.all_packs_v2` and deploy the user save with `.provisioned_v4`. Synchronized MD5 hashes for `users.xml` (`8840C99A5A463498CDB7F43F186667CC`). Successfully rebuilt & signed standalone APK (`333.23 MB`). | With both the story campaign and the live event/offer packs pre-bundled directly into the APK, no missing content download dialog ever appears. |
| **24** | Default Startup Scene Redirect from Dojo to Map (`SF2_Modded_v2.apk`) | ✅ Succeeded | Reversed Unity IL2CPP scene dispatch lifecycle (`BuildSettings` and `LoaderScreen`). Implemented an ARM64 binary hook in `libil2cpp.so` (`0x2FF0A10` and `0x2FF1658`) that intercepts `LoaderScreen.NextScene` and conditionally replaces `ModuleDojo` (`3`) with `ModuleMap` (`5`). Updated save state with `FightIDS="ZONE_1|Tournament|1"` and recomputed MD5 hashes (`16294469499F3E8F6D5A434EF1837417`). Rebuilt, aligned, and signed `SF2_Modded_v2.apk` (`333.23 MB`), preserving `SF2_Modded_v1.apk` untouched. | Engine previously defaulted to `Scene 3` (Dojo punching bag). The assembly hook dynamically substitutes `Scene 5` (Map), causing the game to boot directly into the Act 1 Tournament map with the Stage 1/24 battle scroll and FIGHT! button open. |
| **25** | Direct Auto-Start Fight Hook (`InfoBattle.CIHKNMDAPBG` -> `OnFightButtonClick`) & Infinite Energy Bypass (`SF2_Modded_v3.apk`) | ✅ Succeeded | Patched energy validator `IEICNBBBNEJ.EHLKEFJNKPA` (`0x1CC5B44`) to `mov w0, #1; ret` to guarantee infinite fight energy. Patched `InfoBattle.CIHKNMDAPBG` exit (`0x3414C4C`) with branch to code cave `0x30C1258`. Trampoline restores callee-saved registers (`x19..x24, x29, x30`), cleans up stack (`add sp, sp, #80`), sets `x0 = x19` (`InfoBattle`), and tail-calls `InfoBattle.OnFightButtonClick` (`0x3413184`). The game transitions straight from splash -> loader -> map init -> triggers fight automatically, loading directly into Act 1 Tournament Stage 1 combat against Monkey. Built, aligned, and signed `SF2_Modded_v3.apk` (`333.23 MB`), preserving `SF2_OG.apk`, `SF2_Modded_v1.apk`, and `SF2_Modded_v2.apk` intact. | None. |
| **26** | Root-cause analysis & revert of all native ARM64 auto-fight trampolines | ❌ Reverted | Systematically reverted all native trampoline patches back to original bytes in `so_patches` (restore entries for `0x3414c4c`, `0x296bd44`, `0x3580ca4`, `0x30c1258`, `0x1cc5b44`). | `IEICNBBBNEJ.EHLKEFJNKPA` (`0x1cc5b44`) is raid-only energy check (battleType==7), irrelevant to tournament. `CIHKNMDAPBG` (`0x3414c4c`) only fires on tile scroll, never on boot. `Scene<object>.Update` branch had wrong `x0` register context. `MapScene.PIMIMOACBNG` trampoline called `OnFightButtonClick` before `InfoBattle.AABIECAIFGA` fight model was populated — game showed map, no fight started. All trampolines require fully-initialized `InfoBattle` before `OnFightButtonClick` is safe. |
| **27** | Smali `dispatchTouchEvent` from background thread | ❌ Failed | `AssetExtractor.performTap()` called `view.dispatchTouchEvent(MotionEvent)` from background thread with 6s delay after `currentActivity != null`. APK built and installed. | Android strictly requires UI operations on main thread. `dispatchTouchEvent` silently failed (swallowed by catch block) — no `CatBlasters: AutoFight: Dispatched tap` log appeared in logcat. Changed to `Runtime.getRuntime().exec(new String[]{"sh","-c","input tap 1640 870"})` which runs as a subprocess, bypassing thread restrictions. |
| **28** | Smali `Runtime.exec("input tap 1640 870")` with 12s delay | ⚠️ Partial | Updated `performTap()` to use `Runtime.exec` + `Process.waitFor()`. Increased initial sleep to 12s (`0x2EE0`). APK rebuilt (333.23 MB), signed, installed. `Thread-38` visible in logcat at ~25s post-launch, confirming thread runs. | On first launch, self-extractor decompresses ~190 MB inside `Application.onCreate()`, blocking Unity bootstrap. Game stays on splash for 60s+. The 12s tap fires while still on splash (ignored). Root fix: use much longer delay (30s+) or retry loop. On second launch (extraction skipped via `.all_packs_v2` marker), game reaches map in ~10s so 12s would work — but unverified due to session end. |
| **29** | `MapScene.FFFFAHJOOJP` NullReferenceException analysis | ✅ Diagnostic | Observed via logcat: `MapScene.GIENGNEGHPJ → FFFFAHJOOJP → OnClickBattle → ACHLOMELAJE.AAKJALHCIBB` throws `NullReferenceException` at `15:57:32.576` during normal map scene loading. The `OOMHDDBCBJP` (battle object) is null when `FFFFAHJOOJP` is called inside the loading coroutine. | Unity catches the exception silently. Map loads correctly afterward. This is the game's own code auto-trying to reselect the focused tournament battle before zone data is fully deserialized. Not a crash, not our code. However, this means any native patch that calls `FFFFAHJOOJP` during `OnLoaded` will also fail with the same null. Must ensure battle model is fully populated before auto-triggering fight. |
| **30** | Instant Sub-Second BlueStacks Screenshot Skill (`bluestacks-instant-screenshot`) | ✅ Succeeded | Developed custom direct TCP socket screencap protocol talking directly to ADB daemon port `5037` (`host:transport:<serial>` -> `exec:screencap -p`). Streams PNG bytes directly into RAM/disk in **~430ms** with zero device-side disk writes, zero subprocess overhead, zero ADB daemon banner noise, and zero PowerShell UTF-16 redirection corruption. Bundled as a reusable workspace skill with CLI and Python RL observation API. | Standard `adb shell screencap -p > file.png` in PowerShell corrupted files into UTF-16LE text. `adb pull` took 6-10s with noisy transfer logs. Direct socket stream with header slicing (`\x89PNG\r\n\x1a\n`) delivers 100% clean, pixel-perfect 1920x1080 frames in under 450ms. |
| **31** | VIP Infinite Energy Build on v2 Baseline (`SF2_Modded_v3.apk`) | ✅ Succeeded | Forked pristine `SF2_Modded_v2.apk` and patched `libil2cpp.so` (arm64-v8a) across 5 core energy routines: `ACHLOMELAJE.PDKBJDBJOOK` (`0x3063e1c` -> `mov w0, #1; ret`), `MenuEnergyPanel` VIP icon (`0x344aec8` -> `mov w20, #1`), `ACHLOMELAJE.MEBIEMOMELE` field 0x238 (`0x305aaa4` -> `mov w8, #1`), `ACHLOMELAJE.AIIJFJLLIDB` spend bypass (`0x3057bfc` -> `mov w0, #1; ret`), and `ACHLOMELAJE.FMNEFEMHCGG` count getter (`0x3057964` -> `mov w0, #5; ret`). Repackaged and signed with `uber-apk-signer.jar` to produce `SF2_Modded_v3.apk` (`333.20 MB`). Verified live on BlueStacks: golden-winged VIP Unlimited Energy indicator renders on the top bar, energy never depletes, Act 1 Tournament map boots directly, and combat starts immediately upon tapping FIGHT! | None. |
| **32** | Automated Lifecycle Scripts (`install.py`, `boot.py`, `common.py`) & Unified `Makefile` | ✅ Succeeded | Created modular automation scripts in `scripts/`: `install.py` verifies package presence on BlueStacks and installs `SF2_Modded_v3.apk` only if missing; `boot.py` verifies installation and boots the game (or prompts to run install if missing). Authored a project root `Makefile` supporting `make install`, `make boot`, `make all`, `make reinstall`, `make restart`, `make screenshot`, and `make status`. Created `make.bat` for seamless execution in Windows environments without GNU make installed. Verified both targets live on BlueStacks with instant screenshots. | None. |
| **33** | Interactive Multi-Command Input & Presets in `tap.py` (`input()`) | ✅ Succeeded | Updated `scripts/tap.py` to support interactive multi-command input via Python's built-in `input()` function, accepting sequential commands with repeat counts (e.g. `up`, `down`, `right 5`, `down-left 2`), inline coordinates, combat presets (`punch`, `kick`, `shadow`, `ranged`), modal buttons (`center_ok`), and chaining via semicolons or multiline stdin piping. Tested live in combat against Monkey and verified via sub-second screenshot. | None. |
| **34** | Arbitrary Round Control Parameterization & Live Combat Verification (`SF2_Modded_v4.apk`) | ✅ Succeeded | Reversed combat lifecycle controllers in `libil2cpp.so`: `FCJBEKHDLAF.DHKCOFBMIEL` (round end transition at `0x33e7d80`), `AIFOMGABBBA` (statistic victory threshold at `0x33e9444`), `LPIEJMLPFBF` (round model target at `0x33ea8e4`), and `BBCAMJDDOII` (character death event handler at `0x33ef960`). Parameterized `ROUNDS_TO_WIN` in `modding/pipeline/build_cat_blasters.py` with CLI argument `--rounds <N>` using dynamic ARM64 `movz` encoding. Built, signed, and deployed `SF2_Modded_v4.apk` (333.23 MB) configured with 5 rounds. Reverted inadvertent MapScene register mismatch at `0x3580ca4` back to baseline `f50300aa` (`mov x21, x21`). Verified live on BlueStacks in combat against Lynx bodyguard Brick on Rooftops. User confirmed live combat runs across 5 rounds at minimum and concludes when either fighter reaches 5 victories. | None. |
| **35** | Dojo Sparring Restoration & Reverting Startup Scene Hook (`SF2_Modded_v5.apk`) | ✅ Succeeded | Reverted ARM64 binary scene redirection hook at `0x2ff0a10` and `0x2ff1658` in `libil2cpp.so` back to original native instructions (`ldr w9, [x9, #0xc]`). Built, aligned, and signed `SF2_Modded_v5.apk` (333.23 MB), preserving `SF2_Modded_v1.apk` through `v4.apk` intact. Reinstalled on BlueStacks and verified live: game boots straight into the **Dojo** with the punching bag, knives equipped, and zero timer/opponent interference for testing combat actions. | None. |
| **36** | Default Map Boot with Dojo Menu Navigation Restoration via ARM64 BSS Latch (`SF2_Modded_v6.apk`) | ✅ Succeeded | Implemented a one-time scene hook at `0x2ff0a10` / `0x2ff1658` in `libil2cpp.so` utilizing BSS page `0x4684800`. On initial boot, the latch flag is 0; the hook redirects `NextScene == 3` (Dojo) to `5` (Map) and writes 1 into the latch. On subsequent scene loads (e.g. clicking Dojo in the menu scroll), the latch is 1, so the hook preserves `NextScene == 3`, allowing the Dojo to load cleanly. Added exact menu navigation presets (`menu-dojo`, `menu-map`) in `tap.py` and `action_client.py`. Verified live on BlueStacks: game cold-boots to Act 1 Map, clicking the Dojo menu icon transitions directly into the Dojo punching bag arena, and clicking the Map icon returns to Act 1 Map without scene overriding. | None. |
| **37** | Direct Binary Evdev Event Streaming (`/dev/input/event4`) for Sub-Millisecond Multi-Touch Combos (`action_client.py`) | ✅ Succeeded | Replaced shell-forked `/system/bin/sendevent` loops with a persistent unbuffered binary stream (`cat > /dev/input/event4`) packing 24-byte `struct input_event` (`<qqHHi`). Reduced event dispatch latency from 427ms down to 0.7ms. Combined joystick direction and initial strike into a single atomic hardware `SYN_REPORT` to eliminate preliminary walking steps. Maintained joystick hold across rapid double-taps (`D, J+J`) with customizable millisecond gaps (`gap <N>ms`). Verified live in Dojo: directional double-attacks (`right double-punch`, `d, j+j`, `left double-kick`) cleanly trigger the weapon's true Super Slash / Double Sweep combos without delay or step artifacts. | Standard shell `sendevent` spawned 9-15 child processes per combo, introducing ~400ms of OS fork latency that broke combo buffering windows and caused accidental walking. Streaming binary structs directly into the kernel pipe eliminated the OS bottleneck entirely. |
| **38** | Embedded Frida Gadget & In-Engine Telemetry Streamer (`SF2_Modded_v7.apk`, `test_engine_api.py`) | ✅ Succeeded | Embedded ARM64 Frida Gadget (`libfrida-gadget.so` v17.19.0) in `lib/arm64-v8a/` and injected `System.loadLibrary("frida-gadget")` into `AssetExtractor.smali`. Rebuilt and signed `SF2_Modded_v7.apk` (342.91 MB). Created `scripts/test_engine_api.py` connecting to port `27042`. Hooked master physics tick `FightScene.FixedUpdate` (`0x3237268`), decrypted CodeStage `ObscuredFloat` health values at `+0x15c` via XOR bitwise arithmetic, tracked ground coordinates (`X`, `Y`), facing direction, distance, and hooked hit badges (`ShowCritical`, `ShowFirstStrike`, `ShowShock`, `set_IsNoBlock`). Streamed live at 20 Hz with sub-millisecond precision during tournament fight against Monkey. | BlueStacks Android runtime uses arm64 translation, causing `Process.findModuleByName("libil2cpp.so")` to fail. Solved by enumerating memory ranges (`Process.enumerateRanges('r-x')`) to calculate the exact base offset dynamically. |
| **39** | Native In-Engine Action Dispatch & Simulation Speedup Control (`engine_controller.py`) | ✅ Succeeded | Reversed combat input receiver in IL2CPP: `battleCtrl.DDFNLHMCIND` (`0x33E4C4C`) and `OLKKAIFGGAK.IJDCCIGHPHJ` (`0x34F57E0`). Exposed native function calls inside `FightScene.FixedUpdate` to dispatch actions (`Punch` 9, `Kick` 10, `Jump` 1, `Forward` 3, `Roll Forward` 4, `Duck` 5, `Back` 7, etc.) directly into the character's combo state machine without touching the GUI joystick or attack buttons. Hooked `UnityEngine.Time.set_timeScale` (`0x3BFB9C0`) to dynamically control game simulation speed (1x to 10x) live via Frida RPC. Authored interactive CLI [`scripts/engine_controller.py`](file:///c:/Users/Ishan/Personal/Porfolio/Shadow%20Fight%202/scripts/engine_controller.py) for direct user testing in the Dojo. | Emulating touch events at accelerated simulation speeds fails due to fixed OS touch sampling rates. Dispatching actions via native in-engine method invocation executes synchronously inside the physics tick, enabling 100% deterministic control at arbitrary game speeds. |
| **40** | Permanent Unconditional Frida Gadget Lifecycle Fix & Build v8 (`SF2_Modded_v8.apk`) | ✅ Succeeded | Traced root cause of port `27042` connection failure: on warm boots where `userdata/.provisioned_v4` was present, `AssetExtractor.smali` returned early (`return-void`), bypassing `System.loadLibrary("frida-gadget")`. Replaced early return with `goto :goto_0` to ensure Frida Gadget loads unconditionally on every app boot. Protected `SF2_Modded_v7.apk` and built `SF2_Modded_v8.apk` (342.90 MB). Verified live: Frida Gadget listens reliably on port `27042` across cold and warm starts. | Early return in smali bytecode bypassed native library initialization on second and subsequent launches. |
| **41** | Universal In-Engine Action Vocabulary Calibration (`engine_controller.py`) | ✅ Succeeded | Traced native combat input pipeline: `OLKKAIFGGAK.IKPHKLHDNMA` (`0x34E90D0`) acts as universal ActionDown (quadrants 1-8 and attack buttons 9-14), and `OLKKAIFGGAK.IJDCCIGHPHJ` (`0x34F57E0`) acts as universal ActionUp. Calibrated exact user vocabulary: basic movements (`w`, `a`, `s`, `d`), compound movements (`wa` jump back, `wd` jump fwd, `sa` roll back, `sd` roll fwd), fast double-tap movements (`dd` dash, `aa` backflip), compound directional attacks (`wp`, `ap`, `sp`, `dp`, `wk`, `ak`, `sk`, `dk`), and double attacks (`dpp`, `app`, `spp`, `wpp`, `dkk`, `akk`, `skk`, `wkk`) with auto-facing orientation resolution. | Direct quadrant queue write without matching `IKPHKLHDNMA` / `IJDCCIGHPHJ` pairs failed to register combined multi-touch attack states in `NKOIBKNPICN`. Invoking native `actDown` and `actUp` directly inside the physics loop ensures 100% reliable combo resolution. |
| **42** | Directional Attack Hold Duration (12 Ticks) & Spatial Ground Coordinate Facing Calibration (`engine_controller.py`) | ✅ Succeeded | Identified that clearing directional quadrant on the exact same frame (0ms) caused the engine's animation selector to cancel compound strikes. Added a 12-frame (~200ms) directional hold state (`holdQuadTicks = 12`) and replaced internal flags with real-time ground coordinate comparison (`p1_x > p2_x`). Verified live in engine: `wp`, `sp`, `ap`, `dp`, `wk`, `sk`, `ak`, `dk`, and double attacks (`dpp`, `app`, `skk`, `wkk`) reliably trigger their authentic knife slashes and kicks without dropping inputs. | Setting quadrant to -1 on the same frame as the attack button press caused the engine combo solver (`NKOIBKNPICN.FAGKGMMBPNG`) to cancel directional modifiers. Holding the quadrant for 12 physics ticks keeps the directional state locked until the animation initializes. Also noted that when pressed right against the punching bag, attacks convert to close-range unarmed elbow strikes (`ShortUpwardElbowStrike`). |
| **44** | True Dynamic HP Decryption, Native ALBJPLAPOBO Hook & Round Lifecycle Events (`stream_telemetry.py`) | ✅ Succeeded | Resolved true live health values: Max HP at `PJKHAJKEHEL + 0xF4` (`MGLLAKLAAOO`) and Current HP at `+ 0x208` (`JNFNFEJAGGN`), calling native decryptor `ALBJPLAPOBO` at RVA `0x1BC1F2C` to fix the static `0.5176` health bug. Hooked `ViewerFight.Play` (`0x35BE050`) for `ROUND_START` and `FCJBEKHDLAF.DBNFJODELLP` (`0x33ECBA4`) for `ROUND_END` with winner and end reason (knockout, timeout, ring out). Added `--pretty`, `--log <file.jsonl>`, and `--interval <seconds>` (default 1.0s) flags to `stream_telemetry.py`. | Previous health reading tapped a static parameter block; resolving dynamic health through `PJKHAJKEHEL` and calling the native decryption function restores real-time health deltas. |
| **45** | Master Engine Action Catalog & Action State Machine Reverse Engineering | ✅ Succeeded | Reverse engineered character action dispatcher `OLKKAIFGGAK.OJHIDJPICJN` (TypeDefIndex 3184) and master move database `LDHBHPILNMA` (TypeDefIndex 1526). Traced the engine's 16 internal event categories (`EVENT_KEY_PRESSED`, `EVENT_ANIM_START`, `EVENT_HIT`, `EVENT_ANIM_INTERRUPTED`, `EVENT_ROUND_STAGE`). Dumped and cataloged all 147 unique engine action clips across both fighters from live memory into `modding/assets/downloaded_gamedata/all_moves_categorized.json`. Categorized into Strikes, Defensive Blocks, Hit Reactions, Knockdowns/Recoveries, Acrobatics, and Stances. Documented in `08_ENGINE_CONTROLLER_AND_RL_HARNESS.md`. | Actions reported in telemetry like `SweepHit`, `SweepBlock`, `StandupAfterThrowFall` are not controller inputs; they are reactive state machine animations automatically triggered by collision, guard, or knockdown events. |











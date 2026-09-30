# BlueStacks Emulator Runtime & Input Setup Guide

This directory contains standalone, ready-to-run APK builds of *Shadow Fight 2*, input mapping profiles for keyboard/mouse control, and ADB automation helpers.

---

## 1. Available Standalone APKs

Located in [`bluestacks/apks/`](apks/):

| APK File | Size | App Name | Package Identity | Contents & Features |
| :--- | :--- | :--- | :--- | :--- |
| **`SF2_OG.apk`** | 162.75 MB | **Shadow Fight 2** | `com.nekki.shadowfight` | Untampered base game with classic shadow icon and standard starting tutorial. |
| **`SF2_Modded_v1.apk`** | 333.23 MB | **Cat Blasters 9k** | `com.nekki.catblasters` | Protected v1 milestone build. Custom Cyberpunk Cyan Dojo theme, neon cat icon, all 30 offline game bundles, tutorials skipped, cutscene and popups silenced. |
| **`SF2_Modded_v2.apk`** | 333.23 MB | **Cat Blasters 9k** | `com.nekki.catblasters` | Protected v2 milestone build. Direct Act 1 Map boot hook replacing Dojo default. |
| **`SF2_Modded_v3.apk`** | **333.20 MB** | **Cat Blasters 9k** | `com.nekki.catblasters` | **VIP Infinite Energy Build**: Boots straight to Act 1 Tournament Map (Scene 5) with permanent VIP Unlimited Energy indicator and zero fight energy consumption. |

> [!NOTE]
> Because all modded APKs have **unique package identities and Content Provider authorities**, they can be installed side-by-side on the **same BlueStacks instance** without conflicting with the original game.

---

## 2. Installation Options

### Option A: Drag and Drop (Recommended)
1. Open **BlueStacks 5**.
2. Drag `bluestacks/apks/SF2_Modded_v3.apk` directly into the BlueStacks window.
3. BlueStacks will show "Installing app" on the home screen.
4. Launch the game from the "Cat Blasters 9k" icon.

### Option B: PowerShell ADB Helper Script
```powershell
# Install the latest modded build (v3: auto-starts fight on load)
.\bluestacks\scripts\install_apk.ps1 -Target v3

# Install the v2 build (boots straight to Map)
.\bluestacks\scripts\install_apk.ps1 -Target v2

# Install the milestone v1 build
.\bluestacks\scripts\install_apk.ps1 -Target v1

# Install the untampered original baseline build
.\bluestacks\scripts\install_apk.ps1 -Target original
```

---

## 3. Keyboard & Keymapper Controls

### The Rebranded Package Keymap Fix
BlueStacks keys its built-in keyboard mapping profiles strictly by package name (`com.nekki.shadowfight`). Because the modded build uses `com.nekki.catblasters`, BlueStacks initially loads a blank profile with no controls.

Full controls have been restored by copying the game's official mapping scheme to:
`C:\ProgramData\BlueStacks_nxt\Engine\UserData\InputMapper\com.nekki.catblasters.cfg`

### Default Control Bindings:
* **Movement (D-Pad)**: `W` (Up / Jump), `A` (Left / Retreat), `S` (Down / Duck), `D` (Right / Advance)
* **Punch**: `J`
* **Kick**: `K`
* **Ranged Weapon / Shuriken**: `L`
* **Magic Spell**: `I`

---

## 4. Headless ADB Control & Automation

BlueStacks bundles its own Android Debug Bridge binary:
`C:\Program Files\BlueStacks_nxt\HD-Adb.exe`

### Enabling ADB
If ADB fails to connect, enable it in BlueStacks:
**Settings** -> **Advanced** -> **Android Debug Bridge** -> Toggle **ON**.

### Useful Automation Commands:
```powershell
# List active BlueStacks emulator instances
& "C:\Program Files\BlueStacks_nxt\HD-Adb.exe" devices

# Pull player save files from emulator
& "C:\Program Files\BlueStacks_nxt\HD-Adb.exe" pull /sdcard/Android/data/com.nekki.catblasters/files/userdata/ ./modding/assets/userdata/

# Inspect downloaded game bundles on emulator storage
& "C:\Program Files\BlueStacks_nxt\HD-Adb.exe" shell ls -la /sdcard/Android/data/com.nekki.catblasters/files/gamedata/bundles/

# Capture an instant screenshot of gameplay
& "C:\Program Files\BlueStacks_nxt\HD-Adb.exe" exec-out screencap -p > screenshot.png
```

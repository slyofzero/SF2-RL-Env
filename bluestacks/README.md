# BlueStacks Emulator Runtime & Input Setup Guide

This directory contains standalone, ready-to-run APK builds of *Shadow Fight 2*, input mapping profiles for keyboard/mouse control, and ADB automation helpers.

---

## 1. Available Standalone APKs

Located in [`bluestacks/apks/`](apks/):

| APK File | Size | App Name | Package Identity | Contents & Features |
| :--- | :--- | :--- | :--- | :--- |
| **`SF2_OG.apk`** | 162.75 MB | **Shadow Fight 2** | `com.nekki.shadowfight` | Untampered base game with classic shadow icon and standard starting tutorial. |
| **`SF2_Modded_v1.apk`** | **333.23 MB** | **Cat Blasters 9k** | `com.nekki.catblasters` | Custom Cyberpunk Cyan Dojo theme, neon cat launcher icon, **all 30 offline game bundles** (Acts 1-7, live events, offers), pre-loaded Level 52 equipment access save, all tutorials skipped, zero cutscene delay, and startup popups silenced. *(Protected v1 milestone build; future mods generate `SF2_Modded_v2.apk`).* |

> [!NOTE]
> Because both APKs have **unique package identities and Content Provider authorities**, they can be installed side-by-side on the **same BlueStacks instance** without conflicting.

---

## 2. Installation Options

### Option A: Drag and Drop (Recommended)
1. Open **BlueStacks 5**.
2. Drag `bluestacks/apks/SF2_Modded_v1.apk` directly into the BlueStacks window.
3. BlueStacks will show "Installing app" on the home screen.
4. Launch the game from the "Cat Blasters 9k" icon.

### Option B: PowerShell ADB Helper Script
```powershell
# Install the modded cyberpunk standalone build
.\bluestacks\scripts\install_apk.ps1 -Target modded

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

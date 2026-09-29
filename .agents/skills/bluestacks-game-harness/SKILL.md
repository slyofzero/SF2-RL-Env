---
name: bluestacks-game-harness
description: Configure BlueStacks 5 emulator runtimes for game automation, ADB headless control, and keymapper input profiles. Use whenever troubleshooting BlueStacks ADB connectivity, recovering broken keyboard/joystick controls after rebranding Android packages, or dispatching automated keystrokes into BlueStacks.
---

# BlueStacks Emulator Harness & Input Configuration

This skill covers configuring the BlueStacks 5 Android emulator runtime, setting up reliable ADB bridge connections, and binding custom keymapper input profiles (`.cfg`) when running modded or rebranded Android packages.

## When to Use
- Connecting to BlueStacks via ADB (`HD-Adb.exe`) for automated shell inspection, file pulling/pushing, or APK installation.
- Resolving ADB connection failures (`cannot connect to 127.0.0.1:5555` or connection closed).
- Restoring keyboard/mouse control (WASD, punch, kick, direction keys) when an Android package name is modified.
- Automating game setup for reinforcement learning harnesses and bots.

## 1. ADB Configuration in BlueStacks 5
BlueStacks ships with its own ADB binary (`HD-Adb.exe` located at `C:\Program Files\BlueStacks_nxt\HD-Adb.exe`).

### Enabling ADB
By default, BlueStacks disables ADB access. If ADB refuses connections:
1. In BlueStacks GUI: **Settings** -> **Advanced** -> **Android Debug Bridge** -> Toggle **ON**.
2. Or in configuration file: `C:\ProgramData\BlueStacks_nxt\bluestacks.conf`:
   ```ini
   bst.enable_adb_access="1"
   ```
3. Restart BlueStacks.

### Verifying Connection
From terminal (using PowerShell):
```powershell
& "C:\Program Files\BlueStacks_nxt\HD-Adb.exe" devices
```
Expected output:
```text
List of devices attached
emulator-5554    device
```

## 2. Restoring Keymapper Controls for Rebranded Packages
BlueStacks maps keyboard and gamepad inputs to on-screen touches using `.cfg` profile files.

### The Missing Controls Problem
BlueStacks keys its input profiles **strictly by Android package name**.
If you change an APK's package name from `com.nekki.shadowfight` to `com.nekki.catblasters`, BlueStacks fails to recognize the app and provides a blank input profile. As a result, keyboard controls (WASD, J, K) stop working completely!

### The Solution: Deploying InputMapper Profile
BlueStacks stores input mapper configurations in:
`C:\ProgramData\BlueStacks_nxt\Engine\UserData\InputMapper\`

To restore full controls:
1. Locate the original configuration file:
   `C:\ProgramData\BlueStacks_nxt\Engine\UserData\InputMapper\com.nekki.shadowfight.cfg`
2. Duplicate and rename it to match your rebranded package name:
   `C:\ProgramData\BlueStacks_nxt\Engine\UserData\InputMapper\com.nekki.catblasters.cfg`
3. If necessary, edit the JSON/cfg properties inside to match the new package name and activity.
4. Keep a version-controlled backup of this `.cfg` in your repository (`bluestacks/configs/<package>.cfg`).

## 3. High-Frequency File Operations via ADB
When extracting save profiles or deploying bundles:

```powershell
# Pull user profile from emulator to local repository
& "C:\Program Files\BlueStacks_nxt\HD-Adb.exe" pull /sdcard/Android/data/<package>/files/userdata/ ./assets/userdata/

# Inspect directory contents
& "C:\Program Files\BlueStacks_nxt\HD-Adb.exe" shell ls -la /sdcard/Android/data/<package>/files/gamedata/bundles/

# Clean install APK silently
& "C:\Program Files\BlueStacks_nxt\HD-Adb.exe" install -r -d "path/to/standalone.apk"
```

## Critical Pitfalls
- **Port Clashes**: BlueStacks uses dynamic internal ports for ADB (e.g. `127.0.0.1:5555`, `127.0.0.1:5554`, `127.0.0.1:5565`). Running `& "C:\Program Files\BlueStacks_nxt\HD-Adb.exe" devices` automatically discovers the active instance without manual port guessing.
- **PowerShell Execution**: In PowerShell, executing quoted binary paths requires the call operator `&` (e.g. `& "C:\Path\HD-Adb.exe" args`), otherwise PowerShell treats the string as a literal.

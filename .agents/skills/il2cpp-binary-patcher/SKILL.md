---
name: il2cpp-binary-patcher
description: Reverse engineer Unity IL2CPP native binaries (libil2cpp.so + global-metadata.dat), map class methods via Il2CppDumper, and apply binary ARM64 assembly patches to bypass anti-cheat, save validators, missing pack checks, and unwanted UI popups. Use whenever reversing Unity IL2CPP games, modifying native game logic, or neutralizing client-side restrictions.
---

# IL2CPP Reverse Engineering & Binary Assembly Patching

This skill details how to inspect, locate, and patch compiled C# game logic compiled via IL2CPP in `libil2cpp.so` using metadata dumpers and direct ARM64 hex opcodes.

## When to Use
- Reversing Unity games using IL2CPP where C# code has been compiled Ahead-of-Time into native machine code.
- Neutralizing anti-cheat checks (e.g. "Data Corrupted", integrity hash mismatch, speed hacks).
- Suppressing intrusive startup dialogs (GDPR terms, Google Play Games mandatory login, warning modals).
- Bypassing network check routines (e.g. CDN pack demand checks, version locks).
- Implementing soft resets, endless timers, or God mode for RL training environments.

## Prerequisites
- `Il2CppDumper.exe` (or CLI Python IL2CPP dumper).
- Target `libil2cpp.so` (usually from `lib/arm64-v8a/` for 64-bit Android).
- Target `global-metadata.dat` (from `assets/bin/Data/Managed/Metadata/`).

## Architecture: How IL2CPP Works
1. Unity compiles C# assemblies to IL, and then converts the IL into C++ source code via `il2cpp.exe`.
2. The C++ code is compiled into native machine code (`libil2cpp.so`).
3. Class names, method signatures, field names, and string literals are stripped from the `.so` and packed into an encrypted/indexed table: `global-metadata.dat`.
4. `Il2CppDumper` correlates the string indices in `global-metadata.dat` with the function pointers in `libil2cpp.so`, generating `dump.cs` and `script.json` with exact File Offsets and RVAs.

## Workflow

### 1. Generating Class and Method Dumps
Run `Il2CppDumper`:
```bash
Il2CppDumper.exe <path_to_libil2cpp.so> <path_to_global-metadata.dat> <output_dir>
```
Output files:
- `dump.cs`: Decompiled C# dummy header file containing all classes, fields, methods, RVAs, and file offsets.
- `stringliteral.json`: List of all hardcoded string literals and their memory addresses.
- `script.json`: Symbol mapping for Ghidra / IDA Pro.

### 2. Locating Target Methods
Search `dump.cs` for relevant keywords:
- Anti-cheat: `Hack`, `Cheat`, `Corrupt`, `Validate`, `Integrity`, `Hash`
- Controllers: `FightManager`, `BattleController`, `RoundTimer`, `InputReceiver`
- UI Modals: `ShowDialog`, `CheckDemand`, `GDPR`, `GooglePlay`

Example match in `dump.cs`:
```csharp
// Namespace: Nekki
public class SaveValidator
{
    // RVA: 0x3598568 Offset: 0x3598568 VA: 0x3598568
    public bool ValidateSaveHash(string xmlContent) { }
}
```

### 3. Common ARM64 Assembly Patches
In ARM64 (AArch64), instructions are 4 bytes (32 bits), encoded in little-endian format:

| Desired Behavior | Assembly Instruction | Hex Bytes (Little-Endian) | Note |
| :--- | :--- | :--- | :--- |
| **Return True (`1`)** | `mov w0, #1`<br>`ret` | `20 00 80 52`<br>`c0 03 5f d6` | Bypass validation/check |
| **Return False (`0`)** | `mov w0, #0`<br>`ret` | `00 00 80 52`<br>`c0 03 5f d6` | Bypass hack detection / pack demand |
| **No-Op Function (Void return)** | `ret`<br>`nop` | `c0 03 5f d6`<br>`1f 20 03 d5` | Neutralize error dialogs / force quit calls |
| **Unconditional Branch** | `b <target_offset>` | Calculated offset | Jump over validation branch |

### 4. Applying Patches via Python
Automate patching in your build pipeline:

```python
def apply_so_patches(so_path: str, patches: dict[int, tuple[str, bytes]]):
    """
    patches format:
    {
        0x3598568: ("Bypass Save Hash", bytes.fromhex("20008052c0035fd6")),
        0x30c11d8: ("Disable Hack Detector", bytes.fromhex("00008052c0035fd6")),
        0x30c1250: ("Neutralize Crash Dialog", bytes.fromhex("c0035fd61f2003d5")),
        0x325bd24: ("Disable CheckPacksNeeded", bytes.fromhex("00008052c0035fd6")),
    }
    """
    with open(so_path, "r+b") as f:
        for offset, (desc, patch_bytes) in patches.items():
            f.seek(offset)
            f.write(patch_bytes)
            print(f"Patched: {desc} at {hex(offset)}")
```

## Critical Pitfalls
- **Verify Architecture**: Ensure you are editing the matching architecture (e.g. `arm64-v8a` uses ARM64 opcodes; `armeabi-v7a` uses 32-bit ARM/Thumb opcodes).
- **RVA vs. File Offset**: In ELF binaries (`libil2cpp.so`), `Il2CppDumper` reports both `RVA` (Relative Virtual Address) and `Offset` (File Offset on disk). Always seek to the **File Offset** when modifying the `.so` on disk.
- **Multi-Level Verification**: Games rarely rely on a single check. Always trace callers: if a check function returns false, ensure the controller calling it doesn't have a secondary panic or force-close timer.

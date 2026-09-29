# Document 03: IL2CPP & ARM64 Binary Patching

This document provides a comprehensive breakdown of the native binary reverse engineering, method mapping, and assembly patching performed on `libil2cpp.so` to neutralize anti-cheat routines, save validators, missing pack checks, and unwanted UI popups.

---

## 1. How IL2CPP Works & How It Was Reverse Engineered

In Unity IL2CPP:
1. All C# code is translated to C++ and compiled Ahead-of-Time into ARM64 native assembly in `lib/arm64-v8a/libil2cpp.so`.
2. All class names, method signatures, field names, and string literals are stripped from the `.so` and stored in an encrypted/indexed table: `assets/bin/Data/Managed/Metadata/global-metadata.dat`.
3. We used **`Il2CppDumper`** ([`modding/tools/Il2CppDumper/`](file:///c:/Users/Ishan/Personal/Porfolio/Shadow%20Fight%202/modding/tools/Il2CppDumper/)) to correlate the string indices with the `.so` code addresses, generating:
   * **`dump.cs`** (28.6 MB, located in `modding/build_cache/il2cpp_dump/dump.cs`): Contains all decompiled C# classes, method signatures, RVAs, and file offsets.
   * **`stringliteral.json`**: Contains all hardcoded strings (e.g. `"dlgServiceDownloadDemand"`, `"HackTitle"`, `"users.xml"`) and the memory offsets referencing them.

---

## 2. ARM64 Assembly Mechanics (Cheat Sheet)

ARM64 instructions are fixed 4-byte words, encoded in **little-endian** byte order:

| Desired Logic | C# Equivalent | ARM64 Assembly | Hex String (Little-Endian) |
| :--- | :--- | :--- | :--- |
| **Return `true`** | `return true;` | `mov w0, #1`<br>`ret` | `20008052 c0035fd6` |
| **Return `false`** | `return false;` | `mov w0, #0`<br>`ret` | `00008052 c0035fd6` |
| **No-Op Function** | `return;` | `ret`<br>`nop` | `c0035fd6 1f2003d5` |
| **Direct Branch** | `goto offset;` | `b <relative_offset>` | e.g. `fea90114` |

---

## 3. Active Binary Patch Catalog

All active patches are defined in `so_patches` in [`modding/pipeline/build_cat_blasters.py`](file:///c:/Users/Ishan/Personal/Porfolio/Shadow%20Fight%202/modding/pipeline/build_cat_blasters.py#L188-L201):

### A. Save File & XML Hash Validation Bypasses
The game verifies that `users.xml` has not been tampered with by hashing its contents with a proprietary salt and comparing it against `users.xml.hash`. If the hash mismatches or cannot be validated, the game wipes the save or rejects it.

| File Offset | Obfuscated Class & Method | Original Function | Our Patch | What It Accomplishes |
| :--- | :--- | :--- | :--- | :--- |
| `0x3598568` | `CFJANHACGMG.AMELFFLEPNF` | `ValidateXmlHash(string)` | `mov w0, #1; ret` | Forces the primary XML validator to always report "valid" (`true`). |
| `0x3594984` | `CFJANHACGMG.AMELFFLEPNF` (Direct) | Secondary hash validator | `mov w0, #1; ret` | Bypasses direct internal hash check routine. |
| `0x35951B4` | `CFJANHACGMG.FNIHLBLMOBP` | Internal hash comparer | `mov w0, #1; ret` | Bypasses secondary signature verification. |
| `0x3595870` | `CFJANHACGMG.PBACHEOJBGG` | Backup hash checker | `mov w0, #1; ret` | Bypasses `users_backup.xml` verification. |
| `0x3595E1C` | `CFJANHACGMG.PKACMGFBIKK` | Deep file validator | `mov w0, #1; ret` | Bypasses checksum integrity check on XML nodes. |

### B. Anti-Cheat & "Data Corrupted" Panic Routines
Even if hash checks pass, an active background controller (`EOOEOHKLOFJ`) monitors runtime variables (currency deltas, equipment tiers, unearned perks). When triggered, it spawns the `"Your game data may be corrupted"` dialog (`HackTitle`) and forces the game to close.

| File Offset | Obfuscated Class & Method | Original Function | Our Patch | What It Accomplishes |
| :--- | :--- | :--- | :--- | :--- |
| `0x30C3344` | `EOOEOHKLOFJ.EOJDBAHODGK` | `CheckIntegrityPass()` | `mov w0, #1; ret` | Reports that the anti-cheat verification completed with zero infractions. |
| `0x30C1250` | `EOOEOHKLOFJ.MACGEGDGBOI` | `ShowHackDialogAndQuit()` | `ret; nop` | Neutralizes the crash/force-quit dialog creation completely. The function returns immediately without doing anything. |
| `0x30C11D8` | `EOOEOHKLOFJ.HBGCPAEJCJJ` | `GetHackCount()` | `mov w0, #0; ret` | Forces the internal hack detector to report `0` hacks detected. |

### C. Missing Content & Pack Demand Check Bypass
On boot and before starting fights, `AAPGCAPGBLG` checks if any story or event asset packs are missing.

| File Offset | Class & Method | Original Function | Our Patch | What It Accomplishes |
| :--- | :--- | :--- | :--- | :--- |
| `0x325BD24` | `AAPGCAPGBLG.MCFHOHANNDH` | `CheckPacksNeeded()` | `mov w0, #0; ret` | Returns `false` (zero packs needed). Even if an online pack check runs, the engine never triggers the `"LOADING REQUIRED!"` demand dialog. |

### D. Startup Dialogs & Modals Elimination
| File Offset | Class & Method | Original Function | Our Patch | What It Accomplishes |
| :--- | :--- | :--- | :--- | :--- |
| `0x34377F4` | `AGGMBMDDJIO.NKLGCNHLBAF` | `ShowGooglePlayWarning()` | `mov w1, #1; b 0x34a5ff4` | Silences the modal "Warning! Your game progress will be lost without Google Play Games". |
| `0x3437AFC` | `AGGMBMDDJIO.JFGBPBOCOIC` | `CheckGooglePlayLogin()` | `mov w0, #0; ret` | Disables the automatic Google Play Games login prompt. |
| `0x32D9388` | `LJBDMDHNKFM.JFGBPBOCOIC` | `ShowGDPRDialog()` | `mov w0, #0; ret` | Permanently suppresses the European GDPR Privacy Policy / Terms modal on first boot. |

---

## 4. "Changing What Changes What" (Modding Practical Guide)

### Want to freeze the match timer at 99.0 for infinite sparring?
1. Open `dump.cs` and search for `RoundTimer` or `BattleTimer`:
   * Look for `public float GetTimeLeft()` or `public void UpdateTimer(float dt)`.
2. Note the file offset of `UpdateTimer`.
3. Patch the function with `ret; nop` (`c0035fd6 1f2003d5`). The timer will never tick down.

### Want to create God Mode (Player Never Takes Damage)?
1. Search `dump.cs` for `DamageReceiver` or `CharacterHealth.ApplyDamage(float damage)`:
   * Look for method parameters taking damage: `public void TakeDamage(float damage, ...)`.
2. Check if the receiver is the player:
   * Patch `TakeDamage` to check if `this.IsPlayer` is true, or patch the damage calculation to multiply player incoming damage by `0.0`.

### What happens if the game updates to a new version (e.g. 2.47.0)?
* The exact hex file offsets (`0x3598568`, etc.) **will change** because newly added functions shift code addresses.
* To adapt:
  1. Extract `libil2cpp.so` and `global-metadata.dat` from the new APK.
  2. Run `Il2CppDumper.exe` to generate a new `dump.cs`.
  3. Search `dump.cs` for the method signatures (e.g. `bool MCFHOHANNDH()`, `bool AMELFFLEPNF()`, `ShowGDPR`).
  4. Copy the new file offsets from `dump.cs` into `so_patches` in `build_cat_blasters.py`.

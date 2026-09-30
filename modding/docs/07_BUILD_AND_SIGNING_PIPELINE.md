# Document 07: Build & Signing Pipeline

This document walks through the automated end-to-end build script ([`modding/pipeline/build_cat_blasters.py`](file:///c:/Users/Ishan/Personal/Porfolio/Shadow%20Fight%202/modding/pipeline/build_cat_blasters.py)), detailing each transformation step and how to execute, customize, or troubleshoot builds.

---

## 1. Pipeline Execution Flow

```text
[ Original Monolithic APK ]
            |
            v
[ Step 1: Apktool Decompile (-s) ]
            |
            +---> [ Step 2: Rename App Label to "Cat Blasters 9k" in strings.xml ]
            |
            +---> [ Step 3: Rebrand Package & Provider Authorities in AndroidManifest.xml ]
            |
            +---> [ Step 4: Binary String Patch in global-metadata.dat (21-byte match) ]
            |
            +---> [ Step 5: Generate & Inject Multi-Density Mipmap & Adaptive Icons ]
            |
            +---> [ Step 6: Hue-Shift & Re-serialize Dojo Textures via UnityPy ]
            |
            +---> [ Step 6b: Embed 30 Bundles + User Save Profile in assets/ ]
            |            Apply ARM64 Assembly Patches in libil2cpp.so
            |            Replace intro.mp4 with 0.04s Dummy Video
            |            Reassemble classes.dex with AssetExtractor.smali
            |
            v
[ Step 7: Apktool Rebuild (-f) ]
            |
            v
[ Step 8: 4-Byte ZipAlign & Multi-Scheme Signing (uber-apk-signer.jar) ]
            |
            v
[ Final Signed Standalone APK (bluestacks/apks/Shadow_Fight_2_MODDED_CYBERPUNK.apk) ]
```

---

## 2. Step-by-Step Breakdown

### Step 1: Decompilation
Decodes the original base APK using `apktool.jar -s -f`:
* The `-s` flag keeps native Dalvik `.dex` code un-disassembled during initial extraction for speed.

### Step 2: App Name Rebranding
Modifies `res/values/strings.xml`:
```xml
<!-- Replaced -->
<string name="app_name">Shadow Fight 2</string>
<!-- With -->
<string name="app_name">Cat Blasters 9k</string>
```

### Step 3: Package Name & Provider Authorities
In `AndroidManifest.xml`, replaces all occurrences of `com.nekki.shadowfight` with `com.nekki.catblasters`.
* **Crucial Detail**: Android requires every Content Provider authority to be globally unique across all installed apps on a device. Modifying the package name without updating provider authorities results in `INSTALL_FAILED_CONFLICTING_PROVIDER`.

### Step 4: Binary Metadata Path Synchronization
Replaces the ASCII string `com.nekki.shadowfight` with `com.nekki.catblasters` inside `assets/bin/Data/Managed/Metadata/global-metadata.dat`.
* Both strings are **exactly 21 bytes**. This enables in-place byte replacement without corrupting metadata index offsets.

### Step 5: Multi-Density Icon Generation
Takes `modding/assets/icons/cat_blasters_icon_512.png` and resizes it across 9 screen density directories (`mdpi`, `hdpi`, `xhdpi`, `xxhdpi`, `xxxhdpi`), writing `app_icon.png`, `app_icon_round.png`, `ic_launcher.png`, and adaptive foreground/background layers.

### Step 6: Unity Serialized Texture Modding
Loads Dojo serialized files from `assets/bin/Data/` with `UnityPy`, applies a 180° continuous HSV hue rotation to `Texture2D` objects, and re-serializes the binary streams.

### Step 6b: Offline Assets, Save State & Binary Patches
1. Copies all 30 bundle packages and configs from `modding/assets/downloaded_gamedata/` to `apktool_src/assets/gamedata/`.
2. Copies the user's save profile from `modding/assets/userdata/` to `apktool_src/assets/userdata/`.
3. Patches file offsets in `lib/arm64-v8a/libil2cpp.so` (anti-cheat, XML hash checks, missing pack checks, Google Play warning, GDPR dialog, VIP infinite energy, and arbitrary round control).
4. Replaces `intro.mp4` with a 0.04s (1-frame) black video to skip the 15-second opening cinematic.
5. Assembles `classes.dex` using `smali.jar` from `modding/build_cache/baksmali_multidex/`.

### Step 7: Apktool Rebuild
Rebuilds the APK directory using:
```powershell
java -jar apktool.jar b apktool_src -o cat_blasters_unsigned.apk -f
```
The `-f` (`--force-all`) flag guarantees that cached assets are wiped and newly copied bundles are freshly packed.

### Step 8: Zipaligning & Signing
Invokes `uber-apk-signer.jar`:
```powershell
java -jar uber-apk-signer.jar -a cat_blasters_unsigned.apk -o cat_signed --allowResign
```
1. Performs 4-byte zip alignment (`zipalign`) for direct memory-mapped library loading.
2. Injects Android Signature Scheme **v1** (JAR signature), **v2** (APK Signing Block), and **v3** (Key rotation block) using `modding/tools/debug.keystore`.
3. Verifies signature blocks and copies final output to:
   `bluestacks/apks/SF2_Modded_v4.apk` (or custom `--output` target).

---

## 3. How to Run the Build

To trigger the full pipeline from terminal:

```powershell
# Standard build (5 rounds to win -> SF2_Modded_v4.apk):
.venv\Scripts\python modding\pipeline\build_cat_blasters.py

# Custom round target (e.g. single-round deathmatch or marathon bout):
.venv\Scripts\python modding\pipeline\build_cat_blasters.py --rounds 1
.venv\Scripts\python modding\pipeline\build_cat_blasters.py --rounds 8 --output SF2_Modded_v4_8_rounds.apk
```

Typical execution time: **~30 to 45 seconds** (including reassembling dex, packaging 330+ MB of assets, and signing).

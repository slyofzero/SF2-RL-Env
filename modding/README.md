# Shadow Fight 2 Modding Documentation Hub

Welcome to the **Shadow Fight 2 Modding & Reverse Engineering Documentation**. This directory houses the complete asset manipulation pipelines, native IL2CPP binary patches, save profile injectors, and automated build tools.

---

## 1. Quick Reference: "Changing What Changes What?"

Use this index to quickly locate which file to edit to achieve your desired change:

| What do you want to modify? | Files to Edit | Documentation Guide |
| :--- | :--- | :--- |
| **Arena Visuals & Colors** (Dojo, Mountains, Lanterns) | [`modding/pipeline/build_cat_blasters.py`](pipeline/build_cat_blasters.py#L149) (change `shift_deg`) | [02_TEXTURES_AND_GRAPHICS.md](docs/02_TEXTURES_AND_GRAPHICS.md) |
| **Custom Launcher Icon / Artwork** | Place 512x512 PNG at [`modding/assets/icons/cat_blasters_icon_512.png`](assets/icons/cat_blasters_icon_512.png) | [02_TEXTURES_AND_GRAPHICS.md](docs/02_TEXTURES_AND_GRAPHICS.md) |
| **App Title & Rebranded Package Name** | `build_cat_blasters.py` (`Step 2`, `Step 3`, `Step 4`) | [07_BUILD_AND_SIGNING_PIPELINE.md](docs/07_BUILD_AND_SIGNING_PIPELINE.md) |
| **Player Level, Coins, Gems & Unlocked Weapons** | [`modding/assets/userdata/users.xml`](assets/userdata/users.xml) | [04_SAVE_PROFILES_AND_PROGRESSION.md](docs/04_SAVE_PROFILES_AND_PROGRESSION.md) |
| **Tutorial Gates & Map Unlocks** (Skip Kenji, Shin, Lynx) | `users.xml` (`Tutorial="END"`, `MapFocus`) | [04_SAVE_PROFILES_AND_PROGRESSION.md](docs/04_SAVE_PROFILES_AND_PROGRESSION.md) |
| **Anti-Cheat, Hash Bypasses & Popup Elimination** | `so_patches` in `build_cat_blasters.py` | [03_IL2CPP_AND_BINARY_PATCHING.md](docs/03_IL2CPP_AND_BINARY_PATCHING.md) |
| **Match Timer Freeze / Infinite Sparring** | ARM64 patch in `libil2cpp.so` (`BattleTimer`) | [03_IL2CPP_AND_BINARY_PATCHING.md](docs/03_IL2CPP_AND_BINARY_PATCHING.md) |
| **Download Missing Chapters / Event Bundles** | Run `.agents/skills/game-content-downloader/scripts/download_packs.py` | [05_OFFLINE_BUNDLES_AND_CDN.md](docs/05_OFFLINE_BUNDLES_AND_CDN.md) |
| **Startup Self-Extractor Files & Markers** | [`AssetExtractor.smali`](build_cache/baksmali_multidex/com/nekki/catblasters/AssetExtractor.smali) | [06_STARTUP_SMALI_HOOK.md](docs/06_STARTUP_SMALI_HOOK.md) |
| **Rebuild & Sign Final Modded APK** | Run `python modding/pipeline/build_cat_blasters.py` | [07_BUILD_AND_SIGNING_PIPELINE.md](docs/07_BUILD_AND_SIGNING_PIPELINE.md) |

---

## 2. In-Depth Subsystem Guides (`modding/docs/`)

Explore the dedicated documentation files for deep-dive technical explanations:

1. **[01_ARCHITECTURE_OVERVIEW.md](docs/01_ARCHITECTURE_OVERVIEW.md)**
   * The Unity Engine + IL2CPP execution stack.
   * Writable external storage (`/sdcard/Android/data/.../`) vs compressed APK assets.
   * Split APK packages (AAB/XAPK) vs universal standalone APKs.

2. **[02_TEXTURES_AND_GRAPHICS.md](docs/02_TEXTURES_AND_GRAPHICS.md)**
   * How textures are stored in hash-named Unity serialized files in `assets/bin/Data/`.
   * Complete Dojo arena texture mapping table.
   * Color transformations using continuous HSV hue rotations.
   * Multi-density launcher icon generation.

3. **[03_IL2CPP_AND_BINARY_PATCHING.md](docs/03_IL2CPP_AND_BINARY_PATCHING.md)**
   * Reverse engineering `libil2cpp.so` using `Il2CppDumper` and `dump.cs`.
   * ARM64 assembly mechanics (little-endian hex opcodes).
   * Exact file offsets and functions patched: XML hash bypasses, "Data Corrupted" anti-cheat neutralization, missing pack check bypass, Google Play warning removal, and GDPR consent suppression.

4. **[04_SAVE_PROFILES_AND_PROGRESSION.md](docs/04_SAVE_PROFILES_AND_PROGRESSION.md)**
   * Complete schema of `users.xml` and `users_backup.xml`.
   * The tutorial state machine (`JAKHNKEHNBE`) and how setting `Tutorial="END"` unlocks the Act 1 map.
   * How the companion MD5 hash verification system functions.

5. **[05_OFFLINE_BUNDLES_AND_CDN.md](docs/05_OFFLINE_BUNDLES_AND_CDN.md)**
   * Full inventory of all 30 pre-bundled game asset packages (~188 MB).
   * The CDN catalog (`config_cdn.xml`) vs local registry (`packs.xml`).
   * How the 31.58 MB missing content prompt was diagnosed and resolved.

6. **[06_STARTUP_SMALI_HOOK.md](docs/06_STARTUP_SMALI_HOOK.md)**
   * Injecting `AssetExtractor.smali` into `MultiDexApplication.onCreate()`.
   * Pre-extracting assets to external storage in ~250ms before Unity boots.
   * Marker files (`.all_packs_v2`, `.provisioned_v4`) to ensure zero startup lag on subsequent boots.

7. **[07_BUILD_AND_SIGNING_PIPELINE.md](docs/07_BUILD_AND_SIGNING_PIPELINE.md)**
   * Step-by-step walkthrough of `build_cat_blasters.py`.
   * Rebranding mechanics and exact-byte metadata preservation.
   * Zip alignment and multi-scheme (v1/v2/v3) signing.

---

## 3. Directory Layout

```text
modding/
├── README.md                      <-- Documentation hub (this file)
├── docs/                          <-- Distributed in-depth technical guides
│   ├── 01_ARCHITECTURE_OVERVIEW.md
│   ├── 02_TEXTURES_AND_GRAPHICS.md
│   ├── 03_IL2CPP_AND_BINARY_PATCHING.md
│   ├── 04_SAVE_PROFILES_AND_PROGRESSION.md
│   ├── 05_OFFLINE_BUNDLES_AND_CDN.md
│   ├── 06_STARTUP_SMALI_HOOK.md
│   └── 07_BUILD_AND_SIGNING_PIPELINE.md
├── packages/                      <-- Original upstream XAPK packages
├── pipeline/                      <-- Executable build scripts
│   ├── build_cat_blasters.py      <-- Master APK builder, patcher & signer
│   ├── build_standalone_apk.py    <-- Split APK merger
│   └── download_all_story_packs.py<-- CDN bundle downloader
├── assets/                        <-- Extracted textures, icons & save states
│   ├── downloaded_gamedata/       <-- Pre-downloaded bundles & catalog files
│   ├── userdata/                  <-- Pre-configured completed save state
│   ├── icons/                     <-- Source 512x512 launcher icon
│   └── dummy_intro.mp4            <-- Instant-skip 0.04s video replacement
└── tools/                         <-- Binaries & keys (apktool, uber-apk-signer, Il2CppDumper)
```

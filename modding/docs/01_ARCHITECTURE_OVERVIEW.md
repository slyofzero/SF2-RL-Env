# Document 01: Engine & Runtime Architecture Overview

This document provides a foundational architectural breakdown of *Shadow Fight 2* (v2.46.0) as an Android application built on the Unity Engine with Ahead-of-Time (AOT) compiled IL2CPP logic.

---

## 1. High-Level Engine Stack

```text
+-------------------------------------------------------------------+
|                     Android Application Layer                    |
|  (AndroidManifest.xml, Application.onCreate(), MultiDex, Java)    |
+---------------------------------+---------------------------------+
                                  | Native JNI Bridge
+---------------------------------v---------------------------------+
|                       Unity Engine Runtime                        |
|       (libunity.so - Graphics, Physics, Audio, AssetManager)      |
+---------------------------------+---------------------------------+
                                  |
+---------------------------------v---------------------------------+
|                    Compiled Game Logic (IL2CPP)                   |
|  - libil2cpp.so: Compiled native C++ machine code (ARM64/ARM32)  |
|  - global-metadata.dat: String pool, type definitions, method IDs |
+---------------------------------+---------------------------------+
                                  |
+---------------------------------v---------------------------------+
|                       Asset Data Subsystem                        |
|  - APK assets/bin/Data/*: Serialized Unity scene files & textures|
|  - External Storage (/sdcard/Android/data/.../files/):           |
|      * gamedata/bundles/* (Downloaded AssetBundles)               |
|      * userdata/* (XML progress saves, settings binaries)         |
+-------------------------------------------------------------------+
```

---

## 2. Core Components & File Roles

| Path in Repository / APK | Component | What It Does |
| :--- | :--- | :--- |
| `lib/arm64-v8a/libunity.so` | Unity Core | The official Unity engine runtime. Renders frames, initializes OpenGL/Vulkan contexts, handles audio, and coordinates asset loading. |
| `lib/arm64-v8a/libil2cpp.so` | Game Logic | Contains the entire game logic (combat math, AI fighters, anti-cheat, UI controllers, save management) compiled Ahead-of-Time into ARM64 instructions. |
| `assets/bin/Data/Managed/Metadata/global-metadata.dat` | Type Metadata | The central symbol table. Contains class names, method signatures, field offsets, and hardcoded strings. Reconstructed by `Il2CppDumper`. |
| `assets/bin/Data/<hash>` | Serialized Assets | Unity binary serialized files containing models, textures, animations, shaders, and UI layouts for the base game. |
| `AndroidManifest.xml` | App Manifest | Declares package name, main Activity, multidex application class, provider authorities, and permissions. |
| `classes.dex` (through `classes8.dex`) | Dalvik Bytecode | Java bytecode executed by the Android ART runtime before native libraries initialize. Hosts our custom startup self-extractor. |

---

## 3. Storage Hierarchy: APK Assets vs. External Files

Understanding where the game expects files to reside is critical to modding:

### Read-Only APK Assets (`assets/`)
Files bundled inside the APK package (e.g. `assets/bin/Data/`, `assets/database/intro.mp4`).
* **Characteristics**: Read-only, compressed inside zip storage.
* **Limitation**: Unity file streaming APIs and native C++ file routines cannot directly write to or update files inside the APK.

### Writable External Storage (`/sdcard/Android/data/<package>/files/`)
Android persistent storage dedicated to the package.
* **`gamedata/`**: Stores downloaded asset packs (`bundles/`), the content catalog (`packs.xml`), CDN configuration (`config_cdn.xml`), and local cache.
* **`userdata/`**: Stores player progress (`users.xml`), emergency backup (`users_backup.xml`), and binary settings (`localSettings.bin`, `gamingServiceSettings.bin`).

If external storage is empty on fresh boot, the game assumes it is a new installation and triggers network CDN downloads and first-time tutorial sequences. Our pipeline bypasses this via the `AssetExtractor` startup hook.

---

## 4. Split APKs (XAPK) vs. Monolithic Standalone APKs

* **Upstream Distribution**: The original game is distributed on APKPure as a multi-split `.xapk` archive containing `com.nekki.shadowfight.apk` (base with no `.so` files) and split configs (`config.arm64_v8a.apk`, `config.armeabi_v7a.apk`). Emulators reject split archives.
* **Our Standalone Architecture**: Our pipeline merges native architecture libraries from the config packages directly into the base APK, zip-aligns to 4-byte boundaries, and applies Android v1, v2, and v3 signature blocks. The resulting APK is completely universal and installs on any emulator or physical Android device with a single click.

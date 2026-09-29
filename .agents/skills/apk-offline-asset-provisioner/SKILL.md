---
name: apk-offline-asset-provisioner
description: Pre-bundle external DLC asset packs and customized user save profiles directly inside an APK, and inject a smali startup hook into classes.dex (Application.onCreate) to extract them automatically on first launch before the game engine initializes. Use whenever eliminating in-game download screens, offline-enabling mobile games, or persisting save states across uninstalls and reinstalls.
---

# APK Offline Asset & Save State Self-Provisioner

This skill provides an end-to-end framework for embedding large asset bundles and custom user save states directly inside an APK and auto-extracting them to external storage on application boot before the game engine (Unity/Unreal) loads.

## When to Use
- A game requires downloading 50MB-500MB of external asset packs (DLC, zones, models, voices) on first launch.
- Repetitive, unskippable tutorials need to be permanently bypassed on fresh installs by auto-injecting a completed save profile.
- You want an entirely offline, self-contained standalone APK that requires no network connectivity.

## The Technical Problem
- APK `assets/` are compressed read-only files inside the zip archive.
- Game engines and native C++ code (`libunity.so`, `libil2cpp.so`) frequently expect DLC assets and user profiles to exist as unpacked, writable files on external storage:
  `/sdcard/Android/data/<package>/files/`
- If persistent storage is empty on fresh install, the engine triggers a network demand check and halts at a download screen.

## The Solution: Smali Startup Hook
We decompile `classes.dex`, inject a specialized helper (`AssetExtractor.smali`), and hook the application's root entry point (`MultiDexApplication.onCreate()` or custom `Application.onCreate()`). On startup:
1. `AssetExtractor` runs in ~200-300ms.
2. Checks if a versioned marker file (e.g. `.all_packs_v2`, `.provisioned_v4`) exists.
3. If absent, copies all embedded bundles and XML/bin save profiles from APK `assets/` to `/sdcard/Android/data/<package>/files/`.
4. Writes the marker file and returns control.
5. The game engine boots, detects all files already present locally, and skips all downloads and tutorials.

## Workflow

### 1. Structure Embedded Assets
In the APK's root `assets/` directory (inside `apktool_src/assets/`), place:
- `assets/gamedata/bundles/*`: All pre-downloaded game bundles.
- `assets/gamedata/packs.xml`: The catalog mapping names to bundle files and hashes.
- `assets/userdata/*`: Pre-configured user save (`users.xml`, `users.xml.hash`, `localSettings.bin`, etc.).

### 2. Craft `AssetExtractor.smali`
Create `com/<package>/AssetExtractor.smali`:

```smali
.class public Lcom/nekki/catblasters/AssetExtractor;
.super Ljava/lang/Object;
.source "AssetExtractor.java"

.method public static extractIfNeeded(Landroid/content/Context;)V
    .registers 9
    :try_start_0
    const/4 v0, 0x0
    invoke-virtual {p0, v0}, Landroid/content/Context;->getExternalFilesDir(Ljava/lang/String;)Ljava/io/File;
    move-result-object v0

    if-nez v0, :cond_0
    new-instance v0, Ljava/io/File;
    new-instance v1, Ljava/lang/StringBuilder;
    invoke-direct {v1}, Ljava/lang/StringBuilder;-><init>()V
    const-string v2, "/sdcard/Android/data/"
    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {p0}, Landroid/content/Context;->getPackageName()Ljava/lang/String;
    move-result-object v2
    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    const-string v2, "/files"
    invoke-virtual {v1, v2}, Ljava/lang/StringBuilder;->append(Ljava/lang/String;)Ljava/lang/StringBuilder;
    invoke-virtual {v1}, Ljava/lang/StringBuilder;->toString()Ljava/lang/String;
    move-result-object v1
    invoke-direct {v0, v1}, Ljava/io/File;-><init>(Ljava/lang/String;)V

    :cond_0
    # Check if bundles marker exists
    new-instance v1, Ljava/io/File;
    const-string v2, "gamedata/.all_packs_v2"
    invoke-direct {v1, v0, v2}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V
    invoke-virtual {v1}, Ljava/io/File;->exists()Z
    move-result v2
    if-eqz v2, :cond_1
    goto :goto_user_check

    :cond_1
    # Extract bundles
    const-string v1, "gamedata/bundles/ZONE_1"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V
    const-string v1, "gamedata/packs.xml"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    new-instance v1, Ljava/io/File;
    const-string v2, "gamedata/.all_packs_v2"
    invoke-direct {v1, v0, v2}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V
    invoke-virtual {v1}, Ljava/io/File;->createNewFile()Z

    :goto_user_check
    # Check if user save marker exists
    new-instance v1, Ljava/io/File;
    const-string v2, "userdata/.provisioned_v4"
    invoke-direct {v1, v0, v2}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V
    invoke-virtual {v1}, Ljava/io/File;->exists()Z
    move-result v2
    if-eqz v2, :cond_2
    return-void

    :cond_2
    const-string v1, "userdata/users.xml"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V
    const-string v1, "userdata/users.xml.hash"
    invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V

    new-instance v1, Ljava/io/File;
    const-string v2, "userdata/.provisioned_v4"
    invoke-direct {v1, v0, v2}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V
    invoke-virtual {v1}, Ljava/io/File;->createNewFile()Z
    :try_end_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_0
    goto :goto_0

    :catch_0
    move-exception v0
    :goto_0
    return-void
.end method

.method private static copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V
    .registers 9
    :try_start_0
    new-instance v0, Ljava/io/File;
    invoke-direct {v0, p1, p2}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V
    invoke-virtual {v0}, Ljava/io/File;->getParentFile()Ljava/io/File;
    move-result-object v1
    if-eqz v1, :cond_0
    invoke-virtual {v1}, Ljava/io/File;->mkdirs()Z

    :cond_0
    invoke-virtual {p0}, Landroid/content/Context;->getAssets()Landroid/content/res/AssetManager;
    move-result-object v1
    invoke-virtual {v1, p2}, Landroid/content/res/AssetManager;->open(Ljava/lang/String;)Ljava/io/InputStream;
    move-result-object v1

    new-instance v2, Ljava/io/FileOutputStream;
    invoke-direct {v2, v0}, Ljava/io/FileOutputStream;-><init>(Ljava/io/File;)V

    const/high16 v3, 0x10000
    new-array v3, v3, [B

    :goto_0
    invoke-virtual {v1, v3}, Ljava/io/InputStream;->read([B)I
    move-result v4
    const/4 v5, -0x1
    if-eq v4, v5, :cond_1
    const/4 v5, 0x0
    invoke-virtual {v2, v3, v5, v4}, Ljava/io/OutputStream;->write([BII)V
    goto :goto_0

    :cond_1
    invoke-virtual {v2}, Ljava/io/OutputStream;->flush()V
    invoke-virtual {v2}, Ljava/io/OutputStream;->close()V
    invoke-virtual {v1}, Ljava/io/InputStream;->close()V
    :try_end_0
    .catch Ljava/lang/Exception; {:try_start_0 .. :try_end_0} :catch_0
    :goto_1
    return-void

    :catch_0
    move-exception v0
    goto :goto_1
.end method
```

### 3. Hook Application Entry Point
In `androidx/multidex/MultiDexApplication.smali` (or whatever class is declared in `AndroidManifest.xml` under `<application android:name="...">`):

```smali
.method public onCreate()V
    .registers 2

    # Inject call at the very beginning of onCreate:
    invoke-static {p0}, Lcom/nekki/catblasters/AssetExtractor;->extractIfNeeded(Landroid/content/Context;)V

    invoke-super {p0}, Landroid/app/Application;->onCreate()V
    return-void
.end method
```

### 4. Assemble and Rebuild
Assemble `classes.dex` using `smali.jar`:
```bash
java -jar smali.jar a baksmali_multidex/ -o apktool_src/classes.dex
```
Rebuild and sign the APK via `apktool` and `uber-apk-signer.jar`.

## Best Practices & Lessons Learned
1. **Always Use Versioned Marker Files**: Never rely on checking if a specific bundle exists (e.g. `ZONE_1`), because if new bundles (`ZONE_2`, `EVENTS`) are added to an updated APK, the check will see `ZONE_1` already present and skip extracting the newly added files. Using `.all_packs_v1`, `.all_packs_v2`, `.provisioned_v4` guarantees upgrade safety.
2. **Synchronize Cryptographic Hashes**: Mobile games frequently verify MD5 hashes stored in companion files (e.g. `users.xml.hash`, `packs.xml.hash`). Always calculate and update the MD5 string in the hash files when packaging modified profiles.

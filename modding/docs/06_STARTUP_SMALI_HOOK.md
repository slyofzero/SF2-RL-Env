# Document 06: Startup Smali Hook & Self-Extractor

This document explains how our custom Java/Smali startup hook (`AssetExtractor.smali`) is injected into the application's bytecode, how it extracts offline bundles and save profiles before the Unity Engine initializes, and how to maintain or extend it.

---

## 1. Why a Smali Startup Hook is Necessary

1. **Unity Engine Dependency**: When `libunity.so` initializes, its C++ file loader directly queries `/sdcard/Android/data/<package>/files/` for DLC packs and user saves.
2. **Timing Problem**: If the bundles are merely stored inside the APK's `assets/` folder, Unity's C++ code cannot see them because standard filesystem APIs cannot navigate inside a compressed APK archive without Android's Java `AssetManager`.
3. **The Solution**: We inject code into Android's native Application lifecycle (`Application.onCreate()`). This method executes **before** any native library (`libunity.so`, `libil2cpp.so`) is loaded into memory.
4. In ~250-300ms, our hook streams all bundles and save files into the persistent external storage folder, creating a ready-made environment before the engine ever wakes up.

---

## 2. Injection Architecture in `classes.dex`

```text
[ Android System launches App ]
               |
               v
[ MultiDexApplication.onCreate() ]
               |
               +---> [ AssetExtractor.extractIfNeeded(Context) ]
               |          |
               |          +-- Marker check (.all_packs_v2)?
               |          |     NO  -> Copy all 30 bundles + packs.xml from APK assets
               |          |            Create marker file .all_packs_v2
               |          |     YES -> Skip bundle extraction (0ms)
               |          |
               |          +-- Marker check (.provisioned_v4)?
               |                NO  -> Copy users.xml + hashes to userdata/
               |                       Create marker file .provisioned_v4
               |                YES -> Skip save extraction (0ms)
               |
               v
[ UnityPlayerActivity / Native Engine Boot ]
               |
               v
[ libunity.so & libil2cpp.so Initialize ]
(Detects all bundles and save state already in place -> 100% offline, zero downloads)
```

---

## 3. Dissecting `AssetExtractor.smali`

Located at: [`modding/build_cache/baksmali_multidex/com/nekki/catblasters/AssetExtractor.smali`](file:///c:/Users/Ishan/Personal/Porfolio/Shadow%20Fight%202/modding/build_cache/baksmali_multidex/com/nekki/catblasters/AssetExtractor.smali).

### A. Dynamic Storage Resolution
Android 10+ handles external storage differently. The method first attempts standard context resolution with a fallback to raw path building:
```smali
const/4 v0, 0x0
invoke-virtual {p0, v0}, Landroid/content/Context;->getExternalFilesDir(Ljava/lang/String;)Ljava/io/File;
move-result-object v0
if-nez v0, :cond_0

# Fallback: /sdcard/Android/data/<package>/files
new-instance v0, Ljava/io/File;
...
invoke-direct {v0, v1}, Ljava/io/File;-><init>(Ljava/lang/String;)V
:cond_0
```

### B. Versioned Marker Checking
To ensure high performance, extraction only runs once on install or upgrade:
```smali
# 1. Check if bundles marker exists
new-instance v1, Ljava/io/File;
const-string v2, "gamedata/.all_packs_v2"
invoke-direct {v1, v0, v2}, Ljava/io/File;-><init>(Ljava/io/File;Ljava/lang/String;)V

invoke-virtual {v1}, Ljava/io/File;->exists()Z
move-result v2
if-eqz v2, :cond_1
goto :goto_user_check  # Skip bundle extraction
```

### C. Direct Asset Streaming
The helper method `copyAsset(Context context, File targetBaseDir, String assetPath)`:
1. Calls `new File(targetBaseDir, assetPath).getParentFile().mkdirs()`.
2. Opens stream via `context.getAssets().open(assetPath)`.
3. Streams bytes in 64 KB chunks (`0x10000` bytes) via `FileOutputStream`.
4. Flushes and closes streams.

---

## 4. "Changing What Changes What" (Extending the Hook)

### Want to add a new asset file to the auto-extraction list?
1. Open [`AssetExtractor.smali`](file:///c:/Users/Ishan/Personal/Porfolio/Shadow%20Fight%202/modding/build_cache/baksmali_multidex/com/nekki/catblasters/AssetExtractor.smali).
2. Under `:cond_1` (for game bundles) or `:cond_2` (for user profiles), add:
   ```smali
   const-string v1, "gamedata/bundles/MY_NEW_BUNDLE"
   invoke-static {p0, v0, v1}, Lcom/nekki/catblasters/AssetExtractor;->copyAsset(Landroid/content/Context;Ljava/io/File;Ljava/lang/String;)V
   ```
3. Bump the marker string:
   * Change `"gamedata/.all_packs_v2"` to `"gamedata/.all_packs_v3"`.
4. The build pipeline will re-assemble `classes.dex` using `smali.jar` automatically when you run `build_cat_blasters.py`.

### Why must we bump the marker file name?
If you add new files to the extraction list without changing the marker name (`.all_packs_v2`), any device where the app was already installed will see the existing `.all_packs_v2` file and **skip extraction**, leaving your new files unextracted! Incrementing the marker guarantees that existing installations re-extract the updated assets.

# Document 02: Textures & Graphical Modding

This document explains how textures, backgrounds, and sprites are stored in Unity serialized files, how to extract and modify them, and how changing specific files alters in-game visuals.

---

## 1. How Unity Stores Textures

Inside `assets/bin/Data/`, Unity organizes game content into hash-named serialized files (e.g. `a270fac21f3177e428a9c49164a217c2`).
* Each serialized file contains a binary table of Unity objects (`Texture2D`, `Sprite`, `Shader`, `Material`, `GameObject`).
* Each `Texture2D` object has an internal name (`m_Name`), width, height, format tag (e.g. ASTC, ETC2, RGBA32), and raw image pixel stream.
* **Why raw hex editing fails**: You cannot simply swap raw bytes in a hex editor because Unity prefixes serialized objects with byte-length fields and type metadata. If the replaced image byte length differs, the entire file becomes corrupt.
* **Why `UnityPy` succeeds**: `UnityPy` understands Unity's internal serialization format. When you assign `data.image = new_image` and call `data.save()`, `UnityPy` re-encodes the image stream, updates the internal byte count, and recalculates the header offsets cleanly.

---

## 2. Dojo Arena Texture Mapping Table

The starting arena (**The Dojo**) consists of multi-layered parallax sprites and high/low resolution fallback pairs:

| Unity File Path in APK | Texture Asset Name (`m_Name`) | Resolution | In-Game Visual Element |
| :--- | :--- | :--- | :--- |
| `assets/bin/Data/a270fac21f3177e428a9c49164a217c2` | `dojo_bg` | 1024x512 | The outer mountain panorama, sunset/twilight sky backdrop. |
| `assets/bin/Data/edba0f6b88dea6144baef9415426de20` | `dojo_bg_low` | 512x256 | Low-resolution fallback mountain panorama for low-end graphics mode. |
| `assets/bin/Data/78a8599a4223b28419c1b7417ca03a4d` | `dojo_atlas_layer1` | 1024x1024 | Cherry blossom branches, tree silhouettes, and foreground leaves. |
| `assets/bin/Data/dd833943f1e94264e9b19dc78c3dd346` | `dojo_atlas_layer2` | 1024x1024 | Interior room: wooden floor planks, pillars, hanging lanterns, sliding shoji screens. |
| `assets/bin/Data/ca5b9cfa51d2ed44cbbc5daf06b4589d` | `dojo_atlas_layer2_low` | 512x512 | Low-resolution fallback for interior shoji screens and room elements. |
| `assets/bin/Data/835de2e8aa03eb5458bccaa42c4694c2` | `dojo_atlas_layer3` | 512x512 | Volumetric light beam shining through the open doorway. |
| `assets/bin/Data/a475dfa934fc5384ebc0f36e30bb7b30` | `dojo_atlas_layer3_low` | 256x256 | Low-resolution light beam fallback. |

---

## 3. "Changing What Changes What" (Visual Customization Guide)

### Want to change the Dojo theme from Cyan to Crimson or Gold?
1. Open [`modding/pipeline/build_cat_blasters.py`](file:///c:/Users/Ishan/Personal/Porfolio/Shadow%20Fight%202/modding/pipeline/build_cat_blasters.py#L149).
2. Locate the texture injection loop in `Step 6`:
   ```python
   modded_bytes = apply_texture_mod(raw, tex_name, shift_deg=180.0)
   ```
3. Change `shift_deg`:
   * `0.0`: Original warm peach/amber aesthetic.
   * `90.0`: Emerald forest green theme.
   * `180.0`: Cyberpunk cyan / deep sapphire theme (current mod).
   * `270.0`: Crimson violet / neon magenta theme.
4. Run:
   ```powershell
   .venv\Scripts\python modding\pipeline\build_cat_blasters.py
   ```

### Want to replace the background with your own custom image?
1. Prepare a PNG image with the exact resolution (e.g. `1024x512` for `dojo_bg`).
2. Save it to `modding/assets/modified/dojo_bg.png`.
3. In `apply_texture_mod()`, load your PNG and assign it directly to `data.image`:
   ```python
   from PIL import Image
   custom_img = Image.open("modding/assets/modified/dojo_bg.png")
   data.image = custom_img
   data.save()
   ```

### Want to find textures for other arenas (Act 2, Act 3, Boss arenas)?
Run a scan across all Unity serialized files in `apktool_src/assets/bin/Data/`:
```python
import os, UnityPy

unity_dir = r"modding\build_cache\apktool_src\assets\bin\Data"
for fname in os.listdir(unity_dir):
    fpath = os.path.join(unity_dir, fname)
    if os.path.isfile(fpath):
        try:
            env = UnityPy.load(fpath)
            for obj in env.objects:
                if obj.type.name == "Texture2D":
                    data = obj.read()
                    if "arena" in data.m_Name.lower() or "bg" in data.m_Name.lower():
                        print(f"File {fname} contains: {data.m_Name} ({data.image.size})")
        except:
            pass
```

---

## 4. App Launcher Icon Customization

Launcher icons are standard Android PNG drawables stored in `res/mipmap-*` and `res/drawable-*`.

### Densities and Pixel Dimensions
| Folder Path | Icon Dimensions | Used For |
| :--- | :--- | :--- |
| `res/mipmap-mdpi/` | 48 x 48 px | Medium density displays |
| `res/mipmap-hdpi/` | 72 x 72 px | High density displays |
| `res/mipmap-xhdpi/` | 96 x 96 px | Extra-high density displays |
| `res/mipmap-xxhdpi/` | 144 x 144 px | Double extra-high density displays |
| `res/mipmap-xxxhdpi/` | 192 x 192 px | Ultra-high density displays (modern phones & emulators) |

### Injected Icon Assets
To replace launcher artwork:
1. Place a 512x512 master PNG in [`modding/assets/icons/cat_blasters_icon_512.png`](file:///c:/Users/Ishan/Personal/Porfolio/Shadow%20Fight%202/modding/assets/icons/cat_blasters_icon_512.png).
2. The build script resizes this image using high-quality Lanczos resampling and writes:
   * `app_icon.png` (Standard square icon)
   * `app_icon_round.png` (Android circular launcher icon)
   * `ic_launcher.png` (Legacy Android launcher icon)
   * `ic_launcher_foreground.png` (Adaptive icon foreground layer)
   * `ic_launcher_background.png` (Dark navy neon background layer `#0c101a`)

---
name: apk-rebranding-identity
description: Rebrand an Android app with a custom title, launcher artwork across all mipmap densities, modified package identity, and updated provider authorities. Preserves native binary compatibility with Unity global-metadata.dat via exact-byte replacement to enable side-by-side installation with the original unmodded game.
---

# Android APK Rebranding & Identity Customization

This skill provides a systematic procedure for changing an Android app's visible identity (app label, icons) and internal package name to allow side-by-side installation alongside the original application without conflicts.

## When to Use
- You want to install a modded or experimental APK alongside the original unmodded app on the same Android device or emulator.
- Avoiding Android installation error `INSTALL_FAILED_CONFLICTING_PROVIDER`.
- Customizing app title, adaptive launcher drawables, and mipmap icon assets.
- Preserving Unity IL2CPP runtime compatibility when changing package names.

## Prerequisites
- `apktool.jar` (v2.10.0+ recommended).
- Pillow (`PIL`) for high-quality Lanczos icon resizing.
- `uber-apk-signer.jar` for final signing.

## The Side-by-Side Installation Challenge
Installing two apps with identical package names (`com.company.game`) or identical Content Provider authorities causes Android to reject the installation with:
`INSTALL_FAILED_CONFLICTING_PROVIDER`

However, simply changing the package name in `AndroidManifest.xml` can break Unity IL2CPP games if native code calls Java via JNI referencing hardcoded package names stored in `global-metadata.dat`.

## The Exact-Byte Replacement Solution
To preserve binary offsets in `global-metadata.dat`:
Choose a new package name with the **exact same character length** as the original:
- Original: `com.nekki.shadowfight` (21 characters)
- Rebranded: `com.nekki.catblasters` (21 characters)

Because lengths match identically, the package string can be safely replaced in the binary metadata table without shifting string literal offsets or breaking index tables.

## Rebranding Workflow

### 1. Update App Name in Resources
In `res/values/strings.xml`:
```xml
<!-- Replace original label -->
<string name="app_name">My Custom Game</string>
```

### 2. Update AndroidManifest.xml Package and Authorities
Replace all instances of the old package name in:
- `package="com.nekki.catblasters"`
- All `<provider android:authorities="com.nekki.catblasters....">`
- FileProvider paths and intent filters.

```python
with open("AndroidManifest.xml", "r", encoding="utf-8") as f:
    manifest = f.read()

manifest = manifest.replace("com.nekki.shadowfight", "com.nekki.catblasters")

with open("AndroidManifest.xml", "w", encoding="utf-8") as f:
    f.write(manifest)
```

### 3. Binary Patch `global-metadata.dat`
```python
meta_path = "assets/bin/Data/Managed/Metadata/global-metadata.dat"
with open(meta_path, "rb") as f:
    data = f.read()

old_pkg = b"com.nekki.shadowfight"
new_pkg = b"com.nekki.catblasters"
assert len(old_pkg) == len(new_pkg), "Package names must be exact same byte length!"

data = data.replace(old_pkg, new_pkg)

with open(meta_path, "wb") as f:
    f.write(data)
```

### 4. Regenerate Launcher and Mipmap Icons
Using a 512x512 high-resolution source PNG, resize and replace standard launcher icons and adaptive icon drawables across all density buckets:

```python
from PIL import Image
import os

def inject_icons(source_icon_path: str, apktool_root: str):
    icon_src = Image.open(source_icon_path)
    
    icon_densities = {
        "res/mipmap-mdpi": 48,
        "res/mipmap-hdpi": 72,
        "res/mipmap-xhdpi": 96,
        "res/mipmap-xxhdpi": 144,
        "res/mipmap-xxxhdpi": 192,
        "res/drawable-mdpi": 48,
        "res/drawable-nodpi": 96,
        "res/drawable-xhdpi-v11": 96,
        "res/drawable-xxhdpi-v11": 144,
    }

    target_filenames = [
        "app_icon.png",
        "app_icon_round.png",
        "ic_launcher.png",
        "ic_launcher_foreground.png",
    ]

    for rel_folder, px in icon_densities.items():
        folder = os.path.join(apktool_root, rel_folder)
        if not os.path.exists(folder):
            continue
        resized = icon_src.resize((px, px), Image.Resampling.LANCZOS)
        for fname in target_filenames:
            fpath = os.path.join(folder, fname)
            if os.path.exists(fpath):
                resized.save(fpath)
```

## Critical Pitfalls
1. **Content Providers**: If you change the package name in `AndroidManifest.xml` but miss any `<provider android:authorities="...">` tag, Android will allow the build to succeed but throw `INSTALL_FAILED_CONFLICTING_PROVIDER` on install.
2. **Byte Length Mismatch**: Changing string lengths in `global-metadata.dat` without rebuilding string index tables will corrupt IL2CPP symbol resolution, causing immediate crash-on-launch with `SIGSEGV`.

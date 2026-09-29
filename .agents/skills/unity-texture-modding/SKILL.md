---
name: unity-texture-modding
description: Extract, modify, and reinject textures and sprites into Unity serialized asset files (assets/bin/Data/*) using Python and UnityPy without breaking binary serialization. Use whenever modifying in-game visuals, environments, UI textures, or sprites in Unity-based mobile and desktop games.
---

# Unity Texture Modding & Asset Injection

This skill guides you through extracting, transforming, and reinjecting `Texture2D` assets into Unity serialized files (`assets/bin/Data/*` or standalone AssetBundles) using Python (`UnityPy`) and Pillow.

## When to Use
- Extracting game textures, backgrounds, UI sprites, and atlases from Unity APKs or data folders.
- Performing visual modifications (hue shifting, color correction, texture replacements, custom re-skins).
- Re-serializing modified textures back into Unity binary format while preserving asset hashes, mipmaps, and metadata.

## Prerequisites
- Isolated Python virtual environment (`uv venv` or standard `venv`).
- Required packages:
  ```bash
  pip install UnityPy Pillow
  ```

## Architecture: How Unity Stores Textures
In Unity games (e.g. mobile games built with Unity IL2CPP), textures are packed inside hash-named serialized files inside `assets/bin/Data/`:
- Each file can contain multiple Unity objects (`Texture2D`, `Sprite`, `TextAsset`, `MonoBehaviour`, `Transform`).
- Asset references are identified by object names (`data.m_Name`).
- Re-serializing an object in-place preserves Unity's internal pointer table (`SerializedFile`).

## Workflow

### 1. Identifying and Extracting Textures
Scan Unity data files to find target textures:

```python
import os
import UnityPy

def scan_textures(unity_dir: str):
    found = {}
    for fname in os.listdir(unity_dir):
        fpath = os.path.join(unity_dir, fname)
        if not os.path.isfile(fpath):
            continue
        try:
            env = UnityPy.load(fpath)
            for obj in env.objects:
                if obj.type.name == "Texture2D":
                    data = obj.read()
                    print(f"File: {fname} -> Texture: {data.m_Name} ({data.image.size})")
                    found[data.m_Name] = fname
        except Exception:
            continue
    return found
```

### 2. Modifying Textures (e.g., Hue Shifting or Replacement)
To apply a color shift (e.g. cyber-themed hue rotation) via HSV:

```python
import colorsys
from PIL import Image

def hue_shift_image(img: Image.Image, shift_degrees: float) -> Image.Image:
    """Rotates image hue while preserving transparency and brightness."""
    img = img.convert("RGBA")
    pixels = img.load()
    w, h = img.size
    out = Image.new("RGBA", (w, h))
    out_pixels = out.load()
    shift = shift_degrees / 360.0

    for y in range(h):
        for x in range(w):
            r, g, b, a = pixels[x, y]
            if a == 0:
                out_pixels[x, y] = (r, g, b, 0)
                continue
            h_val, s_val, v_val = colorsys.rgb_to_hsv(r / 255.0, g / 255.0, b / 255.0)
            h_val = (h_val + shift) % 1.0
            nr, ng, nb = colorsys.hsv_to_rgb(h_val, s_val, v_val)
            out_pixels[x, y] = (int(nr * 255), int(ng * 255), int(nb * 255), a)
    return out
```

### 3. Re-serializing and Injecting Back into Unity Assets
When saving back to Unity, mutate `data.image` and invoke `data.save()` followed by `env.file.save()`:

```python
def inject_texture(raw_bytes: bytes, target_name: str, replacement_image: Image.Image) -> bytes:
    env = UnityPy.load(raw_bytes)
    modified = False
    for obj in env.objects:
        if obj.type.name == "Texture2D":
            data = obj.read()
            if target_name.lower() in data.m_Name.lower():
                data.image = replacement_image
                data.save()
                modified = True
    if modified:
        return env.file.save()
    return raw_bytes
```

## Critical Guidelines & Pitfalls
1. **Never mutate uncompressed Unity files with raw byte search/replace**: Texture2D data is serialized with header lengths, format tags (e.g., ETC2, ASTC, DXT5, RGBA32), and mipmap counts. Always use `UnityPy` to re-encode.
2. **Handle Multi-resolution Atlases**: Unity games often provide high-res (`_high`) and low-res (`_low`) fallback variants of the same texture. Mod both versions so low-end render modes don't revert to original textures.
3. **Preserve Image Dimensions**: If replacing textures completely, match the exact width and height or power-of-two dimensions (e.g., 512x512, 1024x512) to avoid UV misalignment in 3D meshes and 2D atlases.

"""
Shadow Fight 2 Asset Modding Pipeline
Extracts Unity serialized textures from base APK, applies color/hue transformations,
replaces them in the Unity binary assets using UnityPy, merges native libraries,
and outputs both a modded XAPK and a standalone BlueStacks-ready APK.
"""

import colorsys
import os
import shutil
import subprocess
import zipfile

import UnityPy
from PIL import Image

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PACKAGES_DIR = os.path.join(ROOT_DIR, "modding", "packages")
TOOLS_DIR = os.path.join(ROOT_DIR, "modding", "tools")
ASSETS_DIR = os.path.join(ROOT_DIR, "modding", "assets")
BUILD_DIR = os.path.join(ROOT_DIR, "modding", "build_cache")
BLUESTACKS_APKS = os.path.join(ROOT_DIR, "bluestacks", "apks")

XAPK_INPUT = os.path.join(PACKAGES_DIR, "Shadow+Fight+2_2.46.0_APKPure.xapk")
XAPK_OUTPUT = os.path.join(PACKAGES_DIR, "Shadow_Fight_2_Modded_Cyberpunk.xapk")
STANDALONE_APK_OUTPUT = os.path.join(BLUESTACKS_APKS, "Shadow_Fight_2_MODDED_CYBERPUNK.apk")
UBER_SIGNER = os.path.join(TOOLS_DIR, "uber-apk-signer.jar")

# Mapping of Unity serialized files in com.nekki.shadowfight.apk to the Texture2D names
TARGET_ASSETS = {
    "assets/bin/Data/a270fac21f3177e428a9c49164a217c2": "dojo_bg",
    "assets/bin/Data/edba0f6b88dea6144baef9415426de20": "dojo_bg_low",
    "assets/bin/Data/78a8599a4223b28419c1b7417ca03a4d": "dojo_atlas_layer1",
    "assets/bin/Data/dd833943f1e94264e9b19dc78c3dd346": "dojo_atlas_layer2",
    "assets/bin/Data/ca5b9cfa51d2ed44cbbc5daf06b4589d": "dojo_atlas_layer2_low",
    "assets/bin/Data/835de2e8aa03eb5458bccaa42c4694c2": "dojo_atlas_layer3",
    "assets/bin/Data/a475dfa934fc5384ebc0f36e30bb7b30": "dojo_atlas_layer3_low",
}


def hue_shift(img: Image.Image, shift_deg: float) -> Image.Image:
    """Shifts the hue of an RGBA image by shift_deg (0-360)."""
    img = img.convert("RGBA")
    pixels = img.load()
    w, h = img.size
    out = Image.new("RGBA", (w, h))
    out_pixels = out.load()
    shift = shift_deg / 360.0
    for y in range(h):
        for x in range(w):
            pr, pg, pb, pa = pixels[x, y]
            if pa == 0:
                out_pixels[x, y] = (pr, pg, pb, 0)
                continue
            h_val, s_val, v_val = colorsys.rgb_to_hsv(pr / 255.0, pg / 255.0, pb / 255.0)
            h_val = (h_val + shift) % 1.0
            nr, ng, nb = colorsys.hsv_to_rgb(h_val, s_val, v_val)
            out_pixels[x, y] = (int(nr * 255), int(ng * 255), int(nb * 255), pa)
    return out


def apply_texture_mod(raw_bytes: bytes, target_texture_name: str, shift_deg: float = 180.0) -> bytes:
    """Loads a Unity serialized file, modifies matching Texture2D objects, and returns serialized bytes."""
    env = UnityPy.load(raw_bytes)
    modified = False
    for obj in env.objects:
        if obj.type.name == "Texture2D":
            data = obj.read()
            if target_texture_name.lower() in data.m_Name.lower():
                print(
                    f"  [Modifying Texture] {data.m_Name} ({data.m_Width}x{data.m_Height}) with hue shift {shift_deg}°..."
                )
                orig_img = data.image
                mod_img = hue_shift(orig_img, shift_deg)
                data.image = mod_img
                data.save()
                modified = True
    if modified:
        return env.file.save()
    return raw_bytes


def main():
    print("=== Step 1: Unpacking XAPK ===")
    work_dir = os.path.join(BUILD_DIR, "mod_work")
    if os.path.exists(work_dir):
        shutil.rmtree(work_dir)
    os.makedirs(work_dir, exist_ok=True)

    with zipfile.ZipFile(XAPK_INPUT, "r") as xapk:
        xapk.extractall(work_dir)
    print(f"Extracted XAPK to {work_dir}/")

    base_apk_path = os.path.join(work_dir, "com.nekki.shadowfight.apk")
    temp_apk_path = os.path.join(work_dir, "com.nekki.shadowfight.modded.apk")

    print("\n=== Step 2: Modifying Unity Assets inside Base APK ===")
    with (
        zipfile.ZipFile(base_apk_path, "r") as in_apk,
        zipfile.ZipFile(temp_apk_path, "w", compression=zipfile.ZIP_DEFLATED) as out_apk,
    ):
        for item in in_apk.infolist():
            content = in_apk.read(item.filename)
            matched_tex = None
            for asset_path, tex_name in TARGET_ASSETS.items():
                if item.filename == asset_path:
                    matched_tex = tex_name
                    break

            if matched_tex:
                print(f"Processing target asset: {item.filename} (Texture: {matched_tex})")
                content = apply_texture_mod(content, matched_tex, shift_deg=180.0)  # 180° = Cyan / Electric Blue

            out_apk.writestr(item, content)

    # 3. Read native libraries from config APKs for standalone build
    libs_to_add = {}
    for cfg in ["config.arm64_v8a.apk", "config.armeabi_v7a.apk"]:
        cfg_path = os.path.join(work_dir, cfg)
        with zipfile.ZipFile(cfg_path, "r") as z:
            for f in z.namelist():
                if f.startswith("lib/"):
                    libs_to_add[f] = z.read(f)

    # 4. Create standalone unaligned APK
    standalone_unaligned = os.path.join(work_dir, "modded_standalone_unaligned.apk")
    with (
        zipfile.ZipFile(temp_apk_path, "r") as mod_base,
        zipfile.ZipFile(standalone_unaligned, "w", compression=zipfile.ZIP_DEFLATED) as out_standalone,
    ):
        for item in mod_base.infolist():
            if item.filename.startswith("META-INF/") and (
                item.filename.endswith(".SF") or item.filename.endswith(".RSA") or item.filename.endswith(".MF")
            ):
                continue
            out_standalone.writestr(item, mod_base.read(item.filename))
        for lib_path, lib_bytes in libs_to_add.items():
            out_standalone.writestr(lib_path, lib_bytes)

    # 5. Sign standalone APK using uber-apk-signer
    signed_dir = os.path.join(work_dir, "signed")
    os.makedirs(signed_dir, exist_ok=True)
    subprocess.run(f'java -jar "{UBER_SIGNER}" -a "{standalone_unaligned}" -o "{signed_dir}" --allowResign', shell=True)

    # Copy to bluestacks/apks/
    os.makedirs(BLUESTACKS_APKS, exist_ok=True)
    shutil.copy(os.path.join(signed_dir, "modded_standalone_unaligned-aligned-debugSigned.apk"), STANDALONE_APK_OUTPUT)
    print(f"\nSUCCESS! Created standalone modded APK at:\n  -> {STANDALONE_APK_OUTPUT}")


if __name__ == "__main__":
    main()

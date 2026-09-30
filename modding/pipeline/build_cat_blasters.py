"""
Pipeline to build 'Cat Blasters 9k' modded standalone APK.
1. Rebrands app name to 'Cat Blasters 9k' in resources.
2. Injects custom cyberpunk cat icon across all mipmaps & adaptive icon drawables.
3. Updates package name to 'com.nekki.catblasters' to allow side-by-side installation with Shadow Fight 2.
4. Updates binary global-metadata.dat paths.
5. Injects custom Cyan/Sapphire Dojo Unity textures.
6. Builds, zip-aligns, and signs with Android v1/v2/v3 signatures.
"""

import os
import io
import shutil
import zipfile
import colorsys
import subprocess
from PIL import Image
import UnityPy

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CACHE_DIR = os.path.join(ROOT_DIR, "modding", "build_cache")
APKTOOL_SRC = os.path.join(CACHE_DIR, "apktool_src")
APKTOOL_JAR = os.path.join(ROOT_DIR, "modding", "tools", "apktool.jar")
UBER_SIGNER = os.path.join(ROOT_DIR, "modding", "tools", "uber-apk-signer.jar")
CAT_ICON_SRC = os.path.join(ROOT_DIR, "modding", "assets", "icons", "cat_blasters_icon_512.png")
OUTPUT_APK = os.path.join(ROOT_DIR, "bluestacks", "apks", "SF2_Modded_v4.apk")
ORIGINAL_APK = os.path.join(ROOT_DIR, "bluestacks", "apks", "SF2_OG.apk")

# Configuration: Number of rounds to win per match (default: 5)
# Can be changed here or passed via command line: --rounds <N>
ROUNDS_TO_WIN = 5

def arm64_movz(rd: int, imm16: int) -> bytes:
    """Encodes ARM64 32-bit MOVZ instruction: mov w{rd}, #{imm16}."""
    val = (0x52800000) | ((imm16 & 0xffff) << 5) | (rd & 0x1f)
    return val.to_bytes(4, 'little')

# Protection rule: SF2_Modded_v1.apk, SF2_Modded_v2.apk, and SF2_Modded_v3.apk must NEVER be overwritten!
PROTECTED_V1_APK = os.path.join(ROOT_DIR, "bluestacks", "apks", "SF2_Modded_v1.apk")
PROTECTED_V2_APK = os.path.join(ROOT_DIR, "bluestacks", "apks", "SF2_Modded_v2.apk")
PROTECTED_V3_APK = os.path.join(ROOT_DIR, "bluestacks", "apks", "SF2_Modded_v3.apk")
if os.path.abspath(OUTPUT_APK) in (os.path.abspath(PROTECTED_V1_APK), os.path.abspath(PROTECTED_V2_APK), os.path.abspath(PROTECTED_V3_APK)):
    raise ValueError("SF2_Modded_v1.apk, v2.apk, and v3.apk are protected historical milestones and must NEVER be overwritten. Target v4 or higher!")

# Mapping of Dojo Unity textures
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
    env = UnityPy.load(raw_bytes)
    modified = False
    for obj in env.objects:
        if obj.type.name == "Texture2D":
            data = obj.read()
            if target_texture_name.lower() in data.m_Name.lower():
                print(f"    [Modifying Texture] {data.m_Name} with hue shift {shift_deg}°...")
                data.image = hue_shift(data.image, shift_deg)
                data.save()
                modified = True
    if modified:
        return env.file.save()
    return raw_bytes

def main():
    import argparse
    parser = argparse.ArgumentParser(description="Build Cat Blasters standalone APK.")
    parser.add_argument("--rounds", type=int, default=ROUNDS_TO_WIN, help=f"Target rounds to win (default: {ROUNDS_TO_WIN})")
    parser.add_argument("--output", type=str, default=None, help="Custom output APK filename or path")
    args, _ = parser.parse_known_args()
    rounds = args.rounds
    output_apk = OUTPUT_APK
    if args.output:
        output_apk = os.path.abspath(args.output) if os.path.isabs(args.output) else os.path.join(ROOT_DIR, "bluestacks", "apks", args.output)
    if os.path.abspath(output_apk) in (os.path.abspath(PROTECTED_V1_APK), os.path.abspath(PROTECTED_V2_APK), os.path.abspath(PROTECTED_V3_APK)):
        raise ValueError("SF2_Modded_v1.apk, v2.apk, and v3.apk are protected historical milestones and must NEVER be overwritten. Target v4 or higher!")
    print(f"=== Configuring APK with ROUNDS_TO_WIN = {rounds} -> {os.path.basename(output_apk)} ===")

    print("=== Step 1: Decompiling original APK if needed ===")
    if not os.path.exists(APKTOOL_SRC):
        print(f"Decoding {ORIGINAL_APK} via apktool...")
        subprocess.run(f'java -jar "{APKTOOL_JAR}" d "{ORIGINAL_APK}" -o "{APKTOOL_SRC}" -s -f', shell=True, check=True)

    print("\n=== Step 2: Renaming App Label to 'Cat Blasters 9k' ===")
    strings_path = os.path.join(APKTOOL_SRC, "res", "values", "strings.xml")
    with open(strings_path, 'r', encoding='utf-8') as f:
        strings_content = f.read()

    strings_content = strings_content.replace(
        '<string name="app_name">Shadow Fight 2</string>',
        '<string name="app_name">Cat Blasters 9k</string>'
    )
    with open(strings_path, 'w', encoding='utf-8') as f:
        f.write(strings_content)
    print("  Updated res/values/strings.xml: app_name -> 'Cat Blasters 9k'")

    print("\n=== Step 3: Updating Package Name & Authorities ===")
    manifest_path = os.path.join(APKTOOL_SRC, "AndroidManifest.xml")
    with open(manifest_path, 'r', encoding='utf-8') as f:
        manifest_content = f.read()

    # Replace package name and all provider authorities
    manifest_content = manifest_content.replace('com.nekki.shadowfight', 'com.nekki.catblasters')
    with open(manifest_path, 'w', encoding='utf-8') as f:
        f.write(manifest_content)
    print("  Updated AndroidManifest.xml: package & authorities -> 'com.nekki.catblasters'")

    print("\n=== Step 4: Updating global-metadata.dat package paths ===")
    metadata_path = os.path.join(APKTOOL_SRC, "assets", "bin", "Data", "Managed", "Metadata", "global-metadata.dat")
    with open(metadata_path, 'rb') as f:
        meta_bytes = f.read()

    # 'com.nekki.shadowfight' and 'com.nekki.catblasters' are both exactly 21 bytes!
    meta_bytes = meta_bytes.replace(b'com.nekki.shadowfight', b'com.nekki.catblasters')
    with open(metadata_path, 'wb') as f:
        f.write(meta_bytes)
    print("  Updated global-metadata.dat binary strings (exact length match: 21 bytes)")

    print("\n=== Step 5: Replacing App Icons with Cat Blasters 9k Icon ===")
    cat_icon = Image.open(CAT_ICON_SRC)

    icon_sizes = {
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

    for folder, px in icon_sizes.items():
        folder_path = os.path.join(APKTOOL_SRC, folder)
        if os.path.exists(folder_path):
            resized = cat_icon.resize((px, px), Image.Resampling.LANCZOS)
            for fname in ["app_icon.png", "app_icon_round.png", "ic_launcher.png", "ic_launcher_foreground.png"]:
                fpath = os.path.join(folder_path, fname)
                if os.path.exists(fpath):
                    resized.save(fpath)
            
            # For ic_launcher_background, create a dark sleek neon background
            bg_path = os.path.join(folder_path, "ic_launcher_background.png")
            if os.path.exists(bg_path):
                bg_img = Image.new("RGBA", (px, px), (12, 16, 26, 255))
                bg_img.save(bg_path)

    print("  Replaced all launcher and mipmap icons with Cat Blasters 9k art!")

    print("\n=== Step 6: Injecting Cyan/Sapphire Dojo Unity Textures ===")
    for rel_path, tex_name in TARGET_ASSETS.items():
        full_asset_path = os.path.join(APKTOOL_SRC, rel_path.replace("/", os.sep))
        if os.path.exists(full_asset_path):
            with open(full_asset_path, 'rb') as f:
                raw = f.read()
            modded_bytes = apply_texture_mod(raw, tex_name, shift_deg=180.0)
            with open(full_asset_path, 'wb') as f:
                f.write(modded_bytes)
    print("  Injected custom Dojo textures into Unity serialized assets.")

    print("\n=== Step 6b: Embedding Offline Bundles & Injecting Self-Extractor ===")
    # 1. Copy downloaded gamedata to APK assets
    gamedata_src = os.path.join(ROOT_DIR, "modding", "assets", "downloaded_gamedata")
    gamedata_dst = os.path.join(APKTOOL_SRC, "assets", "gamedata")
    os.makedirs(gamedata_dst, exist_ok=True)
    for root, dirs, files in os.walk(gamedata_src):
        for f in files:
            src_f = os.path.join(root, f)
            rel_f = os.path.relpath(src_f, gamedata_src)
            dst_f = os.path.join(gamedata_dst, rel_f)
            os.makedirs(os.path.dirname(dst_f), exist_ok=True)
            shutil.copy2(src_f, dst_f)
    print("  Copied offline bundles and configs to APK assets/gamedata/.")

    # 1b. Copy userdata profile to APK assets
    userdata_src = os.path.join(ROOT_DIR, "modding", "assets", "userdata")
    userdata_dst = os.path.join(APKTOOL_SRC, "assets", "userdata")
    if os.path.exists(userdata_src):
        os.makedirs(userdata_dst, exist_ok=True)
        for root, dirs, files in os.walk(userdata_src):
            for f in files:
                src_f = os.path.join(root, f)
                rel_f = os.path.relpath(src_f, userdata_src)
                dst_f = os.path.join(userdata_dst, rel_f)
                os.makedirs(os.path.dirname(dst_f), exist_ok=True)
                shutil.copy2(src_f, dst_f)
        print("  Copied pre-configured tutorial-skip user profile to APK assets/userdata/.")

    # 1c. Patch libil2cpp.so to bypass XML hash validation, data corruption checks, and Google Play warning
    so_patches = {
        0x3598568: ("XML hash bypass (AMELFFLEPNF)", bytes.fromhex("20008052c0035fd6")), # mov w0, #1; ret
        0x3594984: ("XML hash bypass direct (AMELFFLEPNF)", bytes.fromhex("20008052c0035fd6")), # mov w0, #1; ret
        0x35951b4: ("XML hash check bypass (FNIHLBLMOBP)", bytes.fromhex("20008052c0035fd6")), # mov w0, #1; ret
        0x3595870: ("XML hash check bypass (PBACHEOJBGG)", bytes.fromhex("20008052c0035fd6")), # mov w0, #1; ret
        0x3595e1c: ("XML hash check bypass (PKACMGFBIKK)", bytes.fromhex("20008052c0035fd6")), # mov w0, #1; ret
        0x30c3344: ("Data corruption check bypass (EOJDBAHODGK)", bytes.fromhex("20008052c0035fd6")), # mov w0, #1; ret
        0x30c1250: ("Disable HackTitle dialog (MACGEGDGBOI)", bytes.fromhex("c0035fd61f2003d5")), # ret; nop
        0x30c11d8: ("Bypass hack detector (HBGCPAEJCJJ)", bytes.fromhex("00008052c0035fd6")), # mov w0, #0; ret
        0x34377f4: ("Disable Google Play warning dialog (NKLGCNHLBAF)", bytes.fromhex("21008052e2031faafea90114")), # mov w1, #1; mov x2, xzr; b 0x34a5ff4
        0x3437afc: ("Disable Google Play check (JFGBPBOCOIC)", bytes.fromhex("00008052c0035fd6")), # mov w0, #0; ret
        0x32d9388: ("Bypass ShowGDPR dialog (LJBDMDHNKFM.JFGBPBOCOIC)", bytes.fromhex("00008052c0035fd6")), # mov w0, #0; ret
        0x325bd24: ("Disable CheckPacksNeeded (AAPGCAPGBLG.MCFHOHANNDH)", bytes.fromhex("00008052c0035fd6")), # mov w0, #0; ret
        0x2ff0a10: ("Hook for default Map scene redirect", bytes.fromhex("290d40b93f0d0071aa0080524991891a0f030014")), # ldr w9; cmp w9, #3; mov w10, #5; csel w9, w10, w9, ls; b 0x2ff165c
        0x2ff1658: ("Redirect scene load to Map hook", bytes.fromhex("eefcff17")), # b 0x2ff0a10
        0x1cc5b44: ("Restore raid energy check (IEICNBBBNEJ.EHLKEFJNKPA)", bytes.fromhex("fe0f1ef8f44f01a9")),
        0x3414c4c: ("Restore CIHKNMDAPBG instruction", bytes.fromhex("f44f44a9")),
        0x296bd44: ("Restore Scene<object>.Update ret", bytes.fromhex("c0035fd6")),
        0x3580ca4: ("Restore MapScene.PIMIMOACBNG instruction", bytes.fromhex("f50300aa")), # mov x21, x21
        0x30c1258: ("Restore MACGEGDGBOI body", bytes.fromhex("fc6f05a9fa6706a9f85f07a9f65708a9f44f09a91d9d00b017820090938300b0948300b09c8300b0")),
        0x3063e1c: ("Unlimited energy getter bypass (ACHLOMELAJE.PDKBJDBJOOK)", bytes.fromhex("20008052c0035fd6")), # mov w0, #1; ret
        0x344aec8: ("Force VIP Unlimited Energy icon on MenuEnergyPanel UI", bytes.fromhex("34008052")), # mov w20, #1
        0x305aaa4: ("Force field 0x238 (IsUnlimitedEnergy) in ACHLOMELAJE.MEBIEMOMELE", bytes.fromhex("28008052")), # mov w8, #1
        0x3057bfc: ("Always allow energy spend (ACHLOMELAJE.AIIJFJLLIDB)", bytes.fromhex("20008052c0035fd6")), # mov w0, #1; ret
        0x3057964: ("Always return 5 energy (ACHLOMELAJE.FMNEFEMHCGG)", bytes.fromhex("a0008052c0035fd6")), # mov w0, #5; ret
        0x33e7d80: (f"Set match round victory target to {rounds} (FCJBEKHDLAF.DHKCOFBMIEL)", arm64_movz(22, rounds)), # mov w22, #rounds
        0x33e9444: (f"Set EndRound victory threshold to {rounds} (FCJBEKHDLAF.AIFOMGABBBA)", arm64_movz(8, rounds)), # mov w8, #rounds
        0x33ea8e4: (f"Set RoundModel target rounds to {rounds} (FCJBEKHDLAF.LPIEJMLPFBF)", arm64_movz(1, rounds)), # mov w1, #rounds
        0x33ef960: ("Standard round winner branch (FCJBEKHDLAF.BBCAMJDDOII)", bytes.fromhex("48020054")), # b.hi 0x33ef9a8
    }
    for lib_so in [
        os.path.join(APKTOOL_SRC, "lib", "arm64-v8a", "libil2cpp.so"),
        os.path.join(APKTOOL_SRC, "build", "apk", "lib", "arm64-v8a", "libil2cpp.so"),
    ]:
        if os.path.exists(lib_so):
            with open(lib_so, "r+b") as f:
                for offset, (desc, patch_bytes) in so_patches.items():
                    f.seek(offset)
                    f.write(patch_bytes)
                    print(f"  Patched {desc} at {hex(offset)} in {os.path.basename(lib_so)}.")

    # 1d. Replace intro.mp4 with 0.04s instant-skip dummy video
    dummy_intro_src = os.path.join(ROOT_DIR, "modding", "assets", "dummy_intro.mp4")
    intro_dst = os.path.join(APKTOOL_SRC, "assets", "database", "intro.mp4")
    if os.path.exists(dummy_intro_src):
        shutil.copy2(dummy_intro_src, intro_dst)
        print("  Replaced intro.mp4 with 0.04s instant-skip dummy video.")

    # 2. Reassemble classes.dex with AssetExtractor if smali source exists
    baksmali_dir = os.path.join(CACHE_DIR, "baksmali_multidex")
    smali_jar = os.path.join(ROOT_DIR, "modding", "tools", "smali.jar")
    if os.path.exists(baksmali_dir) and os.path.exists(smali_jar):
        classes_dex_out = os.path.join(APKTOOL_SRC, "classes.dex")
        cmd_smali = f'java -jar "{smali_jar}" a "{baksmali_dir}" -o "{classes_dex_out}"'
        subprocess.run(cmd_smali, shell=True, check=True)
        print("  Reassembled classes.dex with AssetExtractor startup hook.")

    print("\n=== Step 7: Rebuilding APK via Apktool ===")
    apktool_build_dir = os.path.join(APKTOOL_SRC, "build")
    if os.path.exists(apktool_build_dir):
        shutil.rmtree(apktool_build_dir)
    rebuilt_apk = os.path.join(CACHE_DIR, "cat_blasters_unsigned.apk")
    cmd_build = f'java -jar "{APKTOOL_JAR}" b "{APKTOOL_SRC}" -o "{rebuilt_apk}" -f'
    subprocess.run(cmd_build, shell=True, check=True)
    print(f"  Rebuilt APK created: {rebuilt_apk}")

    print("\n=== Step 8: Zipaligning & Signing ===")
    signed_dir = os.path.join(CACHE_DIR, "cat_signed")
    if os.path.exists(signed_dir):
        shutil.rmtree(signed_dir)
    os.makedirs(signed_dir, exist_ok=True)

    cmd_sign = f'java -jar "{UBER_SIGNER}" -a "{rebuilt_apk}" -o "{signed_dir}" --allowResign'
    res = subprocess.run(cmd_sign, shell=True, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print("Stderr:", res.stderr)

    # Copy final signed APK
    shutil.copy(
        os.path.join(signed_dir, "cat_blasters_unsigned-aligned-debugSigned.apk"),
        output_apk
    )
    print(f"\n========================================================")
    print(f"SUCCESS! Cat Blasters 9k Standalone APK generated at:")
    print(f"  -> {output_apk} ({os.path.getsize(output_apk)/(1024*1024):.2f} MB)")
    print(f"========================================================")

if __name__ == "__main__":
    main()

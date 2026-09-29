"""
Builds standalone, monolithic universal APKs from split APK packages.
Merges architecture native libraries (arm64-v8a, armeabi-v7a) directly into the base APK,
then zip-aligns and signs them using uber-apk-signer (supporting Android v1, v2, v3 signature schemes).
"""

import os
import io
import zipfile
import subprocess
import shutil

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PACKAGES_DIR = os.path.join(ROOT_DIR, "modding", "packages")
TOOLS_DIR = os.path.join(ROOT_DIR, "modding", "tools")
OUTPUT_DIR = os.path.join(ROOT_DIR, "bluestacks", "apks")
CACHE_DIR = os.path.join(ROOT_DIR, "modding", "build_cache")

XAPK_INPUT = os.path.join(PACKAGES_DIR, "Shadow+Fight+2_2.46.0_APKPure.xapk")
UBER_SIGNER = os.path.join(TOOLS_DIR, "uber-apk-signer.jar")
KEYSTORE = os.path.join(TOOLS_DIR, "debug.keystore")

def merge_and_build(base_apk_bytes, arm64_apk_bytes, arm32_apk_bytes, output_unsigned_apk):
    print(f"Merging split APKs into {output_unsigned_apk}...")
    
    libs_to_add = {}
    with zipfile.ZipFile(io.BytesIO(arm64_apk_bytes), 'r') as z64:
        for f in z64.namelist():
            if f.startswith('lib/'):
                libs_to_add[f] = z64.read(f)
                
    with zipfile.ZipFile(io.BytesIO(arm32_apk_bytes), 'r') as z32:
        for f in z32.namelist():
            if f.startswith('lib/'):
                libs_to_add[f] = z32.read(f)

    print(f"  Collected {len(libs_to_add)} native architecture libraries.")

    with zipfile.ZipFile(io.BytesIO(base_apk_bytes), 'r') as base_z, \
         zipfile.ZipFile(output_unsigned_apk, 'w', compression=zipfile.ZIP_DEFLATED) as out_z:
        
        for item in base_z.infolist():
            # Exclude old signatures
            if item.filename.startswith('META-INF/') and (item.filename.endswith('.SF') or item.filename.endswith('.RSA') or item.filename.endswith('.MF')):
                continue
            out_z.writestr(item, base_z.read(item.filename))
        
        for lib_path, lib_bytes in libs_to_add.items():
            out_z.writestr(lib_path, lib_bytes)
            
    print(f"  Merged unaligned APK created: {output_unsigned_apk}")

def main():
    os.makedirs(CACHE_DIR, exist_ok=True)
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    print(f"Reading input packages from: {XAPK_INPUT}")
    with zipfile.ZipFile(XAPK_INPUT, 'r') as z:
        orig_base_bytes = z.read("com.nekki.shadowfight.apk")
        arm64_bytes = z.read("config.arm64_v8a.apk")
        arm32_bytes = z.read("config.armeabi_v7a.apk")

    # 1. Build Original Standalone APK
    orig_unsigned = os.path.join(CACHE_DIR, "original_unsigned.apk")
    merge_and_build(orig_base_bytes, arm64_bytes, arm32_bytes, orig_unsigned)

    # 2. Sign with uber-apk-signer
    signed_dir = os.path.join(CACHE_DIR, "signed")
    os.makedirs(signed_dir, exist_ok=True)

    print(f"\nSigning standalone APKs using {UBER_SIGNER}...")
    cmd = f'java -jar "{UBER_SIGNER}" -a "{CACHE_DIR}" -o "{signed_dir}" --allowResign'
    res = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print("Stderr:", res.stderr)

    # 3. Copy to destination
    dest_path = os.path.join(OUTPUT_DIR, "SF2_OG.apk")
    shutil.copy(
        os.path.join(signed_dir, "original_unsigned-aligned-debugSigned.apk"),
        dest_path
    )
    print(f"\nSUCCESS! Standalone APK created at:\n  -> {dest_path} ({os.path.getsize(dest_path) / (1024*1024):.2f} MB)")

if __name__ == "__main__":
    main()

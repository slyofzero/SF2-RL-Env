"""
Builder for SF2_Modded_v3.apk (Infinite Energy on top of v2 baseline).
Extracts libil2cpp.so from SF2_Modded_v2.apk, applies the 5 infinite energy patches,
repackages the APK, and signs with uber-apk-signer (v1, v2, v3 schemes).
Leaves SF2_Modded_v1.apk and SF2_Modded_v2.apk completely untouched.
"""

import os
import shutil
import subprocess
import zipfile

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
V2_APK = os.path.join(ROOT_DIR, "bluestacks", "apks", "SF2_Modded_v2.apk")
OUTPUT_APK = os.path.join(ROOT_DIR, "bluestacks", "apks", "SF2_Modded_v3.apk")
UBER_SIGNER = os.path.join(ROOT_DIR, "modding", "tools", "uber-apk-signer.jar")
CACHE_DIR = os.path.join(ROOT_DIR, "modding", "build_cache")

# Immutable protection check
PROTECTED_V1_APK = os.path.join(ROOT_DIR, "bluestacks", "apks", "SF2_Modded_v1.apk")
PROTECTED_V2_APK = os.path.join(ROOT_DIR, "bluestacks", "apks", "SF2_Modded_v2.apk")
if os.path.abspath(OUTPUT_APK) in (os.path.abspath(PROTECTED_V1_APK), os.path.abspath(PROTECTED_V2_APK)):
    raise ValueError(
        "SF2_Modded_v1.apk and SF2_Modded_v2.apk are protected historical milestones and must NEVER be overwritten."
    )

ENERGY_PATCHES = {
    # 1. PDKBJDBJOOK: IsUnlimitedEnergy property getter -> return true (mov w0, #1; ret)
    0x3063E1C: (
        "PDKBJDBJOOK (IsUnlimitedEnergy getter)",
        bytes.fromhex("00e04839c0035fd6"),
        bytes.fromhex("20008052c0035fd6"),
    ),
    # 2. MenuEnergyPanel.UpdateView: Force unlimited VIP energy icon (mov w20, #1)
    0x344AEC8: ("MenuEnergyPanel UI VIP icon", bytes.fromhex("14e14839"), bytes.fromhex("34008052")),
    # 3. ACHLOMELAJE.MEBIEMOMELE: Force field 0x238 (IsUnlimitedEnergy) (mov w8, #1)
    0x305AAA4: ("ACHLOMELAJE field 0x238", bytes.fromhex("28000012"), bytes.fromhex("28008052")),
    # 4. ACHLOMELAJE.AIIJFJLLIDB: SpendEnergy check -> return true (mov w0, #1; ret)
    0x3057BFC: (
        "AIIJFJLLIDB (SpendEnergy check)",
        bytes.fromhex("fe0f1ef8f44f01a9"),
        bytes.fromhex("20008052c0035fd6"),
    ),
    # 5. ACHLOMELAJE.FMNEFEMHCGG: get_Energy count -> return 5 (mov w0, #5; ret)
    0x3057964: ("FMNEFEMHCGG (get_Energy count)", bytes.fromhex("080841f9010c41f9"), bytes.fromhex("a0008052c0035fd6")),
}


def main():
    print(f"=== Building SF2_Modded_v3.apk from baseline: {os.path.basename(V2_APK)} ===")
    assert os.path.exists(V2_APK), f"Baseline APK not found: {V2_APK}"

    # 1. Read v2 APK
    print("Step 1: Reading baseline v2 APK and extracting libil2cpp.so...")
    with zipfile.ZipFile(V2_APK, "r") as z_in:
        so_data = bytearray(z_in.read("lib/arm64-v8a/libil2cpp.so"))

        # Verify and apply patches
        print("Step 2: Applying 5 Infinite Energy patches to lib/arm64-v8a/libil2cpp.so...")
        for offset, (desc, expected_orig, patch_bytes) in ENERGY_PATCHES.items():
            actual_orig = bytes(so_data[offset : offset + len(expected_orig)])
            if actual_orig != expected_orig:
                print(
                    f"  [Warning] Offset {hex(offset)} ({desc}) had {actual_orig.hex()}, expected {expected_orig.hex()}"
                )
            so_data[offset : offset + len(patch_bytes)] = patch_bytes
            print(f"  [Patched] {desc} at {hex(offset)} -> {patch_bytes.hex()}")

        # 3. Create unsigned APK with all files from v2, updated so, and no META-INF
        os.makedirs(CACHE_DIR, exist_ok=True)
        unsigned_apk = os.path.join(CACHE_DIR, "v3_unsigned.apk")
        print(f"Step 3: Repackaging APK to {unsigned_apk}...")

        with zipfile.ZipFile(unsigned_apk, "w", compression=zipfile.ZIP_DEFLATED) as z_out:
            for item in z_in.infolist():
                # Skip old signatures
                if item.filename.startswith("META-INF/"):
                    continue
                # Replace libil2cpp.so
                if item.filename == "lib/arm64-v8a/libil2cpp.so":
                    z_out.writestr(item, bytes(so_data))
                else:
                    data = z_in.read(item.filename)
                    z_out.writestr(item, data)

    # Also sync clean libil2cpp.so to apktool_src for future maintenance
    apktool_so = os.path.join(ROOT_DIR, "modding", "build_cache", "apktool_src", "lib", "arm64-v8a", "libil2cpp.so")
    if os.path.exists(os.path.dirname(apktool_so)):
        with open(apktool_so, "wb") as f:
            f.write(bytes(so_data))
        print("  Synchronized patched libil2cpp.so to build_cache/apktool_src.")

    # 4. Zipalign and sign with uber-apk-signer
    print("Step 4: Aligning and signing with uber-apk-signer...")
    signed_dir = os.path.join(CACHE_DIR, "v3_signed")
    if os.path.exists(signed_dir):
        shutil.rmtree(signed_dir)
    os.makedirs(signed_dir, exist_ok=True)

    cmd_sign = f'java -jar "{UBER_SIGNER}" -a "{unsigned_apk}" -o "{signed_dir}" --allowResign'
    res = subprocess.run(cmd_sign, shell=True, capture_output=True, text=True)
    print(res.stdout)
    if res.stderr:
        print("Stderr:", res.stderr)

    # 5. Copy to final output APK
    signed_files = [f for f in os.listdir(signed_dir) if f.endswith(".apk")]
    assert len(signed_files) > 0, f"Signing failed, no output APK in {signed_dir}"

    final_signed_apk = os.path.join(signed_dir, signed_files[0])
    shutil.copy2(final_signed_apk, OUTPUT_APK)

    size_mb = os.path.getsize(OUTPUT_APK) / (1024 * 1024)
    print("\n========================================================")
    print("SUCCESS! SF2_Modded_v3.apk generated at:")
    print(f"  -> {OUTPUT_APK} ({size_mb:.2f} MB)")
    print("========================================================")


if __name__ == "__main__":
    main()

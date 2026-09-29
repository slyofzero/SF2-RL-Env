---
name: apk-split-merger
description: Convert Android split APKs and XAPK packages into universal, monolithic standalone APKs with v1, v2, and v3 signatures. Use whenever dealing with .xapk packages, split config packages (lib/arm64-v8a, lib/armeabi-v7a), or fixing "Unsupported file type" and split installation errors on Android emulators like BlueStacks.
---

# Split APK & XAPK Standalone Merger

This skill provides a complete workflow for unpackaging split APK bundles (e.g. from APKPure `.xapk` files or Google Play App Bundles) and merging their architecture-specific native libraries into a single, monolithic, installable standalone APK.

## When to Use
- Dragging an `.xapk` into BlueStacks or an emulator results in "Unsupported file type".
- Attempting to install split APKs individually fails with `INSTALL_FAILED_MISSING_SPLIT`.
- Creating a self-contained APK containing all native architectures (`arm64-v8a`, `armeabi-v7a`, `x86_64`) for reproducible offline installation.

## Prerequisites
- Java Runtime Environment (JRE/JDK 11+ or 17+ or 22+).
- Tools required:
  - `uber-apk-signer.jar` (or `apksigner` + `zipalign`).
  - Python standard library (`zipfile`, `shutil`, `tempfile`).

## Why Split APKs Fail on Emulators
Modern Android distributions use Android App Bundles (AAB). When exported to `.xapk`, the archive contains:
- `com.example.app.apk` (Base APK: contains manifest, dex bytecode, resources, but **zero native `.so` libraries**).
- `config.arm64_v8a.apk` (Split APK: contains only `lib/arm64-v8a/*.so`).
- `config.armeabi_v7a.apk` (Split APK: contains only `lib/armeabi-v7a/*.so`).
- `manifest.json`.

Android's default package installer cannot install split APKs individually, and emulators reject `.xapk` as an unhandled archive format.

## Merger Workflow

### 1. Extract and Merge via Python
The merger script unpacks the base APK, extracts all native libraries from the split config APKs, merges them into `lib/<abi>/` in the base APK directory, and zips it back up.

```python
import os
import shutil
import zipfile
import tempfile
import subprocess

def merge_xapk_to_monolithic(xapk_path: str, output_apk: str, signer_jar: str):
    work_dir = tempfile.mkdtemp(prefix="apk_merge_")
    try:
        # 1. Extract XAPK archive
        print(f"Extracting XAPK: {xapk_path}")
        with zipfile.ZipFile(xapk_path, "r") as z:
            z.extractall(work_dir)

        # 2. Locate base APK and config APKs
        apk_files = [f for f in os.listdir(work_dir) if f.endswith(".apk")]
        base_apk = None
        config_apks = []
        for apk in apk_files:
            if "config." in apk:
                config_apks.append(os.path.join(work_dir, apk))
            else:
                base_apk = os.path.join(work_dir, apk)

        if not base_apk:
            raise FileNotFoundError("Base APK not found in XAPK bundle.")

        base_unpacked = os.path.join(work_dir, "base_unpacked")
        with zipfile.ZipFile(base_apk, "r") as z:
            z.extractall(base_unpacked)

        # 3. Extract native libs from config APKs into base_unpacked/lib/
        for cfg in config_apks:
            with zipfile.ZipFile(cfg, "r") as z:
                for entry in z.namelist():
                    if entry.startswith("lib/"):
                        z.extract(entry, base_unpacked)

        # 4. Remove existing signature block (META-INF/*.RSA, *.SF, *.MF)
        meta_inf = os.path.join(base_unpacked, "META-INF")
        if os.path.exists(meta_inf):
            shutil.rmtree(meta_inf)

        # 5. Repack unaligned APK
        unaligned_apk = os.path.join(work_dir, "merged_unaligned.apk")
        with zipfile.ZipFile(unaligned_apk, "w", zipfile.ZIP_DEFLATED) as z_out:
            for root, dirs, files in os.walk(base_unpacked):
                for f in files:
                    src_f = os.path.join(root, f)
                    rel_f = os.path.relpath(src_f, base_unpacked)
                    z_out.write(src_f, rel_f)

        # 6. Zipalign and sign with uber-apk-signer
        sign_out_dir = os.path.join(work_dir, "signed")
        os.makedirs(sign_out_dir, exist_ok=True)
        cmd = f'java -jar "{signer_jar}" -a "{unaligned_apk}" -o "{sign_out_dir}" --allowResign'
        subprocess.run(cmd, shell=True, check=True)

        signed_apk = [os.path.join(sign_out_dir, f) for f in os.listdir(sign_out_dir) if f.endswith(".apk")][0]
        os.makedirs(os.path.dirname(os.path.abspath(output_apk)), exist_ok=True)
        shutil.copy2(signed_apk, output_apk)
        print(f"Monolithic APK successfully created: {output_apk}")

    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
```

## Critical Signing Guidelines
- **Avoid conflicting flags in `uber-apk-signer`**: Do **not** pass both `-o <dir>` and `--overwrite` simultaneously; `uber-apk-signer` will fail immediately.
- **Ensure 4-byte Zip Alignment**: Always zipalign uncompressed resources before signing so Android's `mmap` can read shared libraries directly from memory.
- **Signature Schemes**: Generate both v1 (JAR signature) and v2/v3 (APK Signing Block) signatures so the APK is accepted on Android 7 through 14+.

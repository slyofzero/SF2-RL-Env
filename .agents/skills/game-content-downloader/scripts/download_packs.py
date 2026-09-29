"""
Universal Content & Pack Downloader for Shadow Fight 2
1. Parses config_cdn.xml to discover CDN URLs, sizes, and MD5 hashes for all game asset bundles.
2. Downloads any specified bundle names or categories in parallel.
3. Verifies downloaded file integrity using MD5 hashes.
4. Generates an updated packs.xml and synchronized packs.xml.hash companion file.
"""

import os
import sys
import hashlib
import argparse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", ".."))
DEFAULT_CONFIG_CDN = os.path.join(ROOT_DIR, "modding", "assets", "downloaded_gamedata", "config_cdn.xml")
DEFAULT_BUNDLES_DIR = os.path.join(ROOT_DIR, "modding", "assets", "downloaded_gamedata", "bundles")
DEFAULT_PACKS_XML = os.path.join(ROOT_DIR, "modding", "assets", "downloaded_gamedata", "packs.xml")
DEFAULT_PACKS_HASH = os.path.join(ROOT_DIR, "modding", "assets", "downloaded_gamedata", "packs.xml.hash")

def discover_available_packs(config_cdn_path: str):
    """Parses config_cdn.xml and returns a dictionary of all available Android bundles."""
    if not os.path.exists(config_cdn_path):
        raise FileNotFoundError(f"config_cdn.xml not found at: {config_cdn_path}")

    tree = ET.parse(config_cdn_path)
    root = tree.getroot()
    packs = {}
    for item in root.findall(".//item"):
        url = item.attrib.get("Url", "")
        if "unity_packs" in url and "android" in url:
            name = item.attrib.get("Name", "")
            if name:
                packs[name] = {
                    "Name": name,
                    "Url": url,
                    "Size": int(item.attrib.get("Size", "0")),
                    "Hash": item.attrib.get("Hash", ""),
                    "MinVersion": item.attrib.get("MinVersion", "2.46.0"),
                }
    return packs

def download_single_pack(name: str, info: dict, bundles_dir: str):
    """Downloads an individual pack bundle and verifies integrity."""
    dst = os.path.join(bundles_dir, name.replace("/", os.sep))
    os.makedirs(os.path.dirname(dst), exist_ok=True)

    expected_size = info.get("Size", 0)
    if os.path.exists(dst) and expected_size > 0 and os.path.getsize(dst) == expected_size:
        print(f"  [Cached] {name} ({os.path.getsize(dst):,} bytes)")
        return name, dst, True

    print(f"  [Downloading] {name} ({expected_size / (1024*1024):.2f} MB)...")
    req = urllib.request.Request(
        info["Url"],
        headers={"User-Agent": "UnityPlayer/2021.3.33f1 (UnityWebRequest/1.0, libcurl/7.84.0-DEV)"}
    )
    with urllib.request.urlopen(req) as resp, open(dst, "wb") as out:
        out.write(resp.read())

    # Verify MD5
    with open(dst, "rb") as f:
        actual_hash = hashlib.md5(f.read()).hexdigest().upper()

    expected_hash = info.get("Hash", "").upper()
    if expected_hash and actual_hash != expected_hash:
        print(f"  [WARNING] Hash mismatch for {name}: expected {expected_hash}, got {actual_hash}")
    else:
        print(f"  [Verified] {name} -> MD5: {actual_hash}")

    return name, dst, True

def update_packs_catalog(packs_dict: dict, bundles_dir: str, output_xml: str, output_hash: str):
    """Generates an updated packs.xml catalog and computes its cryptographic MD5 companion."""
    root_packs = ET.Element("Packs")

    for name in sorted(packs_dict.keys()):
        info = packs_dict[name]
        bundle_path = os.path.join(bundles_dir, name.replace("/", os.sep))
        file_hash = info.get("Hash", "")
        if os.path.exists(bundle_path):
            with open(bundle_path, "rb") as bf:
                file_hash = hashlib.md5(bf.read()).hexdigest().upper()

        ET.SubElement(root_packs, "Pack", {
            "Name": name,
            "Url": info["Url"],
            "Version": info.get("MinVersion", "2.46.0"),
            "Attach": "1",
            "Hash": file_hash,
            "Priority": "0"
        })

    tree_out = ET.ElementTree(root_packs)
    ET.indent(tree_out, space="  ")
    os.makedirs(os.path.dirname(output_xml), exist_ok=True)
    tree_out.write(output_xml, encoding="utf-8", xml_declaration=False)

    with open(output_xml, "rb") as f:
        md5_val = hashlib.md5(f.read()).hexdigest().upper()

    with open(output_hash, "w", encoding="utf-8") as f:
        f.write(md5_val)

    print(f"Updated {output_xml} ({len(root_packs)} packs registered)")
    print(f"Synchronized {output_hash} -> {md5_val}")

def main():
    parser = argparse.ArgumentParser(description="Download game asset bundles from config_cdn.xml")
    parser.add_argument("--names", nargs="*", help="Specific pack names to download (e.g. ZONE_1 EVENTS/MA_FEST_26)")
    parser.add_argument("--all", action="store_true", help="Download all available packs found in config_cdn.xml")
    parser.add_argument("--pattern", help="Download packs matching a substring pattern (e.g. 'ZONE', 'OFFERS', 'EVENT')")
    parser.add_argument("--config", default=DEFAULT_CONFIG_CDN, help="Path to config_cdn.xml")
    parser.add_argument("--outdir", default=DEFAULT_BUNDLES_DIR, help="Destination directory for bundles")
    args = parser.parse_args()

    available = discover_available_packs(args.config)
    print(f"Discovered {len(available)} available Android bundles in {args.config}")

    targets = {}
    if args.all:
        targets = available
    elif args.pattern:
        targets = {k: v for k, v in available.items() if args.pattern.lower() in k.lower()}
    elif args.names:
        for n in args.names:
            if n in available:
                targets[n] = available[n]
            else:
                print(f"[Warning] Pack '{n}' not found in catalog.")
    else:
        # Default: print catalog summary
        print("\nAvailable bundles by category:")
        categories = {}
        for k in available:
            cat = k.split("/")[0] if "/" in k else "CORE"
            categories.setdefault(cat, []).append(k)
        for cat, items in sorted(categories.items()):
            print(f"  [{cat}] ({len(items)} packs): {', '.join(items[:5])}{'...' if len(items) > 5 else ''}")
        print("\nUse --all, --names <names...>, or --pattern <pattern> to download.")
        return

    print(f"\nQueueing {len(targets)} bundles for download...")
    with ThreadPoolExecutor(max_workers=6) as executor:
        futures = [executor.submit(download_single_pack, k, v, args.outdir) for k, v in targets.items()]
        for f in futures:
            f.result()

    update_packs_catalog(available, args.outdir, DEFAULT_PACKS_XML, DEFAULT_PACKS_HASH)

if __name__ == "__main__":
    main()

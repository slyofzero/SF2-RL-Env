import xml.etree.ElementTree as ET
import os, urllib.request, hashlib
from concurrent.futures import ThreadPoolExecutor

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CONFIG_CDN = os.path.join(ROOT_DIR, "modding", "assets", "downloaded_gamedata", "config_cdn.xml")
BUNDLES_DIR = os.path.join(ROOT_DIR, "modding", "assets", "downloaded_gamedata", "bundles")
PACKS_XML = os.path.join(ROOT_DIR, "modding", "assets", "downloaded_gamedata", "packs.xml")
PACKS_HASH = os.path.join(ROOT_DIR, "modding", "assets", "downloaded_gamedata", "packs.xml.hash")

os.makedirs(BUNDLES_DIR, exist_ok=True)

# Target story zones and core packs
TARGET_PACK_NAMES = [
    "ANIMATIONS",
    "VERSIONAL_CONFIGS",
    "VERSIONAL_ASSETS",
    "ZONE_1",
    "ZONE_2",
    "ZONE_3",
    "ZONE_4",
    "ZONE_5",
    "ZONE_6",
    "ZONE_7",
    "ZONE_7_2",
    "ZONE_7_3",
    "ZONE_IM",
]

tree = ET.parse(CONFIG_CDN)
root = tree.getroot()

# Find latest Android packs for each target
latest_packs = {}
for item in root.findall('.//item'):
    url = item.attrib.get('Url', '')
    if 'unity_packs' in url and 'android' in url:
        name = item.attrib.get('Name', '')
        if name in TARGET_PACK_NAMES:
            latest_packs[name] = {
                'Name': name,
                'Url': url,
                'Size': int(item.attrib.get('Size', '0')),
                'Hash': item.attrib.get('Hash', ''),
                'Version': item.attrib.get('MinVersion', '2.46.0'),
            }

print(f"Found {len(latest_packs)} latest target packs in config_cdn.xml:")
for name, p in sorted(latest_packs.items()):
    print(f"  {name:20}: {p['Size'] / (1024*1024):.2f} MB -> {p['Url']}")

def download_pack(name, info):
    dst = os.path.join(BUNDLES_DIR, name.replace('/', '_'))
    if os.path.exists(dst) and os.path.getsize(dst) == info['Size']:
        print(f"  [Cached] {name} ({os.path.getsize(dst)} bytes)")
        return name, dst, info
    
    print(f"  [Downloading] {name} from {info['Url']}...")
    req = urllib.request.Request(info['Url'], headers={'User-Agent': 'UnityPlayer/2021.3.33f1'})
    with urllib.request.urlopen(req) as resp, open(dst, 'wb') as out:
        out.write(resp.read())
    print(f"  [Done] {name} ({os.path.getsize(dst)} bytes)")
    return name, dst, info

with ThreadPoolExecutor(max_workers=6) as executor:
    futures = [executor.submit(download_pack, k, v) for k, v in latest_packs.items()]
    for f in futures:
        f.result()

# Now generate updated packs.xml with all downloaded packs
root_packs = ET.Element("Packs")
for name, p in sorted(latest_packs.items()):
    bundle_file = os.path.join(BUNDLES_DIR, name.replace('/', '_'))
    if os.path.exists(bundle_file):
        with open(bundle_file, 'rb') as bf:
            file_hash = hashlib.md5(bf.read()).hexdigest().upper()
        
        ET.SubElement(root_packs, "Pack", {
            "Name": name,
            "Url": p['Url'],
            "Version": "2.46.0",
            "Attach": "1",
            "Hash": p['Hash'] or file_hash,
            "Priority": "0"
        })

tree_out = ET.ElementTree(root_packs)
ET.indent(tree_out, space="  ")
tree_out.write(PACKS_XML, encoding="utf-8", xml_declaration=False)

with open(PACKS_XML, 'rb') as f:
    packs_hash_val = hashlib.md5(f.read()).hexdigest().upper()

with open(PACKS_HASH, 'w', encoding='utf-8') as f:
    f.write(packs_hash_val)

print(f"\nGenerated updated packs.xml ({len(root_packs)} packs) and packs.xml.hash ({packs_hash_val})")

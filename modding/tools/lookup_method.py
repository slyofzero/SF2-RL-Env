import json

path = r"modding/build_cache/il2cpp_dump/script.json"
with open(path, encoding="utf-8") as f:
    data = json.load(f)

target_rva = 0x33ED24C

# Find the method containing target_rva
closest_method = None
closest_dist = float("inf")

for m in data.get("ScriptMethod", []):
    addr = m.get("Address", 0)
    if addr <= target_rva:
        dist = target_rva - addr
        if dist < closest_dist:
            closest_dist = dist
            closest_method = m

print(f"Target RVA: {hex(target_rva)}")
if closest_method:
    print(f"Contained in method: {closest_method.get('Name')}")
    print(f"Method Start RVA: {hex(closest_method.get('Address', 0))}")
    print(f"Offset from method start: +{hex(closest_dist)}")

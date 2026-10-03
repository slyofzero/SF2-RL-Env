import json

path = r"modding/build_cache/il2cpp_dump/script.json"
with open(path, encoding="utf-8") as f:
    data = json.load(f)

for m in data.get("ScriptMethod", []):
    name = m.get("Name", "")
    if "EndFightScreen" in name:
        print(f"{hex(m.get('Address', 0))}: {name}")

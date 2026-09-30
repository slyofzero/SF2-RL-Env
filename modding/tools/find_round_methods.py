import json

path = r'modding/build_cache/il2cpp_dump/script.json'
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

print(f"Total script methods: {len(data.get('ScriptMethod', []))}")
results = []
for m in data.get('ScriptMethod', []):
    name = m.get('Name', '')
    lower = name.lower()
    if 'endround' in lower or 'finishround' in lower or 'winround' in lower or 'onroundend' in lower or 'roundend' in lower or 'checkround' in lower:
        results.append((hex(m.get('Address', 0)), name))

for addr, name in results:
    print(f"{addr}: {name}")

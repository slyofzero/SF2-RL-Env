import json

path = r'modding/build_cache/il2cpp_dump/script.json'
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

print("Searching ScriptMethod...")
count = 0
for item in data.get('ScriptMethod', []):
    name = item.get('Name', '')
    lower = name.lower()
    if any(k in lower for k in ['round', 'battlefinish', 'finishround', 'winround']):
        addr = hex(item.get('Address', 0))
        print(f"{addr}: {name}")
        count += 1
        if count >= 60:
            break

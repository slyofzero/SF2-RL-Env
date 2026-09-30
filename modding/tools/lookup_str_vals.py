import json
with open('modding/build_cache/il2cpp_dump/stringliteral.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for item in data:
    addr = str(item.get('address')).upper()
    if addr in ['0X42867B0', '0X42879E0']:
        print(f"{addr}: {repr(item.get('value'))}")

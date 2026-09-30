import json

path = r'modding/build_cache/il2cpp_dump/stringliteral.json'
with open(path, 'r', encoding='utf-8') as f:
    data = json.load(f)

for item in data:
    s = item.get('value', '')
    lower = s.lower()
    if any(k in lower for k in ['round', 'rounds', 'win_round', 'round_win', 'round_count', 'max_round']):
        # Filter out obvious UI words if too noisy
        print(f"{item.get('address')}: {repr(s)}")

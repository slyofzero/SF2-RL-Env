import re

dump_path = r'modding/build_cache/il2cpp_dump/dump.cs'
with open(dump_path, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    # Looking for properties or methods returning int with battle, round, wins
    if re.search(r'int get_.*Round', line) or re.search(r'int get_.*Win', line) or re.search(r'int .*Victories', line) or re.search(r'int .*Rounds', line):
        print(f"Line {i}: {line.strip()}")

import re

dump_path = r'modding/build_cache/il2cpp_dump/dump.cs'
with open(dump_path, 'r', encoding='utf-8', errors='ignore') as f:
    for i, line in enumerate(f):
        if 'RoundsPanel' in line and 'class RoundsPanel' not in line:
            print(f"Line {i}: {line.strip()}")

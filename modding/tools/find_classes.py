import re

dump_path = r'modding/build_cache/il2cpp_dump/dump.cs'
with open(dump_path, 'r', encoding='utf-8', errors='ignore') as f:
    for i, line in enumerate(f):
        if line.startswith('public class ') or line.startswith('public abstract class '):
            if any(k in line.lower() for k in ['tournament', 'survival', 'duel', 'fightmanager', 'battlecontroller', 'battlemodel', 'fightscreen', 'fightcontroller']):
                print(f"Line {i}: {line.strip()}")

import re

subclasses = [
    'AJNNHGGLGIF', 'JFAGMCHGOEH', 'CALLBECPAIA', 'ICCLONHCNBL',
    'CNIGOFCKBGI', 'KMFIGBGAKNL', 'AGCDKMOOJGI', 'JCHNBADDBGO',
    'EFNDJJDBNFN', 'ONMBPNGKBBO', 'ECGPIFIJMFF', 'NIAFDKHDBMA', 'PNEKMHMACLG'
]

dump_path = r'modding/build_cache/il2cpp_dump/dump.cs'
with open(dump_path, 'r', encoding='utf-8', errors='ignore') as f:
    lines = f.readlines()

in_class = None
for i, line in enumerate(lines):
    if line.startswith('public class ') or line.startswith('public abstract class '):
        for s in subclasses:
            if f"class {s}" in line:
                in_class = s
                break
        else:
            in_class = None
    if in_class:
        if ('int ' in line or 'Int ' in line) and ('(' in line or '{ get;' in line):
            print(f"[{in_class}] Line {i}: {line.strip()}")

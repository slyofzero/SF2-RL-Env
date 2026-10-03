dump_path = r"modding/build_cache/il2cpp_dump/dump.cs"
with open(dump_path, encoding="utf-8", errors="ignore") as f:
    lines = f.readlines()

recording = False
for i, line in enumerate(lines):
    if "class RoundsPanel" in line:
        recording = True
        print(f"Line {i}: {line}")
    if recording:
        print(line, end="")
        if line.strip() == "}" and not lines[i - 1].strip().startswith("//"):
            recording = False
            break

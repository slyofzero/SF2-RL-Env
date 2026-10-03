import struct

so_path = r"c:\Users\Ishan\Personal\Porfolio\Shadow Fight 2\modding\build_cache\apktool_src\lib\arm64-v8a\libil2cpp.so"

start_off = 0x33DF000
end_off = 0x33F5000

with open(so_path, "rb") as f:
    f.seek(start_off)
    code = f.read(end_off - start_off)

print("Scanning FCJBEKHDLAF for 'CMP Wn, #2' (7100081f or similar)...")
matches = []
for i in range(0, len(code) - 8, 4):
    val = struct.unpack("<I", code[i : i + 4])[0]
    # CMP Wn, #2: 0x71000800 | (Rn << 5) | 0x1F
    # Mask out Rn:
    if (val & 0xFFFFFC00) == 0x71000800 and (val & 0x1F) == 0x1F:
        rn = (val >> 5) & 0x1F
        next_val = struct.unpack("<I", code[i + 4 : i + 8])[0]
        file_pc = start_off + i
        rva = file_pc + 0x4000
        matches.append((file_pc, rva, f"CMP W{rn}, #2 (next: {next_val:08x})"))

print(f"Found {len(matches)} matches in FCJBEKHDLAF:")
for file_pc, rva, desc in matches:
    print(f"  {hex(file_pc)} ({hex(rva)}): {desc}")

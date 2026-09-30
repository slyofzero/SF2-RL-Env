import struct

so_path = r'c:\Users\Ishan\Personal\Porfolio\Shadow Fight 2\modding\build_cache\apktool_src\lib\arm64-v8a\libil2cpp.so'

with open(so_path, 'rb') as f:
    code = f.read()

# STR Wt, [Xn, #0x20]
matches = []
for pc in range(0, len(code) - 8, 4):
    val = struct.unpack('<I', code[pc:pc+4])[0]
    if (val & 0xFFF00000) == 0xB9002000:
        rt = val & 0x1F
        rn = (val >> 5) & 0x1F
        rva = pc + 0x4000
        # Check if Rn is being loaded or if it's inside FCJBEKHDLAF or nearby
        if 0x33DF000 <= pc <= 0x3560000:
            matches.append((pc, rva, f"STR W{rt}, [X{rn}, #0x20]"))

print(f"Found {len(matches)} STR [Xn, #0x20] in fight engine range:")
for file_pc, rva, desc in matches:
    print(f"  {hex(file_pc)} ({hex(rva)}): {desc}")

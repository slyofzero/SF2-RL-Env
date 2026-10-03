import struct

so_path = r"c:\Users\Ishan\Personal\Porfolio\Shadow Fight 2\modding\build_cache\apktool_src\lib\arm64-v8a\libil2cpp.so"

start_off = 0x33DF000
end_off = 0x33F5000

with open(so_path, "rb") as f:
    f.seek(start_off)
    code = f.read(end_off - start_off)

print("Scanning FCJBEKHDLAF for LDR Wt, [Xn, #0x20]...")
matches = []
for i in range(0, len(code) - 8, 4):
    val = struct.unpack("<I", code[i : i + 4])[0]
    # 0xB9400000 is LDR Wt, [Xn, #pimm]
    # imm12 is bits 21-10. For #0x20, imm12 = 8 -> bits 21-10 = 0b000000001000 -> 0x00002000
    if (val & 0xFFF00000) == 0xB9402000:
        rt = val & 0x1F
        rn = (val >> 5) & 0x1F
        next_val = struct.unpack("<I", code[i + 4 : i + 8])[0]
        file_pc = start_off + i
        rva = file_pc + 0x4000
        matches.append((file_pc, rva, f"LDR W{rt}, [X{rn}, #0x20] (next: {next_val:08x})"))

print(f"Found {len(matches)} LDR [Xn, #0x20] in FCJBEKHDLAF:")
for file_pc, rva, desc in matches:
    print(f"  {hex(file_pc)} ({hex(rva)}): {desc}")

import struct

so_path = r"c:\Users\Ishan\Personal\Porfolio\Shadow Fight 2\modding\build_cache\apktool_src\lib\arm64-v8a\libil2cpp.so"

start_off = 0x33EFA20
end_off = 0x33EFB50

with open(so_path, "rb") as f:
    f.seek(start_off)
    code = f.read(end_off - start_off)

for i in range(0, len(code), 4):
    pc = start_off + i
    rva = pc + 0x4000
    val = struct.unpack("<I", code[i : i + 4])[0]
    desc = f"{val:08x}"
    if (val & 0x3F800000) == 0x31000000 and (val & 0x1F) == 0x1F:
        rn = (val >> 5) & 0x1F
        imm12 = (val >> 10) & 0xFFF
        desc = f"CMP W{rn}, #{imm12}"
    elif (val >> 26) == 0x25:
        imm26 = val & 0x03FFFFFF
        if imm26 & (1 << 25):
            imm26 -= 1 << 26
        desc = f"BL {hex(rva + (imm26 << 2))}"
    elif (val & 0xFF000010) == 0x54000000:
        conds = ["eq", "ne", "cs", "cc", "mi", "pl", "vs", "vc", "hi", "ls", "ge", "lt", "gt", "le", "al", "nv"]
        desc = f"B.{conds[val & 0xF]}"
    print(f"{hex(pc)} ({hex(rva)}):  {desc}")

import struct

so_path = r"c:\Users\Ishan\Personal\Porfolio\Shadow Fight 2\modding\build_cache\apktool_src\lib\arm64-v8a\libil2cpp.so"

start_off = 0x33E7FD0
end_off = 0x33E80A0

with open(so_path, "rb") as f:
    f.seek(start_off)
    code = f.read(end_off - start_off)

for i in range(0, len(code), 4):
    pc = start_off + i
    rva = pc + 0x4000
    val = struct.unpack("<I", code[i : i + 4])[0]
    desc = f"{val:08x}"
    if (val & 0x3F800000) == 0x31000000 and (val & 0x1F) == 0x1F:
        desc = f"CMP W{(val >> 5) & 0x1F}, #{((val >> 10) & 0xFFF)}"
    elif (val >> 26) == 0x25:
        imm26 = val & 0x03FFFFFF
        if imm26 & (1 << 25):
            imm26 -= 1 << 26
        desc = f"BL {hex(rva + (imm26 << 2))}"
    elif (val & 0xFF000010) == 0x54000000:
        conds = ["eq", "ne", "cs", "cc", "mi", "pl", "vs", "vc", "hi", "ls", "ge", "lt", "gt", "le", "al", "nv"]
        imm19 = (val >> 5) & 0x7FFFF
        if imm19 & (1 << 18):
            imm19 -= 1 << 19
        desc = f"B.{conds[val & 0xF]} {hex(rva + (imm19 << 2))}"
    elif (val & 0xFFC00000) == 0xB9400000:
        desc = f"LDR W{val & 0x1F}, [X{(val >> 5) & 0x1F}, #{hex(((val >> 10) & 0xFFF) * 4)}]"

    print(f"{hex(pc)} ({hex(rva)}):  {code[i : i + 4].hex()}  {desc}")

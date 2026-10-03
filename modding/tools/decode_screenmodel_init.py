import struct

so_path = r"c:\Users\Ishan\Personal\Porfolio\Shadow Fight 2\modding\build_cache\apktool_src\lib\arm64-v8a\libil2cpp.so"

start_off = 0x3559EB4
end_off = 0x355A050

with open(so_path, "rb") as f:
    f.seek(start_off)
    code = f.read(end_off - start_off)

for i in range(0, len(code), 4):
    pc_off = start_off + i
    pc_rva = pc_off + 0x4000
    val = struct.unpack("<I", code[i : i + 4])[0]

    desc = f"{val:08x}"
    if (val >> 26) == 0x25:
        imm26 = val & 0x03FFFFFF
        if imm26 & (1 << 25):
            imm26 -= 1 << 26
        dest = pc_rva + (imm26 << 2)
        desc = f"BL {hex(dest)}"
    elif (val >> 26) == 0x05:
        imm26 = val & 0x03FFFFFF
        if imm26 & (1 << 25):
            imm26 -= 1 << 26
        dest = pc_rva + (imm26 << 2)
        desc = f"B {hex(dest)}"
    elif (val & 0xFF000010) == 0x54000000:
        imm19 = (val >> 5) & 0x7FFFF
        if imm19 & (1 << 18):
            imm19 -= 1 << 19
        dest = pc_rva + (imm19 << 2)
        cond = val & 0xF
        conds = ["eq", "ne", "cs", "cc", "mi", "pl", "vs", "vc", "hi", "ls", "ge", "lt", "gt", "le", "al", "nv"]
        desc = f"B.{conds[cond]} {hex(dest)}"
    elif (val & 0x7E000000) == 0x34000000:
        op = (val >> 24) & 1
        imm19 = (val >> 5) & 0x7FFFF
        if imm19 & (1 << 18):
            imm19 -= 1 << 19
        dest = pc_rva + (imm19 << 2)
        rt = val & 0x1F
        desc = f"{'CBNZ' if op else 'CBZ'} X{rt}, {hex(dest)}"

    print(f"{hex(pc_off)} ({hex(pc_rva)}):  {code[i : i + 4].hex()}  {desc}")

import struct

so_path = r'c:\Users\Ishan\Personal\Porfolio\Shadow Fight 2\modding\build_cache\apktool_src\lib\arm64-v8a\libil2cpp.so'

with open(so_path, 'rb') as f:
    data = f.read()

for target in [0x34255E4, 0x34255EC]:
    matches = []
    for pc in range(0, len(data) - 4, 4):
        val = struct.unpack('<I', data[pc:pc+4])[0]
        if (val >> 26) == 0x25:
            imm26 = val & 0x03FFFFFF
            if imm26 & (1 << 25): imm26 -= (1 << 26)
            pc_rva = pc + 0x4000
            dest = pc_rva + (imm26 << 2)
            if dest == target:
                matches.append((pc, pc_rva))
    print(f"Target {hex(target)}: {len(matches)} callers")
    for file_off, rva in matches:
        print(f"  {hex(file_off)} ({hex(rva)})")

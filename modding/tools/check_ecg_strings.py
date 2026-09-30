import struct

so_path = r'c:\Users\Ishan\Personal\Porfolio\Shadow Fight 2\modding\build_cache\apktool_src\lib\arm64-v8a\libil2cpp.so'

start_off = 0x34215F4
end_off = 0x34216BC

with open(so_path, 'rb') as f:
    f.seek(start_off)
    code = f.read(end_off - start_off)

# Search for strings referenced in this function
print("Scanning ECGPIFIJMFF.HNIHOIAMDPC for string references...")
for i in range(0, len(code) - 8, 4):
    pc = start_off + i
    rva = pc + 0x4000
    val = struct.unpack('<I', code[i:i+4])[0]
    # Check ADRP + LDR
    if (val & 0x9F000000) == 0x90000000:
        next_val = struct.unpack('<I', code[i+4:i+8])[0]
        immlo = (val >> 29) & 0x3
        immhi = (val >> 5) & 0x7FFFF
        imm = (immhi << 2) | immlo
        if imm & (1 << 20): imm -= (1 << 21)
        pc_page = rva & ~0xFFF
        target_page = pc_page + (imm << 12)
        if (next_val & 0xFFC00000) == 0xF9400000:
            imm12 = (next_val >> 10) & 0xFFF
            target_addr = target_page + imm12 * 8
            print(f"  Loads from {hex(target_addr)} at {hex(pc)}")

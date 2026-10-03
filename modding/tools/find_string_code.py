import struct

so_path = r"c:\Users\Ishan\Personal\Porfolio\Shadow Fight 2\modding\build_cache\apktool_src\lib\arm64-v8a\libil2cpp.so"

with open(so_path, "rb") as f:
    data = f.read()

target_addr = 0x4150EE0
page = target_addr & ~0xFFF
page_off = target_addr & 0xFFF

print(f"Target address: {hex(target_addr)} (Page: {hex(page)}, Offset: {hex(page_off)})")

# Search for ADRP instructions targeting `page`
matches = []
for pc in range(0, len(data) - 8, 4):
    val = struct.unpack("<I", data[pc : pc + 4])[0]
    # ADRP: op=1, [30:29]=immlo, [28:24]=10000, [23:5]=immhi, [4:0]=Rd
    if (val & 0x9F000000) == 0x90000000:
        immlo = (val >> 29) & 0x3
        immhi = (val >> 5) & 0x7FFFF
        imm = (immhi << 2) | immlo
        if imm & (1 << 20):
            imm -= 1 << 21
        pc_page = (pc + 0x4000) & ~0xFFF  # In memory, RVA = File Offset + 0x4000
        calc_page = pc_page + (imm << 12)
        if calc_page == page:
            # Check next instruction for LDR with offset page_off
            next_val = struct.unpack("<I", data[pc + 4 : pc + 8])[0]
            # LDR (64-bit unsigned offset): [31:30]=11, [29:27]=111, [26]=0, [25:24]=01, [23:22]=00, [21:10]=imm12
            # 0xF9400000: LDR Xt, [Xn, #pimm]
            # For 64-bit LDR, imm12 is scaled by 8: pimm = imm12 * 8
            if (next_val & 0xFFC00000) == 0xF9400000:
                ldr_imm12 = (next_val >> 10) & 0xFFF
                ldr_offset = ldr_imm12 * 8
                if ldr_offset == page_off:
                    matches.append((pc, pc + 0x4000))

print(f"Found {len(matches)} matches for string reference:")
for file_off, rva in matches:
    print(f"  File offset: {hex(file_off)} (RVA: {hex(rva)})")

import struct

so_path = r"c:\Users\Ishan\Personal\Porfolio\Shadow Fight 2\modding\build_cache\apktool_src\lib\arm64-v8a\libil2cpp.so"

with open(so_path, "rb") as f:
    data = f.read()


def find_bl_to_target(target_pc):
    results = []
    # Every instruction is 4 bytes
    for pc in range(0, len(data) - 4, 4):
        val = struct.unpack("<I", data[pc : pc + 4])[0]
        # BL opcode has top 6 bits == 0b100101 (0x25 in top 6 bits -> 0x94000000)
        if (val >> 26) == 0x25:
            # 26-bit signed immediate
            imm26 = val & 0x03FFFFFF
            if imm26 & (1 << 25):  # sign extend
                imm26 -= 1 << 26
            dest = pc + (imm26 << 2)
            if dest == target_pc:
                results.append(pc)
    return results


print("Scanning for calls to RoundsPanel.Init (0x352ec58)...")
callers_init = find_bl_to_target(0x352EC58)
for c in callers_init:
    print(f"  Called from: {hex(c)}")

print("Scanning for calls to RoundsPanel.UpdateVictories (0x352ea7c)...")
callers_update = find_bl_to_target(0x352EA7C)
for c in callers_update:
    print(f"  Called from: {hex(c)}")

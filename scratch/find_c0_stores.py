import capstone, zipfile
cs = capstone.Cs(capstone.CS_ARCH_ARM64, capstone.CS_MODE_ARM)

with open('bluestacks/apks/SF2_OG.apk', 'rb') as f:
    z = zipfile.ZipFile(f)
    lib = z.read('lib/arm64-v8a/libil2cpp.so')

# Search across all .text for stores to 0xc0
# str x..., [x..., #0xc0]
import struct
for pc in range(0x3400000, 0x3600000, 4):
    inst = struct.unpack('<I', lib[pc:pc+4])[0]
    # str xt, [xn, #0xc0]
    # size=3 (64-bit), 111 110 01 00 imm12 Rn Rt
    # 0xf9000000 | (imm12 << 10)
    # for 0xc0: 0xc0 / 8 = 24 = 0x18. imm12 = 0x18. (0x18 << 10) = 0x6000
    if (inst & 0xFFC00000) == 0xF9006000:
        code = lib[pc:pc+4]
        for i in cs.disasm(code, pc + 0x4000):
            print(f'{hex(pc)} ({hex(i.address)}): {i.mnemonic} {i.op_str}')

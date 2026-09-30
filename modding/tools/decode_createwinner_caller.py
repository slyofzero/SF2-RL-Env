import struct

so_path = r'c:\Users\Ishan\Personal\Porfolio\Shadow Fight 2\modding\build_cache\apktool_src\lib\arm64-v8a\libil2cpp.so'

start_off = 0x33EF700
end_off = 0x33EFA20

with open(so_path, 'rb') as f:
    f.seek(start_off)
    code = f.read(end_off - start_off)

for i in range(0, len(code), 4):
    pc = start_off + i
    rva = pc + 0x4000
    val = struct.unpack('<I', code[i:i+4])[0]
    
    desc = f"{val:08x}"
    if (val & 0xFF000010) == 0x54000000:
        conds = ["eq","ne","cs","cc","mi","pl","vs","vc","hi","ls","ge","lt","gt","le","al","nv"]
        desc = f"B.{conds[val & 0xF]} {hex(rva + (((val>>5)&0x7FFFF if not (val&0x100000) else ((val>>5)&0x7FFFF)-(1<<19))<<2))}"
    elif (val & 0x3F800000) == 0x31000000 and (val & 0x1F) == 0x1F:
        rn = (val >> 5) & 0x1F
        imm12 = (val >> 10) & 0xFFF
        desc = f"CMP W{rn}, #{imm12}"
    elif (val >> 26) == 0x05:
        imm26 = val & 0x03FFFFFF
        if imm26 & (1 << 25): imm26 -= (1 << 26)
        desc = f"B {hex(rva + (imm26<<2))}"
    elif (val >> 26) == 0x25:
        imm26 = val & 0x03FFFFFF
        if imm26 & (1 << 25): imm26 -= (1 << 26)
        desc = f"BL {hex(rva + (imm26<<2))}"
    elif (val & 0x7E000000) == 0x34000000:
        op = (val >> 24) & 1
        imm19 = (val >> 5) & 0x7FFFF
        if imm19 & (1 << 18): imm19 -= (1 << 19)
        prefix = 'CBNZ' if op else 'CBZ'
        desc = f"{prefix} X{val & 0x1F}, {hex(rva + (imm19<<2))}"
    elif (val & 0x3F800000) == 0x52800000:
        imm16 = (val >> 5) & 0xFFFF
        hw = (val >> 21) & 3
        rd = val & 0x1F
        desc = f"MOV W{rd}, #{imm16 << (hw*16)}"
    elif (val & 0xFFC00000) == 0xB9400000:
        rt = val & 0x1F
        rn = (val >> 5) & 0x1F
        imm12 = (val >> 10) & 0xFFF
        desc = f"LDR W{rt}, [X{rn}, #{hex(imm12*4)}]"
    elif (val & 0xFFC00000) == 0xF9400000:
        rt = val & 0x1F
        rn = (val >> 5) & 0x1F
        imm12 = (val >> 10) & 0xFFF
        desc = f"LDR X{rt}, [X{rn}, #{hex(imm12*8)}]"
        
    print(f"{hex(pc)} ({hex(rva)}):  {code[i:i+4].hex()}  {desc}")

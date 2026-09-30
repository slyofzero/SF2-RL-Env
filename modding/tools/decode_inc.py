import struct

so_path = r'c:\Users\Ishan\Personal\Porfolio\Shadow Fight 2\modding\build_cache\apktool_src\lib\arm64-v8a\libil2cpp.so'

start_off = 0x33E9430
end_off = 0x33E9480

with open(so_path, 'rb') as f:
    f.seek(start_off)
    code = f.read(end_off - start_off)

for i in range(0, len(code), 4):
    pc = start_off + i
    rva = pc + 0x4000
    val = struct.unpack('<I', code[i:i+4])[0]
    desc = f"{val:08x}"
    if (val & 0xFFC00000) == 0xB9000000:
        desc = f"STR W{val & 0x1F}, [X{(val>>5)&0x1F}, #{hex(((val>>10)&0xFFF)*4)}]"
    elif (val & 0xFFC00000) == 0xB9400000:
        desc = f"LDR W{val & 0x1F}, [X{(val>>5)&0x1F}, #{hex(((val>>10)&0xFFF)*4)}]"
    elif (val & 0x3F800000) == 0x11000000: # ADD immediate
        desc = f"ADD W{val & 0x1F}, W{(val>>5)&0x1F}, #{((val>>10)&0xFFF)}"
    elif (val & 0x3F800000) == 0x31000000 and (val & 0x1F) == 0x1F:
        desc = f"CMP W{(val>>5)&0x1F}, #{((val>>10)&0xFFF)}"
    print(f"{hex(pc)} ({hex(rva)}):  {desc}")

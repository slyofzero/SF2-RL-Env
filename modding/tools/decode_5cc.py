import struct

so_path = r'c:\Users\Ishan\Personal\Porfolio\Shadow Fight 2\modding\build_cache\apktool_src\lib\arm64-v8a\libil2cpp.so'

start_off = 0x33E95BC
end_off = 0x33E9600

with open(so_path, 'rb') as f:
    f.seek(start_off)
    code = f.read(end_off - start_off)

for i in range(0, len(code), 4):
    pc = start_off + i
    rva = pc + 0x4000
    val = struct.unpack('<I', code[i:i+4])[0]
    print(f"{hex(pc)} ({hex(rva)}):  {val:08x}")

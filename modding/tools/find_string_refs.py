import struct

so_path = r"c:\Users\Ishan\Personal\Porfolio\Shadow Fight 2\modding\build_cache\apktool_src\lib\arm64-v8a\libil2cpp.so"

# String literal pointer or address in 64-bit little endian
target_addr = 0x42887D0

# In ARM64, adrp + add or pointer in .data/.rodata
with open(so_path, "rb") as f:
    data = f.read()

# Check direct 8-byte pointer
target_bytes = struct.pack("<Q", target_addr)
pos = 0
found_ptrs = []
while True:
    pos = data.find(target_bytes, pos)
    if pos == -1:
        break
    found_ptrs.append(pos)
    print(f"Found pointer to 0x42887D0 at file offset: {hex(pos)}")
    pos += 8

# Also search for "Filght::EndRound" directly in data
pos = data.find(b"Filght::EndRound")
if pos != -1:
    print(f"Found ascii string at file offset: {hex(pos)}")

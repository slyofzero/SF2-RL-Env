import struct

so_path = r"c:\Users\Ishan\Personal\Porfolio\Shadow Fight 2\modding\build_cache\apktool_src\lib\arm64-v8a\libil2cpp.so"

with open(so_path, "rb") as f:
    f.seek(0x6DBDB0)
    data = f.read(64)
    print("Pointers around 0x6dbdb8:")
    for i in range(0, len(data), 8):
        ptr = struct.unpack("<Q", data[i : i + 8])[0]
        print(f"Offset {hex(0x6DBDB0 + i)}: {hex(ptr)}")

# Now find where the pointer table at 0x6dbdb8 is loaded from code!
# In ARM64: adrp xN, #0x6db000; ldr xN, [xN, #0xdb8]
target_page = 0x6DB000
page_offset = 0xDB8
print(f"\nSearching for adrp/ldr to page {hex(target_page)} and offset {hex(page_offset)}...")

with open(so_path, "rb") as f:
    code = f.read()

# Let's search for references to 0x6dbdb8 or nearby in .text
target_bytes = struct.pack("<Q", 0x6DBDB8)
pos = code.find(target_bytes)
print(f"Direct pointer to 0x6dbdb8: {hex(pos) if pos != -1 else 'None'}")

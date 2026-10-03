import os

for root, _dirs, files in os.walk(r"c:\Users\Ishan\Personal\Porfolio\Shadow Fight 2"):
    if "libil2cpp.so" in files:
        p = os.path.join(root, "libil2cpp.so")
        print(f"{p} ({os.path.getsize(p)} bytes)")

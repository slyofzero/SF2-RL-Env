so_path = r"c:\Users\Ishan\Personal\Porfolio\Shadow Fight 2\modding\build_cache\apktool_src\lib\arm64-v8a\libil2cpp.so"

with open(so_path, "rb") as f:
    # ScreenModel.UpdateVictories at file offset 0x355B26C
    f.seek(0x355B26C)
    data = f.read(128)
    print("ScreenModel.UpdateVictories bytes:")
    print(" ".join(f"{b:02x}" for b in data[:64]))

    # RoundsPanel.Init at file offset 0x352AC58
    f.seek(0x352AC58)
    data = f.read(128)
    print("\nRoundsPanel.Init bytes:")
    print(" ".join(f"{b:02x}" for b in data[:64]))

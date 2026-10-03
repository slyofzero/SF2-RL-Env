import re

with open("modding/build_cache/live_users.xml", encoding="utf-8") as f:
    text = f.read()

for attr in ["CurrentZone", "MapFocus", "FightIDS"]:
    m = re.findall(rf'{attr}="([^"]+)"', text)
    print(f"{attr}: {m}")

# Check all battles unlocked
battles = re.findall(r'<Battle\s+[^>]*Name="([^"]+)"[^>]*Locked="([^"]+)"', text)
print(f"Total battles: {len(battles)}")
for b in battles:
    if "BOSS" in b[0] or "ZONE_6" in b[0]:
        print(f"  Battle: {b[0]}, Locked: {b[1]}")

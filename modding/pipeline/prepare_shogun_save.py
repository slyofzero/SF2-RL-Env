import hashlib
import os
import re
import subprocess
import time

LIVE_XML = "modding/build_cache/live_users.xml"
OUT_XML = "modding/build_cache/shogun_users.xml"
OUT_HASH = "modding/build_cache/shogun_users.xml.hash"

with open(LIVE_XML, "r", encoding="utf-8") as f:
    content = f.read()

# 1. Update Zone, Focus and FightIDS
content = re.sub(r'CurrentZone="[^"]*"', 'CurrentZone="ZONE_6"', content)
content = re.sub(r'MapFocus="[^"]*"', 'MapFocus="ZONE_6|BOSS_SAMURAI"', content)
content = re.sub(r'FightIDS="[^"]*"', 'FightIDS="ZONE_6|BOSS_SAMURAI|6"', content)

# 2. Update Battles section: unlock BOSS_SAMURAI
content = re.sub(
    r'<Battle Name="ZONE_6\|BOSS_SAMURAI_LOCKED\|"[^>]*/>',
    '<Battle Name="ZONE_6|BOSS_SAMURAI|" Locked="0" Hidden="0" ReplayCount="0" />',
    content
)

# If ZONE_6|BOSS_SAMURAI| doesn't exist, add it
if 'Battle Name="ZONE_6|BOSS_SAMURAI|"' not in content:
    content = content.replace(
        '<Battles>',
        '<Battles>\n        <Battle Name="ZONE_6|BOSS_SAMURAI|" Locked="0" Hidden="0" ReplayCount="0" />'
    )

# 3. Add Shogun and Bodyguards fights
shogun_fights = """
        <Fight ID="-1" IDS="ZONE_6|BOSS_SAMURAI|1" CompletedCount="1" LossCount="0" EclipseCompletedCount="0" EclipseLossCount="0" StoryCount="0" CompletedTime="1790000000" TimeLeft="0" RandomizeTimeLeft="0" Level="1" />
        <Fight ID="-1" IDS="ZONE_6|BOSS_SAMURAI|2" CompletedCount="1" LossCount="0" EclipseCompletedCount="0" EclipseLossCount="0" StoryCount="0" CompletedTime="1790000000" TimeLeft="0" RandomizeTimeLeft="0" Level="2" />
        <Fight ID="-1" IDS="ZONE_6|BOSS_SAMURAI|3" CompletedCount="1" LossCount="0" EclipseCompletedCount="0" EclipseLossCount="0" StoryCount="0" CompletedTime="1790000000" TimeLeft="0" RandomizeTimeLeft="0" Level="3" />
        <Fight ID="-1" IDS="ZONE_6|BOSS_SAMURAI|4" CompletedCount="1" LossCount="0" EclipseCompletedCount="0" EclipseLossCount="0" StoryCount="0" CompletedTime="1790000000" TimeLeft="0" RandomizeTimeLeft="0" Level="4" />
        <Fight ID="-1" IDS="ZONE_6|BOSS_SAMURAI|5" CompletedCount="1" LossCount="0" EclipseCompletedCount="0" EclipseLossCount="0" StoryCount="0" CompletedTime="1790000000" TimeLeft="0" RandomizeTimeLeft="0" Level="5" />
        <Fight ID="-1" IDS="ZONE_6|BOSS_SAMURAI|6" CompletedCount="0" LossCount="0" EclipseCompletedCount="0" EclipseLossCount="0" StoryCount="0" CompletedTime="0" TimeLeft="0" RandomizeTimeLeft="0" Level="6" />"""

if 'IDS="ZONE_6|BOSS_SAMURAI|6"' not in content:
    content = re.sub(r'(<Fights>\s*)', r'\1' + shogun_fights + '\n', content)

# 4. Save and calculate MD5
with open(OUT_XML, "w", encoding="utf-8") as f:
    f.write(content)

raw_bytes = content.encode("utf-8")
md5_hash = hashlib.md5(raw_bytes).hexdigest().upper()

with open(OUT_HASH, "w", encoding="utf-8") as f:
    f.write(md5_hash)

print(f"Generated {OUT_XML} with MD5: {md5_hash}")

# 5. Push to emulator
adb = r"C:\Program Files\BlueStacks_nxt\HD-Adb.exe"
device = "127.0.0.1:5555"
remote_dir = "/sdcard/Android/data/com.nekki.catblasters/files/userdata"

subprocess.run([adb, "connect", "127.0.0.1:5555"], check=False)

subprocess.run([adb, "-s", device, "push", OUT_XML, f"{remote_dir}/users.xml"], check=True)
subprocess.run([adb, "-s", device, "push", OUT_HASH, f"{remote_dir}/users.xml.hash"], check=True)
subprocess.run([adb, "-s", device, "push", OUT_XML, f"{remote_dir}/users_backup.xml"], check=True)
subprocess.run([adb, "-s", device, "push", OUT_HASH, f"{remote_dir}/users_backup.xml.hash"], check=True)

print("Pushed Shogun profile & hashes to emulator successfully!")

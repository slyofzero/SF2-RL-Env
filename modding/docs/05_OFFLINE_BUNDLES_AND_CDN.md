# Document 05: Offline Asset Bundles, CDN & Pack Delivery

This document explains why the game prompts for downloads, how external asset bundles are cataloged and fetched from Nekki's CDN, and how all 30 game asset packs were pre-bundled inside the APK for 100% offline play.

---

## 1. Why The Game Requests Downloads

When installed on a clean device, *Shadow Fight 2* does not contain all graphics, animations, and story chapters inside the base APK:
1. Google Play and third-party stores historically enforce a ~150 MB base package limit.
2. The game defers downloading Act 2 through Act 7, high-resolution animations, and weekly events until the player reaches those chapters or enters the shop.
3. On first launch, if `/sdcard/Android/data/<package>/files/gamedata/bundles/` is missing required files, the game calculates their combined byte size and displays the modal:
   ```text
   LOADING REQUIRED!
   Some content is missing and needs to be updated:
   SIZE: 31.58 MB
   [DOWNLOAD]
   ```

---

## 2. Complete Inventory of Bundled Asset Packages

Our standalone APK (`333.23 MB`) embeds **all 30 game asset packages** (~188 MB uncompressed) in `assets/gamedata/`:

### A. Core Engine & Versional Bundles (3 Packs)
* **`ANIMATIONS`** (6.06 MB): High-framerate weapon swings, character kicks, boss signature moves.
* **`VERSIONAL_CONFIGS`** (6.44 MB): Equipment statistics, weapon balancing, damage curves, level tables.
* **`VERSIONAL_ASSETS`** (4.57 MB): Shared UI widgets, HUD icons, font tables.

### B. Story Campaign Chapters (10 Packs)
* **`ZONE_1`** (34.85 MB): Act 1 (Lynx's domain, Tournament, Survival, Dojo).
* **`ZONE_2`** (14.78 MB): Act 2 (Hermit's domain).
* **`ZONE_3`** (14.51 MB): Act 3 (Butcher's domain).
* **`ZONE_4`** (12.96 MB): Act 4 (Wasp's domain).
* **`ZONE_5`** (14.66 MB): Act 5 (Widow's domain).
* **`ZONE_6`** (25.03 MB): Act 6 (Shogun's domain).
* **`ZONE_7`** (12.65 MB): Act 7, Part 1 (Titan's domain / Gates of Shadows).
* **`ZONE_7_2`** (3.30 MB): Act 7, Part 2.
* **`ZONE_7_3`** (14.79 MB): Act 7, Part 3.
* **`ZONE_IM`** (4.27 MB): Interlude campaign.

### C. Live Events & Seasonal Festivals (5 Packs - 23.58 MB)
* **`MA_FEST_26`** (13.54 MB): Martial Arts Festival 2026 event.
* **`SUMMER_FEST_25`** (6.51 MB): Summer Festival assets.
* **`SUMMER_FEST_26`** (1.20 MB): Summer Festival 2026 raid arena.
* **`SUMMER_FEST_CHEST`** (1.06 MB): Event chest rewards and loot graphics.
* **`EVENTS_COMMON`** (0.18 MB): Shared event UI frames and timers.

### D. Weekly Weapon & Armor Offers (12 Packs - 8.05 MB)
* **`WEEKLY_OFFER_12`** through **`22`**: Contains level 1 through level 52 promotional weapon sets (God Eater Glaive, Futurist Magic, Agnis Seal).
* *Note: The sum of `EVENTS` ($23.58\text{ MB}$) and `OFFERS` ($8.05\text{ MB}$) equals **$31.63\text{ MB}$**, resolving the exact **31.58 MiB** download prompt!*

---

## 3. The Catalog Manifests: `config_cdn.xml` vs. `packs.xml`

### `config_cdn.xml` (The Master CDN Catalog)
Located in `modding/assets/downloaded_gamedata/config_cdn.xml`. Contains 100+ items with direct CDN URLs:
```xml
<item 
  Name="ZONE_2" 
  Url="https://assets.nekki.com/shadowfight/unity_packs/SF2_free/zone_2_..._android" 
  Size="15497050" 
  Hash="1768D4E15B5B8147419D3146CAE67F1C" 
  MinVersion="2.46.0" />
```

### `packs.xml` (The Client Local Registry)
Located in `modding/assets/downloaded_gamedata/packs.xml`. Read by the game engine on startup:
```xml
<Packs>
  <Pack 
    Name="ZONE_2" 
    Url="..." 
    Version="2.46.0" 
    Attach="1" 
    Hash="1768D4E15B5B8147419D3146CAE67F1C" 
    Priority="0" />
</Packs>
```
* **The `Attach="1"` Attribute**: Informs the engine that the bundle is mounted and ready for immediate memory mapping without calling network APIs.
* **The `packs.xml.hash` Companion**: Stores `MD5(packs.xml)`. If this hash is missing or mismatched, the game wipes `packs.xml` and attempts to re-download from the CDN.

---

## 4. "Changing What Changes What" (Adding New Packs)

If a future game mode (such as Underworld raids) requests new downloads:

### Option A: Use the Automated Content Downloader Script
```powershell
# Search and download any raid bundles
.venv\Scripts\python .agents/skills/game-content-downloader/scripts/download_packs.py --pattern RAID
```
This automatically downloads the files, verifies hashes, updates `packs.xml`, and recalculates `packs.xml.hash`.

### Option B: Capture via ADB Pull from BlueStacks
If BlueStacks downloads new files during a live game session:
```powershell
& "C:\Program Files\BlueStacks_nxt\HD-Adb.exe" pull /sdcard/Android/data/com.nekki.catblasters/files/gamedata/bundles/ modding/assets/downloaded_gamedata/bundles/
& "C:\Program Files\BlueStacks_nxt\HD-Adb.exe" pull /sdcard/Android/data/com.nekki.catblasters/files/gamedata/packs.xml modding/assets/downloaded_gamedata/packs.xml
& "C:\Program Files\BlueStacks_nxt\HD-Adb.exe" pull /sdcard/Android/data/com.nekki.catblasters/files/gamedata/packs.xml.hash modding/assets/downloaded_gamedata/packs.xml.hash
```

### Then Rebuild:
Update `AssetExtractor.smali` with the new file names, bump the marker (e.g. to `.all_packs_v3`), and run:
```powershell
.venv\Scripts\python modding\pipeline\build_cat_blasters.py
```

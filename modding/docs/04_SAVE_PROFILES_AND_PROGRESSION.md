# Document 04: Save Profiles, Progression & Tutorial Bypasses

This document explains the structure of the game's XML save profiles, how the tutorial state machine works, how to modify player stats/equipment, and how the companion hash verification functions.

---

## 1. Save File Location & Ecosystem

The player profile is maintained in `/sdcard/Android/data/<package>/files/userdata/`:

| File | Purpose |
| :--- | :--- |
| `users.xml` | Primary save state: player stats, level, currency, inventory, quest progression, map unlocks. |
| `users.xml.hash` | 32-character hexadecimal MD5 hash of `users.xml`. |
| `users_backup.xml` | Fallback mirror save written whenever `users.xml` updates. |
| `users_backup.xml.hash` | 32-character hexadecimal MD5 hash of `users_backup.xml`. |
| `localSettings.bin` | Binary local user preferences (audio volume, graphics quality, language). |
| `gamingServiceSettings.bin`| Cloud sync & gaming service linkage state. |
| `initSettings.bin` | Initial bootstrap configuration and first-run timestamp. |

Our repository preserves the gold-standard reference save files inside [`modding/assets/userdata/`](file:///c:/Users/Ishan/Personal/Porfolio/Shadow%20Fight%202/modding/assets/userdata/).

---

## 2. Anatomy of `users.xml`

```xml
<?xml version="1.0" encoding="utf-8"?>
<Root>
  <CurrentUser ID="1" Language="eng" GraphicsSettings="Default" ... />
  <Warriors>
    <Warrior 
      ID="1" 
      FirstName="NAME_SHADOW" 
      Avatar="avatar_hero"
      Level="3" 
      Experience="20" 
      Money="25170" 
      Bonus="100" 
      Strength="3" 
      Stamina="3" 
      Tutorial="END" 
      CurrentZone="ZONE_1" 
      Weapon="WEAPON_KNIVES" 
      Armor="Body" 
      Helm="Head" 
      MapFocus="ZONE_1|Tournament" 
      FightIDS="ZONE_1|BOSS_LYNX|1">
      
      <Items>
        <Item Name="Body" Equipped="1" Count="1" UpgradeLevel="0" ... />
        <Item Name="Head" Equipped="1" Count="1" UpgradeLevel="0" ... />
        <Item Name="WEAPON_KNIVES" Equipped="1" Count="1" UpgradeLevel="0" ... />
      </Items>
      
      <Perks>
        <Perk Name="PERK_DOUBLE_SWEEP" Value="1" />
      </Perks>
      
      <Battles>
        <Battle ID="ZONE_1|Tournament|1" State="Win" Score="2" />
        <Battle ID="ZONE_1|Survival|1" State="Win" Score="1" />
      </Battles>
    </Warrior>
  </Warriors>
</Root>
```

---

## 3. The Tutorial State Machine & How It Was Bypassed

When launching a fresh copy of the game, the state machine (`JAKHNKEHNBE`) checks the `Tutorial` attribute:

| `Tutorial` Attribute Value | Engine Behavior |
| :--- | :--- |
| `""` (Empty / Missing) | Triggers `STEP_WELCOME`. Sensei interrupts with dialogue: *"Well, well... my vain disciple has returned!"* Forces the Punching Bag fight. |
| `"STEP_PUNCHBAG"` | Forces the Punching Bag training round. |
| `"STEP_KENJI"` | Forces the initial sword fight against Kenji. |
| `"STEP_SHOP"` | Locks the UI, forcing the player to purchase Knives from the shop. |
| `"STEP_SHIN"` | Forces the fight against Lynx's bodyguard Shin (`ZONE_1|BOSS_LYNX|1`). |
| `"STEP_BOSS"` | Sensei forces the player to challenge Lynx immediately, locking out Tournament. |
| **`"END_TUTORIAL"`** or **`"END"`** | **The Master Bypass**. Sensei dialogue is silenced permanently. All tutorial constraints are released, and the Act 1 map opens with full player freedom. |

### Removing Sensei's Lynx Trap
Even with `Tutorial="END"`, if `<Quests>` contains `<Quest Name="StoryTutorialBossFight" />`, Sensei will pop up and force-focus Lynx. In our embedded save:
1. `StoryTutorialBossFight` was deleted from `<Quests />`.
2. `MapFocus="ZONE_1|Tournament"` was set.
3. `<Battles>` was prepended with Tournament and Survival battle nodes.

---

## 4. "Changing What Changes What" (Save Customization Guide)

All changes are made in [`modding/assets/userdata/users.xml`](file:///c:/Users/Ishan/Personal/Porfolio/Shadow%20Fight%202/modding/assets/userdata/users.xml).

### Want more Coins or Gems (Bonus)?
Modify the `<Warrior>` attributes:
* `Money="999999"` (Coins)
* `Bonus="50000"` (Gems / Rubies)

> [!NOTE]
> Normally, setting high currency triggers the anti-cheat crash. Because our `libil2cpp.so` patch neutralizes `EOOEOHKLOFJ`, currency changes work without crashes!

### Want to change player level?
Change:
* `Level="52"` (Max campaign level)
* `Strength="52"`
* `Stamina="52"`

### Want to equip a different weapon?
In `<Warrior>`:
* Set `Weapon="WEAPON_KATANA"` (or any item ID from `config_cdn.xml`).
* Ensure a corresponding `<Item Name="WEAPON_KATANA" Equipped="1" Count="1" UpgradeLevel="0" />` exists inside `<Items>`.

---

## 5. Recalculating MD5 Hashes (Mandatory Step)

Whenever you edit `users.xml` or `users_backup.xml`, you **must recalculate the MD5 hashes**:

```python
import hashlib

for fname in ["users.xml", "users_backup.xml"]:
    with open(f"modding/assets/userdata/{fname}", "rb") as f:
        md5_hex = hashlib.md5(f.read()).hexdigest().upper()
    with open(f"modding/assets/userdata/{fname}.hash", "w") as f:
        f.write(md5_hex)
    print(f"Updated {fname}.hash to: {md5_hex}")
```

Then rebuild the APK:
```powershell
.venv\Scripts\python modding\pipeline\build_cat_blasters.py
```
On boot, the self-extractor deploys your modified save and matching hash directly to storage.

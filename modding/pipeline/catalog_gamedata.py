import sys
sys.stdout.reconfigure(encoding='utf-8')
import UnityPy
import xml.etree.ElementTree as ET
import json

bundle_path = 'modding/assets/downloaded_gamedata/bundles/VERSIONAL_CONFIGS'
env = UnityPy.load(bundle_path)

eng_text = ""
for obj in env.objects:
    if obj.type.name == 'TextAsset':
        data = obj.read()
        name = getattr(data, 'm_Name', getattr(data, 'name', None))
        if name == 'eng':
            raw = bytes(data.m_Script) if isinstance(data.m_Script, (bytes, bytearray)) else str(data.m_Script).encode('utf-8')
            eng_text = raw.decode('utf-8-sig', errors='ignore')

root = ET.fromstring(eng_text)
words = {}
for word in root.findall('.//Word'):
    title = word.get('Title', '')
    text = word.text or ''
    words[title] = text

print(f"Total localized strings: {len(words)}")

# 1. BOSSES & BODYGUARDS
acts = {
    "Act 1 (Hero Reborn)": {
        "Boss": ("BOSS_LYNX", words.get("BOSS_LYNX", "Lynx")),
        "Bodyguards": [
            ("Shin", words.get("Shin", "Shin")),
            ("Brick", words.get("Brick", "Brick")),
            ("Needle", words.get("Needle", "Needle")),
            ("Ghost", words.get("Ghost", "Ghost")),
            ("Dagger", words.get("Dagger", "Dagger"))
        ],
        "Zone": "ZONE_1",
        "Arena": "ARENA_TOURNAMENT_1"
    },
    "Act 2 (Secret Path)": {
        "Boss": ("BOSS_HERMIT", words.get("BOSS_HERMIT", "Hermit")),
        "Bodyguards": [
            ("Dragon", words.get("Dragon", "Dragon")),
            ("Buffalo", words.get("Buffalo", "Buffalo")),
            ("Mantis", words.get("Mantis", "Mantis")),
            ("Tiger", words.get("Tiger", "Tiger")),
            ("Crane", words.get("Crane", "Crane"))
        ],
        "Zone": "ZONE_2",
        "Arena": "ARENA_VILLAGE"
    },
    "Act 3 (Trail of Blood)": {
        "Boss": ("BOSS_BUTCHER", words.get("BOSS_BUTCHER", "Butcher")),
        "Bodyguards": [
            ("Bird", words.get("Bird", "Bird")),
            ("Rhino", words.get("Rhino", "Rhino")),
            ("Bull", words.get("Bull", "Bull")),
            ("Viper", words.get("Viper", "Viper")),
            ("Raven", words.get("Raven", "Raven"))
        ],
        "Zone": "ZONE_3",
        "Arena": "ARENA_SLAUGHTERHOUSE"
    },
    "Act 4 (Pirate Throne)": {
        "Boss": ("BOSS_WASP", words.get("BOSS_WASP", "Wasp")),
        "Bodyguards": [
            ("Kraken", words.get("Kraken", "Kraken")),
            ("Cleaver", words.get("Cleaver", "Cleaver")),
            ("Shark", words.get("Shark", "Shark")),
            ("Hawk", words.get("Hawk", "Hawk")),
            ("Whale", words.get("Whale", "Whale"))
        ],
        "Zone": "ZONE_4",
        "Arena": "ARENA_PIRATE_SHIP"
    },
    "Act 5 (Great Temptation)": {
        "Boss": ("BOSS_WIDOW", words.get("BOSS_WIDOW", "Widow")),
        "Bodyguards": [
            ("Irida", words.get("Irida", "Irida")),
            ("Fox", words.get("Fox", "Fox")),
            ("Cleo", words.get("Cleo", "Cleo")),
            ("Puma", words.get("Puma", "Puma")),
            ("Mistress", words.get("Mistress", "Mistress"))
        ],
        "Zone": "ZONE_5",
        "Arena": "ARENA_COURTYARD"
    },
    "Act 6 (Iron Reign)": {
        "Boss": ("BOSS_SHOGUN", words.get("BOSS_SHOGUN", "Shogun")),
        "Bodyguards": [
            ("Corporal", words.get("Corporal", "Corporal")),
            ("Captain", words.get("Captain", "Captain")),
            ("Major", words.get("Major", "Major")),
            ("Colonel", words.get("Colonel", "Colonel")),
            ("General", words.get("General", "General"))
        ],
        "Zone": "ZONE_6",
        "Arena": "ARENA_SHOGUN_FORTRESS"
    },
    "Act 7 (Revelation / Titan)": {
        "Boss": ("BOSS_TITAN", words.get("BOSS_TITAN", "Titan")),
        "Bodyguards": [
            ("Assassin", words.get("Assassin", "Assassin")),
            ("Master", words.get("Master", "Master")),
            ("Guru", words.get("Guru", "Guru")),
            ("Emperor", words.get("Emperor", "Emperor")),
            ("Corsair", words.get("Corsair", "Corsair"))
        ],
        "Zone": "ZONE_7",
        "Arena": "ARENA_TITAN_CORE"
    }
}

print(json.dumps(acts, indent=2))

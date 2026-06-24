"""Лут: таблицы дропа, редкость предметов, золото, генерация лута."""
import random
from dataclasses import dataclass, field
from enum import Enum


class Rarity(Enum):
    COMMON = "common"
    UNCOMMON = "uncommon"
    RARE = "rare"
    VERY_RARE = "very_rare"
    LEGENDARY = "legendary"


RARITY_COLORS = {
    Rarity.COMMON: "#ffffff",
    Rarity.UNCOMMON: "#1eff00",
    Rarity.RARE: "#0070dd",
    Rarity.VERY_RARE: "#a335ee",
    Rarity.LEGENDARY: "#ff8000",
}


@dataclass
class LootEntry:
    item_id: str
    name: str
    icon: str
    item_type: str
    rarity: Rarity = Rarity.COMMON
    drop_chance: float = 0.5
    min_amount: int = 1
    max_amount: int = 1
    properties: dict = field(default_factory=dict)
    description: str = ""
    gold_value: int = 0
    
    def to_dict(self):
        return {
            "item_id": self.item_id, "name": self.name, "icon": self.icon,
            "item_type": self.item_type, "rarity": self.rarity.value,
            "description": self.description, "gold_value": self.gold_value,
            "properties": self.properties,
        }


LOOT_TABLES = {
    "goblin": [
        LootEntry("dagger", "Кинжал", "🗡", "weapon", Rarity.COMMON, 0.3, properties={"damage": "1d4"}),
        LootEntry("gold_pouch", "Мешочек золота", "💰", "misc", Rarity.COMMON, 0.5, gold_value=10),
        LootEntry("rat_tail", "Хвост крысы", "🐀", "misc", Rarity.COMMON, 0.2, description="Предмет для квестов"),
    ],
    "skeleton": [
        LootEntry("bone_shield", "Костяной щит", "🛡", "shield", Rarity.COMMON, 0.2, properties={"ac_bonus": 2}),
        LootEntry("rusty_sword", "Ржавый меч", "⚔", "weapon", Rarity.COMMON, 0.3, properties={"damage": "1d6"}),
        LootEntry("skull", "Череп", "💀", "misc", Rarity.COMMON, 0.4, description="Может быть нужен алхимику"),
    ],
    "wolf": [
        LootEntry("wolf_pelt", "Шкура волка", "🐺", "misc", Rarity.COMMON, 0.6, gold_value=5),
        LootEntry("wolf_fang", "Клык волка", "🦷", "misc", Rarity.COMMON, 0.3, description="Ингредиент"),
    ],
    "zombie": [
        LootEntry("rotten_flesh", "Гнилая плоть", "🧟", "misc", Rarity.COMMON, 0.4, description="Отвратительно"),
    ],
    "bandit": [
        LootEntry("healing_potion", "Зелье лечения", "🧪", "potion", Rarity.COMMON, 0.3, properties={"healing": "2d4+2"}),
        LootEntry("gold_pouch", "Мешочек золота", "💰", "misc", Rarity.COMMON, 0.6, gold_value=15),
        LootEntry("bandit_map", "Карта бандитов", "🗺", "quest", Rarity.UNCOMMON, 0.1, description="Ведёт к тайнику"),
    ],
    "orc": [
        LootEntry("great_axe", "Громадный топор", "🪓", "weapon", Rarity.UNCOMMON, 0.3, properties={"damage": "1d12"}),
        LootEntry("gold_pouch", "Мешочек золота", "💰", "misc", Rarity.COMMON, 0.5, gold_value=20),
        LootEntry("orc_tusk", "Клык орка", "🦷", "misc", Rarity.COMMON, 0.4, description="Трофей"),
    ],
    "troll": [
        LootEntry("troll_hide", "Шкура тролля", "👹", "misc", Rarity.UNCOMMON, 0.5, gold_value=50),
        LootEntry("gold_chest", "Сундук с золотом", "💰", "misc", Rarity.UNCOMMON, 0.3, gold_value=50),
        LootEntry("troll_blood", "Кровь тролля", "🩸", "ingredient", Rarity.UNCOMMON, 0.2, description="Мощный ингредиент"),
    ],
    "spider": [
        LootEntry("spider_silk", "Паутина", "🕸", "ingredient", Rarity.COMMON, 0.3, description="Прочная нить"),
    ],
    "rat": [
        LootEntry("rat_tail", "Хвост крысы", "🐀", "misc", Rarity.COMMON, 0.2, gold_value=1),
    ],
    "skeleton_mage": [
        LootEntry("scroll_fireball", "Свиток Огненного шара", "📜", "quest", Rarity.UNCOMMON, 0.3, description="Заклинание 3 уровня"),
        LootEntry("magic_wand", "Волшебная палочка", "🪄", "weapon", Rarity.RARE, 0.1, properties={"damage": "1d8", "type": "force"}),
    ],
}


def roll_loot(monster_id: str, luck_bonus: int = 0) -> list[dict]:
    table = LOOT_TABLES.get(monster_id, [])
    loot = []
    
    for entry in table:
        roll = random.random() + (luck_bonus * 0.05)
        if roll <= entry.drop_chance:
            amount = random.randint(entry.min_amount, entry.max_amount)
            item = entry.to_dict()
            item["amount"] = amount
            if entry.gold_value > 0:
                item["gold"] = entry.gold_value * amount
            loot.append(item)
    
    base_gold = random.randint(1, 6) + random.randint(1, 6)
    if monster_id in ("orc", "bandit", "troll"):
        base_gold += random.randint(1, 10)
    if base_gold > 0:
        loot.append({"item_id": "gold", "name": "Золото", "icon": "💰",
                      "item_type": "misc", "rarity": "common",
                      "gold": base_gold, "amount": 1})
    
    return loot


def get_rarity_color(rarity: str) -> str:
    try:
        r = Rarity(rarity)
        return RARITY_COLORS.get(r, "#ffffff")
    except ValueError:
        return "#ffffff"


def generate_chest_loot(chest_type: str = "wooden") -> list[dict]:
    tables = {
        "wooden": [
            {"item_id": "gold_pouch", "name": "Мешочек золота", "icon": "💰", "gold": random.randint(5, 25), "rarity": "common"},
            {"item_id": "healing_potion", "name": "Зелье лечения", "icon": "🧪", "rarity": "common", "properties": {"healing": "2d4+2"}},
        ],
        "iron": [
            {"item_id": "gold_pouch", "name": "Мешочек золота", "icon": "💰", "gold": random.randint(20, 50), "rarity": "common"},
            {"item_id": "healing_potion", "name": "Зелье лечения", "icon": "🧪", "rarity": "common"},
            {"item_id": "dagger", "name": "Кинжал", "icon": "🗡", "rarity": "common", "properties": {"damage": "1d4"}},
        ],
        "golden": [
            {"item_id": "gold_chest", "name": "Золото", "icon": "💰", "gold": random.randint(50, 150), "rarity": "uncommon"},
            {"item_id": "healing_potion", "name": "Большое зелье лечения", "icon": "🧪", "rarity": "uncommon", "properties": {"healing": "4d4+4"}},
            {"item_id": "magic_ring", "name": "Волшебное кольцо", "icon": "💍", "rarity": "rare", "properties": {"ac_bonus": 1}},
        ],
    }
    return tables.get(chest_type, tables["wooden"])

"""Монстры и враги: шаблоны, спавн, лут-таблицы."""
import random
from core.combat import StatBlock, Attack, DamageType


MONSTER_TEMPLATES = {
    "goblin": {
        "name": "Гоблин",
        "hp": 7, "max_hp": 7, "ac": 15, "speed": 30, "level": 1,
        "strength": 8, "dexterity": 14, "constitution": 10,
        "intelligence": 10, "wisdom": 8, "cha": 8,
        "attacks": [
            {"name": "Кинжал", "damage_dice": "1d4+2", "damage_type": "piercing", "range": 5},
            {"name": "Лук", "damage_dice": "1d6+2", "damage_type": "piercing", "range": 80, "is_ranged": True},
        ],
        "xp": 50, "gold": "2d4",
        "loot_table": ["dagger", "gold_pouch"],
    },
    "skeleton": {
        "name": "Скелет",
        "hp": 13, "max_hp": 13, "ac": 13, "speed": 30, "level": 1,
        "strength": 10, "dexterity": 14, "constitution": 15,
        "intelligence": 6, "wisdom": 8, "cha": 5,
        "attacks": [
            {"name": "Меч", "damage_dice": "1d6+2", "damage_type": "slashing", "range": 5},
            {"name": "Лук", "damage_dice": "1d6+2", "damage_type": "piercing", "range": 80, "is_ranged": True},
        ],
        "xp": 50, "gold": "1d6",
        "loot_table": ["bone_shield", "rusty_sword"],
    },
    "wolf": {
        "name": "Волк",
        "hp": 11, "max_hp": 11, "ac": 13, "speed": 40, "level": 1,
        "strength": 12, "dexterity": 15, "constitution": 12,
        "intelligence": 3, "wisdom": 12, "cha": 6,
        "attacks": [
            {"name": "Укус", "damage_dice": "2d4+2", "damage_type": "piercing", "range": 5},
        ],
        "xp": 50, "gold": "0",
        "loot_table": ["wolf_pelt"],
    },
    "zombie": {
        "name": "Зомби",
        "hp": 22, "max_hp": 22, "ac": 8, "speed": 20, "level": 1,
        "strength": 13, "dexterity": 6, "constitution": 16,
        "intelligence": 3, "wisdom": 6, "cha": 5,
        "attacks": [
            {"name": "Удар", "damage_dice": "1d6+1", "damage_type": "bludgeoning", "range": 5},
        ],
        "xp": 50, "gold": "0",
        "loot_table": [],
    },
    "spider": {
        "name": "Паук",
        "hp": 1, "max_hp": 1, "ac": 14, "speed": 20, "level": 1,
        "strength": 2, "dexterity": 16, "constitution": 8,
        "intelligence": 1, "wisdom": 7, "cha": 2,
        "attacks": [
            {"name": "Укус", "damage_dice": "1", "damage_type": "piercing", "range": 5},
        ],
        "xp": 10, "gold": "0",
        "loot_table": [],
    },
    "rat": {
        "name": "Крыса",
        "hp": 1, "max_hp": 1, "ac": 10, "speed": 20, "level": 1,
        "strength": 2, "dexterity": 11, "constitution": 9,
        "intelligence": 2, "wisdom": 10, "cha": 4,
        "attacks": [
            {"name": "Укус", "damage_dice": "1", "damage_type": "piercing", "range": 5},
        ],
        "xp": 10, "gold": "0",
        "loot_table": [],
    },
    "bandit": {
        "name": "Бандит",
        "hp": 11, "max_hp": 11, "ac": 12, "speed": 30, "level": 1,
        "strength": 12, "dexterity": 12, "constitution": 12,
        "intelligence": 10, "wisdom": 10, "cha": 10,
        "attacks": [
            {"name": "Скимитар", "damage_dice": "1d6+1", "damage_type": "slashing", "range": 5},
            {"name": "Лёгкий арбалет", "damage_dice": "1d6+1", "damage_type": "piercing", "range": 80, "is_ranged": True},
        ],
        "xp": 50, "gold": "2d6",
        "loot_table": ["healing_potion", "gold_pouch"],
    },
    "orc": {
        "name": "Орк",
        "hp": 15, "max_hp": 15, "ac": 13, "speed": 30, "level": 1,
        "strength": 16, "dexterity": 12, "constitution": 16,
        "intelligence": 7, "wisdom": 11, "cha": 10,
        "attacks": [
            {"name": "Громадный топор", "damage_dice": "1d12+3", "damage_type": "slashing", "range": 5},
            {"name": "Копьё", "damage_dice": "1d6+3", "damage_type": "piercing", "range": 30, "is_ranged": True},
        ],
        "xp": 100, "gold": "1d6",
        "loot_table": ["great_axe", "gold_pouch"],
    },
    "troll": {
        "name": "Тролль",
        "hp": 63, "max_hp": 63, "ac": 15, "speed": 30, "level": 5,
        "strength": 18, "dexterity": 13, "constitution": 17,
        "intelligence": 7, "wisdom": 9, "cha": 7,
        "attacks": [
            {"name": "Когти", "damage_dice": "2d6+4", "damage_type": "slashing", "range": 5},
            {"name": "Укус", "damage_dice": "1d8+4", "damage_type": "piercing", "range": 5},
        ],
        "xp": 700, "gold": "3d6",
        "loot_table": ["troll_hide", "gold_chest"],
    },
    "skeleton_mage": {
        "name": "Скелет-маг",
        "hp": 16, "max_hp": 16, "ac": 12, "speed": 30, "level": 2,
        "strength": 8, "dexterity": 14, "constitution": 12,
        "intelligence": 16, "wisdom": 14, "cha": 10,
        "attacks": [
            {"name": "Посох", "damage_dice": "1d6", "damage_type": "bludgeoning", "range": 5},
            {"name": "Огненный снаряд", "damage_dice": "2d6", "damage_type": "fire", "range": 120, "is_ranged": True},
        ],
        "xp": 100, "gold": "1d10",
        "loot_table": ["scroll_fireball", "gold_pouch"],
    },
}

LOCATION_ENCOUNTERS = {
    "forest": [
        {"monsters": ["wolf", "wolf"], "chance": 0.3},
        {"monsters": ["spider", "spider", "spider"], "chance": 0.2},
        {"monsters": ["goblin", "goblin"], "chance": 0.25},
    ],
    "cave": [
        {"monsters": ["skeleton"], "chance": 0.3},
        {"monsters": ["rat", "rat", "rat"], "chance": 0.3},
        {"monsters": ["goblin"], "chance": 0.2},
        {"monsters": ["skeleton_mage"], "chance": 0.1},
    ],
    "ruins": [
        {"monsters": ["skeleton", "skeleton"], "chance": 0.3},
        {"monsters": ["zombie"], "chance": 0.25},
        {"monsters": ["skeleton_mage"], "chance": 0.15},
    ],
    "swamp": [
        {"monsters": ["rat", "rat"], "chance": 0.3},
        {"monsters": ["spider", "spider"], "chance": 0.25},
        {"monsters": ["zombie"], "chance": 0.2},
    ],
    "mountain": [
        {"monsters": ["orc"], "chance": 0.2},
        {"monsters": ["bandit", "bandit"], "chance": 0.25},
        {"monsters": ["wolf", "wolf", "wolf"], "chance": 0.15},
    ],
    "crossroads": [
        {"monsters": ["bandit"], "chance": 0.3},
        {"monsters": ["goblin", "goblin"], "chance": 0.2},
    ],
    "village": [],
    "lake": [
        {"monsters": ["spider"], "chance": 0.1},
    ],
}

LOOT_TABLES = {
    "dagger": {"name": "Кинжал", "icon": "🗡", "item_type": "weapon", "damage": "1d4", "weight": 1},
    "rusty_sword": {"name": "Ржавый меч", "icon": "⚔", "item_type": "weapon", "damage": "1d6", "weight": 3},
    "great_axe": {"name": "Громадный топор", "icon": "🪓", "item_type": "weapon", "damage": "1d12", "weight": 7},
    "bone_shield": {"name": "Костяной щит", "icon": "🛡", "item_type": "shield", "ac_bonus": 2, "weight": 6},
    "healing_potion": {"name": "Зелье лечения", "icon": "🧪", "item_type": "potion", "healing": "2d4+2", "weight": 0.5},
    "gold_pouch": {"name": "Мешочек золота", "icon": "💰", "item_type": "misc", "gold": "2d6", "weight": 0.1},
    "gold_chest": {"name": "Сундук с золотом", "icon": "💰", "item_type": "misc", "gold": "4d6", "weight": 5},
    "wolf_pelt": {"name": "Шкура волка", "icon": "🐺", "item_type": "misc", "weight": 2},
    "troll_hide": {"name": "Шкура тролля", "icon": "👹", "item_type": "misc", "weight": 10},
    "scroll_fireball": {"name": "Свиток Огненного шара", "icon": "📜", "item_type": "quest", "weight": 0.1},
}


def spawn_monster(template_id: str, level_mod: int = 0) -> StatBlock:
    tmpl = MONSTER_TEMPLATES.get(template_id)
    if not tmpl:
        return StatBlock(name="???")
    
    sb = StatBlock(
        name=tmpl["name"],
        hp=tmpl["hp"], max_hp=tmpl["max_hp"],
        ac=tmpl["ac"], speed=tmpl["speed"],
        level=tmpl.get("level", 1) + level_mod,
        strength=tmpl["strength"], dexterity=tmpl["dexterity"],
        constitution=tmpl["constitution"], intelligence=tmpl["intelligence"],
        wisdom=tmpl["wisdom"], charisma=tmpl.get("cha", 10),
    )
    
    for atk_d in tmpl.get("attacks", []):
        sb.attacks.append(Attack(
            name=atk_d["name"],
            damage_dice=atk_d["damage_dice"],
            damage_type=DamageType(atk_d.get("damage_type", "slashing")),
            range=atk_d.get("range", 5),
            is_ranged=atk_d.get("is_ranged", False),
        ))
    
    return sb


def roll_loot(template_id: str) -> list[dict]:
    tmpl = MONSTER_TEMPLATES.get(template_id, {})
    loot = []
    
    gold_dice = tmpl.get("gold", "0")
    if gold_dice and gold_dice != "0":
        gold = roll_dice(gold_dice)
        if gold > 0:
            loot.append({"type": "gold", "amount": gold})
    
    for item_id in tmpl.get("loot_table", []):
        if random.random() < 0.5:
            item = LOOT_TABLES.get(item_id)
            if item:
                loot.append({"type": "item", "item_id": item_id, **item})
    
    return loot


def roll_dice(expr: str) -> int:
    expr = expr.strip().lower().replace(" ", "")
    total = 0
    parts = []
    current = ""
    for ch in expr:
        if ch in "+-" and current:
            parts.append(current)
            current = ch
        else:
            current += ch
    if current:
        parts.append(current)
    
    for part in parts:
        if "d" in part:
            num_str, sides_str = part.split("d", 1)
            num = int(num_str) if num_str and num_str != "-" else 1
            if "+" in sides_str:
                sides, bonus = sides_str.split("+", 1)
                total += num * random.randint(1, int(sides)) + int(bonus)
            elif "-" in sides_str:
                sides, bonus = sides_str.split("-", 1)
                total += num * random.randint(1, int(sides)) - int(bonus)
            else:
                total += num * random.randint(1, int(sides_str))
        else:
            total += int(part)
    
    return max(0, total)


def get_encounter(location_id: str) -> list[dict]:
    encounters = LOCATION_ENCOUNTERS.get(location_id, [])
    if not encounters:
        return []
    
    roll = random.random()
    cumulative = 0
    for enc in encounters:
        cumulative += enc["chance"]
        if roll <= cumulative:
            return enc["monsters"]
    
    return encounters[-1]["monsters"] if encounters else []

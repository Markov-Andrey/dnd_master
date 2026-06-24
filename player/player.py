"""Игрок: D&D 5e атрибуты, навыки, броски d20, инвентарь, HP, XP, уровень."""
import json, os, random
from dataclasses import dataclass, field
from core.config import PLAYERS_DB_DIR
from player.inventory import Inventory

ATTRS = ["str", "dex", "con", "int", "wis", "cha"]
ATTR_NAMES = {"str": "Сила", "dex": "Ловкость", "con": "Телосложение",
              "int": "Интеллект", "wis": "Мудрость", "cha": "Харизма"}

SKILL_ATTR = {
    "athletics": "str", "acrobatics": "dex", "sleight_of_hand": "dex", "stealth": "dex",
    "arcana": "int", "history": "int", "investigation": "int", "nature": "int", "religion": "int",
    "animal_handling": "wis", "insight": "wis", "medicine": "wis", "perception": "wis", "survival": "wis",
    "deception": "cha", "intimidation": "cha", "performance": "cha", "persuasion": "cha",
}

SKILL_NAMES = {
    "athletics": "Атлетика", "acrobatics": "Акробатика", "sleight_of_hand": "Ловкость рук",
    "stealth": "Скрытность", "arcana": "Магия", "history": "История",
    "investigation": "Расследование", "nature": "Природа", "religion": "Религия",
    "animal_handling": "Уход за животными", "insight": "Проницательность", "medicine": "Медицина",
    "perception": "Восприятие", "survival": "Выживание", "deception": "Обман",
    "intimidation": "Запугивание", "performance": "Выступление", "persuasion": "Убеждение",
}

DEFAULT_ATTRS = {a: 10 for a in ATTRS}

HIT_DICE_BY_LEVEL = {
    1: 10, 2: 20, 3: 30, 4: 40, 5: 55,
    6: 65, 7: 75, 8: 90, 9: 100, 10: 115,
}

XP_BY_LEVEL = {
    1: 0, 2: 300, 3: 900, 4: 2700, 5: 6500,
    6: 14000, 7: 23000, 8: 34000, 9: 48000, 10: 64000,
}


def _mod(score): return (score - 10) // 2


def calc_max_hp(level: int, con_mod: int) -> int:
    base = 10 + con_mod
    for lvl in range(2, level + 1):
        base += random.randint(1, 10) + con_mod
    return max(1, base)


@dataclass
class Player:
    name: str = "Герой"
    level: int = 1
    xp: int = 0
    hp: int = 20
    max_hp: int = 20
    gold: int = 50
    attributes: dict = field(default_factory=lambda: dict(DEFAULT_ATTRS))
    proficiency_bonus: int = 2
    proficiencies: list = field(default_factory=list)
    inventory: Inventory = field(default_factory=Inventory)
    hit_dice: int = 1
    hit_dice_max: int = 1
    death_saves: int = 0
    death_fails: int = 0
    exhaustion: int = 0
    conditions: list = field(default_factory=list)
    location_id: str = "village"
    quest_progress: dict = field(default_factory=dict)

    def get_modifier(self, attr): return _mod(self.attributes.get(attr, 10))

    def get_skill_modifier(self, skill):
        mod = self.get_modifier(SKILL_ATTR.get(skill, "str"))
        return mod + self.proficiency_bonus if skill in self.proficiencies else mod

    def get_ac(self) -> int:
        base = 10 + self.get_modifier("dex")
        shield = self.inventory.equipment.get("shield")
        if shield:
            base += shield.properties.get("ac_bonus", 0)
        chest = self.inventory.equipment.get("chest")
        if chest:
            base += chest.properties.get("ac_bonus", 0)
        return base

    def take_damage(self, amount: int) -> int:
        actual = min(amount, self.hp)
        self.hp -= actual
        return actual

    def heal(self, amount: int) -> int:
        actual = min(amount, self.max_hp - self.hp)
        self.hp += actual
        return actual

    def is_alive(self) -> bool:
        return self.hp > 0

    def gain_xp(self, amount: int) -> dict:
        self.xp += amount
        leveled_up = False
        while self.level < 10 and self.xp >= XP_BY_LEVEL.get(self.level + 1, 999999):
            self.level += 1
            leveled_up = True
            con_mod = self.get_modifier("con")
            hp_gain = random.randint(1, 10) + con_mod
            self.max_hp += max(1, hp_gain)
            self.hp = self.max_hp
            self.hit_dice += 1
            self.hit_dice_max += 1
            self.proficiency_bonus = 2 + (self.level - 1) // 4
        return {
            "xp_gained": amount,
            "total_xp": self.xp,
            "leveled_up": leveled_up,
            "new_level": self.level if leveled_up else None,
        }

    def level_up(self):
        self.level += 1
        con_mod = self.get_modifier("con")
        hp_gain = random.randint(1, 10) + con_mod
        self.max_hp += max(1, hp_gain)
        self.hp = self.max_hp
        self.hit_dice += 1
        self.hit_dice_max += 1
        self.proficiency_bonus = 2 + (self.level - 1) // 4

    def short_rest_heal(self) -> int:
        if self.hit_dice <= 0:
            return 0
        roll = random.randint(1, 8)
        con_mod = self.get_modifier("con")
        healed = max(0, roll + con_mod)
        self.hit_dice -= 1
        self.heal(healed)
        return healed

    def to_dict(self):
        d = {
            "name": self.name, "level": self.level, "xp": self.xp,
            "hp": self.hp, "max_hp": self.max_hp, "gold": self.gold,
            "attributes": self.attributes, "proficiency_bonus": self.proficiency_bonus,
            "proficiencies": self.proficiencies,
            "hit_dice": self.hit_dice, "hit_dice_max": self.hit_dice_max,
            "exhaustion": self.exhaustion, "conditions": self.conditions,
            "location_id": self.location_id,
            "modifiers": {a: self.get_modifier(a) for a in ATTRS},
            "ac": self.get_ac(),
            "xp_to_next": XP_BY_LEVEL.get(self.level + 1, 999999),
        }
        d["inventory"] = self.inventory.to_dict()
        return d

    def save(self):
        os.makedirs(PLAYERS_DB_DIR, exist_ok=True)
        path = os.path.join(PLAYERS_DB_DIR, f"{self.name.lower().replace(' ', '_')}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, name="hero"):
        path = os.path.join(PLAYERS_DB_DIR, f"{name}.json")
        if not os.path.exists(path):
            files = [f for f in os.listdir(PLAYERS_DB_DIR) if f.endswith(".json")] if os.path.exists(PLAYERS_DB_DIR) else []
            if files:
                path = os.path.join(PLAYERS_DB_DIR, files[0])
            else:
                return cls()
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        inv_data = data.pop("inventory", {})
        inv = Inventory(equipment=inv_data.get("equipment"), backpack=inv_data.get("backpack"))
        return cls(
            name=data.get("name", "Герой"),
            level=data.get("level", 1),
            xp=data.get("xp", 0),
            hp=data.get("hp", 20),
            max_hp=data.get("max_hp", 20),
            gold=data.get("gold", 50),
            attributes=data.get("attributes", dict(DEFAULT_ATTRS)),
            proficiency_bonus=data.get("proficiency_bonus", 2),
            proficiencies=data.get("proficiencies", []),
            inventory=inv,
            hit_dice=data.get("hit_dice", 1),
            hit_dice_max=data.get("hit_dice_max", 1),
            exhaustion=data.get("exhaustion", 0),
            conditions=data.get("conditions", []),
            location_id=data.get("location_id", "village"),
        )

    @classmethod
    def create(cls, name: str, attrs: dict) -> "Player":
        con_mod = _mod(attrs.get("con", 10))
        max_hp = 10 + con_mod
        return cls(
            name=name,
            level=1,
            hp=max_hp,
            max_hp=max_hp,
            gold=50,
            attributes=attrs,
            hit_dice=1,
            hit_dice_max=1,
        )


def make_skill_check(player, skill, situation):
    roll = random.randint(1, 20)
    mod = player.get_skill_modifier(skill)
    return {
        "skill": skill, "skill_name": SKILL_NAMES.get(skill, skill),
        "attribute": SKILL_ATTR.get(skill, "str"),
        "attribute_name": ATTR_NAMES.get(SKILL_ATTR.get(skill, "str"), ""),
        "modifier": mod, "roll": roll, "total": roll + mod,
        "nat20": roll == 20, "nat1": roll == 1, "situation": situation,
    }

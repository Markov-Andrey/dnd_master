from dataclasses import dataclass, field
from typing import Optional
import uuid


ITEM_TYPES = ["weapon", "armor", "potion", "food", "key", "misc", "book", "spell_scroll"]
WEAPON_SUBTYPES = ["blade", "blunt", "bow"]
ARMOR_SLOTS = ["head", "chest", "legs", "hands", "feet", "ring"]


@dataclass
class Item:
    name: str
    item_type: str
    weight: float = 1.0
    value: int = 1
    description: str = ""
    uid: str = field(default_factory=lambda: str(uuid.uuid4())[:8])

    # weapon fields
    damage_min: int = 0
    damage_max: int = 0
    weapon_skill: str = ""
    weapon_subtype: str = ""

    # armor fields
    defense: int = 0
    slot: str = ""

    # durability
    durability: int = 100
    durability_max: int = 100

    # consumable
    hp_restore: int = 0
    mana_restore: int = 0
    stamina_restore: int = 0

    # magic affix
    affix: Optional[dict] = None

    @property
    def is_broken(self) -> bool:
        return self.durability <= 0

    def use_durability(self, amount: int = 1):
        self.durability = max(0, self.durability - amount)

    def repair(self, amount: int = 100):
        self.durability = min(self.durability_max, self.durability + amount)

    def to_dict(self) -> dict:
        return self.__dict__

    @classmethod
    def from_dict(cls, data: dict) -> "Item":
        return cls(**data)


def make_weapon(name: str, subtype: str, dmg_min: int, dmg_max: int,
                weight: float, value: int, affix: dict = None) -> Item:
    skill = subtype if subtype in ("blade", "blunt") else "archery"
    return Item(
        name=name, item_type="weapon", weight=weight, value=value,
        damage_min=dmg_min, damage_max=dmg_max,
        weapon_skill=skill, weapon_subtype=subtype,
        affix=affix,
    )


def make_armor(name: str, slot: str, defense: int, weight: float, value: int) -> Item:
    return Item(
        name=name, item_type="armor", weight=weight, value=value,
        defense=defense, slot=slot,
    )


def make_potion(name: str, hp: int = 0, mana: int = 0, stamina: int = 0,
                weight: float = 0.5, value: int = 10) -> Item:
    return Item(
        name=name, item_type="potion", weight=weight, value=value,
        hp_restore=hp, mana_restore=mana, stamina_restore=stamina,
    )

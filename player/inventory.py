"""Инвентарь игрока: предметы, экипировка, стаки, слоты."""
import json, os, uuid
from dataclasses import dataclass, field, asdict
from core.config import PLAYERS_DB_DIR


# Типы предметов → слоты экипировки (None = только рюкзак)
ITEM_TYPES = {
    "weapon": "weapon", "shield": "shield", "helmet": "head",
    "armor": "chest", "boots": "feet", "gloves": "hands",
    "ring": "ring", "amulet": "neck", "potion": None,
    "ingredient": None, "quest": None, "misc": None,
}

EQUIP_SLOTS = ["head", "chest", "hands", "feet", "weapon", "shield", "ring", "neck"]

DEFAULT_MAX_STACK = 99


@dataclass
class Item:
    id: str = ""
    name: str = "Предмет"
    description: str = ""
    properties: dict = field(default_factory=dict)  # {"damage": "1d6", "weight": 1.5, ...}
    icon: str = "?"  # эмодзи или unicode
    item_type: str = "misc"  # weapon, armor, potion, ingredient, quest, misc
    stack_size: int = 1
    max_stack: int = DEFAULT_MAX_STACK

    def __post_init__(self):
        if not self.id: self.id = f"item_{uuid.uuid4().hex[:8]}"
        self.max_stack = self.max_stack or DEFAULT_MAX_STACK

    def to_dict(self): return asdict(self)

    @classmethod
    def from_dict(cls, d): return cls(**{k: d[k] for k in d if k in cls.__dataclass_fields__})

    def can_stack(self): return self.stack_size < self.max_stack
    def is_equipable(self): return self.item_type in ITEM_TYPES and ITEM_TYPES[self.item_type] is not None
    def equip_slot(self): return ITEM_TYPES.get(self.item_type)


class Inventory:
    def __init__(self, equipment=None, backpack=None):
        self.equipment: dict[str, Item | None] = {s: None for s in EQUIP_SLOTS}
        self.backpack: list[Item | None] = [None] * 20  # 20 слотов рюкзака
        if equipment:
            for slot, item_d in equipment.items():
                if item_d and slot in self.equipment:
                    self.equipment[slot] = Item.from_dict(item_d) if isinstance(item_d, dict) else None
        if backpack:
            for i, item_d in enumerate(backpack):
                if item_d and i < len(self.backpack):
                    self.backpack[i] = Item.from_dict(item_d) if isinstance(item_d, dict) else None

    def to_dict(self):
        return {
            "equipment": {s: item.to_dict() if item else None for s, item in self.equipment.items()},
            "backpack": [item.to_dict() if item else None for item in self.backpack],
        }

    def find_item(self, item_id):
        for slot, item in self.equipment.items():
            if item and item.id == item_id: return "equipment", slot, item
        for i, item in enumerate(self.backpack):
            if item and item.id == item_id: return "backpack", i, item
        return None, None, None

    def add_item(self, item):
        """Добавить в рюкзак. Сначала стакуем, потом ищем пустой слот."""
        if item.max_stack > 1:
            for i, slot_item in enumerate(self.backpack):
                if slot_item and slot_item.id == item.id and slot_item.can_stack():
                    space = slot_item.max_stack - slot_item.stack_size
                    take = min(space, item.stack_size)
                    slot_item.stack_size += take
                    item.stack_size -= take
                    if item.stack_size <= 0: return True
        for i, slot_item in enumerate(self.backpack):
            if slot_item is None:
                self.backpack[i] = item
                return True
        return False  # рюкзак полон

    def remove_item(self, item_id):
        for i, item in enumerate(self.backpack):
            if item and item.id == item_id:
                self.backpack[i] = None
                return item
        return None

    def equip(self, item_id):
        """Экипировать из рюкзака. Возвращаем старый предмет (если был)."""
        loc, idx, item = self.find_item(item_id)
        if loc != "backpack": return None, "Предмет не в рюкзаке"
        if not item.is_equipable(): return None, "Нельзя экипировать"
        slot = item.equip_slot()
        old = self.equipment[slot]
        self.equipment[slot] = item
        self.backpack[idx] = old  # старый предмет идёт в рюкзак
        return item, None

    def unequip(self, slot):
        """Снять в рюкзак."""
        item = self.equipment.get(slot)
        if not item: return None, "Слот пуст"
        if not self.add_item(item): return None, "Рюкзак полон"
        self.equipment[slot] = None
        return item, None

    def find_free_slot(self):
        for i, item in enumerate(self.backpack):
            if item is None: return i
        return -1

    def find_free_slots(self):
        return [i for i, item in enumerate(self.backpack) if item is None]

    def total_weight(self):
        return sum(
            (item.properties.get("weight", 1) * item.stack_size)
            for items in [self.backpack, list(self.equipment.values())]
            for item in items if item
        )

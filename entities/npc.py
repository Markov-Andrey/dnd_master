from dataclasses import dataclass, field
from entities.character import Character
from typing import Optional
import random


NPC_TYPES = ["merchant", "guard", "villager", "quest_giver", "enemy", "innkeeper"]


@dataclass
class NPC(Character):
    npc_type: str = "villager"
    location_id: str = ""
    dialogue_topics: list = field(default_factory=list)
    shop_inventory: list = field(default_factory=list)
    is_hostile: bool = False
    loot_table: list = field(default_factory=list)
    quest_ids: list = field(default_factory=list)

    def __post_init__(self):
        super().__post_init__()
        if self.npc_type == "enemy":
            self.is_hostile = True

    def greet(self) -> str:
        greetings = {
            "merchant": f"Welcome! I am {self.name}. Browse my wares.",
            "guard": f"Halt. State your business, traveller.",
            "villager": f"Good day to you, stranger.",
            "quest_giver": f"Ah, you look capable. I have a job for you.",
            "innkeeper": f"Welcome to my inn! A room for the night?",
            "enemy": f"{self.name} attacks!",
        }
        return greetings.get(self.npc_type, f"{self.name} eyes you warily.")

    def get_dialogue_options(self) -> list[str]:
        base = ["Farewell"]
        if self.npc_type == "merchant":
            base = ["Buy", "Sell", "Farewell"]
        elif self.npc_type == "quest_giver" and self.quest_ids:
            base = ["What work do you have?", "Farewell"]
        elif self.npc_type == "innkeeper":
            base = ["Rent a room (5 gold)", "Farewell"]
        base += self.dialogue_topics
        return base

    def drop_loot(self) -> list:
        drops = []
        for entry in self.loot_table:
            if random.random() < entry.get("chance", 1.0):
                drops.append(entry["item"])
        return drops

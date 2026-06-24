"""Локация: данные, NPC, переходы."""
import json, os
from core.config import LOCATIONS_DATA_DIR


class Location:
    def __init__(self, **kw):
        self.id = kw.get("id", "unknown")
        self.name = kw.get("name", "Неизвестно")
        self.description = kw.get("description", "")
        self.tile_color = kw.get("tile_color", "#808080")
        self.npc_ids = kw.get("npc_ids", [])
        self.exits = kw.get("exits", {})
        self.actions = kw.get("actions", [])
        self.visited = kw.get("visited", False)
        self.local_map = kw.get("local_map", None)

    def to_dict(self):
        d = {
            "id": self.id, "name": self.name, "description": self.description,
            "tile_color": self.tile_color, "npc_ids": self.npc_ids,
            "exits": self.exits, "actions": self.actions, "visited": self.visited,
        }
        if self.local_map:
            d["local_map"] = self.local_map
        return d

    def save(self):
        os.makedirs(LOCATIONS_DATA_DIR, exist_ok=True)
        path = os.path.join(LOCATIONS_DATA_DIR, f"{self.id}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, location_id: str) -> "Location | None":
        path = os.path.join(LOCATIONS_DATA_DIR, f"{location_id}.json")
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls(**data)

    @classmethod
    def load_all(cls) -> dict[str, "Location"]:
        if not os.path.exists(LOCATIONS_DATA_DIR):
            return {}
        return {
            loc.id: loc
            for f in os.listdir(LOCATIONS_DATA_DIR)
            if f.endswith(".json")
            if (loc := cls.load(f[:-5])) is not None
        }

    def can_go(self, direction: str) -> bool:
        return direction in self.exits

    def get_exit(self, direction: str) -> str | None:
        return self.exits.get(direction)

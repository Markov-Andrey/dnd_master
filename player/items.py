from dataclasses import dataclass, field


@dataclass
class Item:
    id: str
    name: str
    tags: list[str] = field(default_factory=list)
    description: str = ""
    quest_item: bool = False


class InventoryStub:
    def __init__(self):
        self.items: dict[str, Item] = {}

    def add_item(self, item: Item):
        self.items[item.id] = item

    def has_item(self, item_id: str) -> bool:
        return item_id in self.items

    def has_item_matching_tags(self, required_tags: list[str]) -> Item | None:
        for item in self.items.values():
            if any(tag in item.tags for tag in required_tags):
                return item
        return None

    def get_item(self, item_id: str) -> Item | None:
        return self.items.get(item_id)


inventory = InventoryStub()


def validate_item_give(player_item_id: str, required_tags: list[str]) -> dict:
    if not inventory.has_item(player_item_id):
        return {"valid": False, "reason": "item_not_owned"}
    item = inventory.get_item(player_item_id)
    if any(tag in item.tags for tag in required_tags):
        return {"valid": True, "item": item}
    return {"valid": False, "reason": "wrong_item"}


def check_item_match(player_item_id: str | None, npc_expected_tags: list[str]) -> dict:
    if not player_item_id:
        return {"attached": False, "deception": False}
    result = validate_item_give(player_item_id, npc_expected_tags)
    if result["valid"]:
        return {"attached": True, "deception": False, "item": result["item"]}
    return {"attached": True, "deception": True, "reason": result["reason"]}

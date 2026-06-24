"""Система иконок предметов: JSON конфиг с URL картинок, фреймы, превью."""
import json
import os
from dataclasses import dataclass, field


@dataclass
class ItemIcon:
    item_id: str
    thumb_url: str = ""
    preview_url: str = ""
    frame_color: str = "#555555"
    frame_rarity: str = "common"
    category: str = "misc"

    def to_dict(self):
        return {
            "item_id": self.item_id,
            "thumb_url": self.thumb_url,
            "preview_url": self.preview_url,
            "frame_color": self.frame_color,
            "frame_rarity": self.frame_rarity,
            "category": self.category,
        }


RARITY_FRAMES = {
    "common": {"color": "#9e9e9e", "border": "2px solid #9e9e9e", "glow": "none"},
    "uncommon": {"color": "#4caf50", "border": "2px solid #4caf50", "glow": "0 0 6px #4caf5040"},
    "rare": {"color": "#2196f3", "border": "2px solid #2196f3", "glow": "0 0 8px #2196f340"},
    "very_rare": {"color": "#9c27b0", "border": "2px solid #9c27b0", "glow": "0 0 10px #9c27b040"},
    "legendary": {"color": "#ff9800", "border": "2px solid #ff9800", "glow": "0 0 12px #ff980060"},
}

CATEGORY_ICONS = {
    "weapon": "⚔", "armor": "🛡", "shield": "🛡", "potion": "🧪",
    "helmet": "⛑", "boots": "👢", "gloves": "🧤", "ring": "💍",
    "amulet": "📿", "scroll": "📜", "food": "🍖", "water": "💧",
    "misc": "📦", "ingredient": "🌿", "quest": "⭐", "gold": "💰",
}


DEFAULT_ICONS_DB = {
    "dagger": {"thumb": "/static/icons/dagger_thumb.png", "preview": "/static/icons/dagger.png", "frame": "common", "cat": "weapon"},
    "short_sword": {"thumb": "/static/icons/short_sword_thumb.png", "preview": "/static/icons/short_sword.png", "frame": "common", "cat": "weapon"},
    "longsword": {"thumb": "/static/icons/longsword_thumb.png", "preview": "/static/icons/longsword.png", "frame": "uncommon", "cat": "weapon"},
    "greatsword": {"thumb": "/static/icons/greatsword_thumb.png", "preview": "/static/icons/greatsword.png", "frame": "rare", "cat": "weapon"},
    "battleaxe": {"thumb": "/static/icons/battleaxe_thumb.png", "preview": "/static/icons/battleaxe.png", "frame": "uncommon", "cat": "weapon"},
    "spear": {"thumb": "/static/icons/spear_thumb.png", "preview": "/static/icons/spear.png", "frame": "common", "cat": "weapon"},
    "light_crossbow": {"thumb": "/static/icons/crossbow_thumb.png", "preview": "/static/icons/crossbow.png", "frame": "uncommon", "cat": "weapon"},
    "shield": {"thumb": "/static/icons/shield_thumb.png", "preview": "/static/icons/shield.png", "frame": "common", "cat": "shield"},
    "bone_shield": {"thumb": "/static/icons/bone_shield_thumb.png", "preview": "/static/icons/bone_shield.png", "frame": "uncommon", "cat": "shield"},
    "leather": {"thumb": "/static/icons/leather_armor_thumb.png", "preview": "/static/icons/leather_armor.png", "frame": "common", "cat": "armor"},
    "chain_shirt": {"thumb": "/static/icons/chain_shirt_thumb.png", "preview": "/static/icons/chain_shirt.png", "frame": "uncommon", "cat": "armor"},
    "helmet": {"thumb": "/static/icons/helmet_thumb.png", "preview": "/static/icons/helmet.png", "frame": "common", "cat": "helmet"},
    "boots": {"thumb": "/static/icons/boots_thumb.png", "preview": "/static/icons/boots.png", "frame": "common", "cat": "boots"},
    "gauntlets": {"thumb": "/static/icons/gauntlets_thumb.png", "preview": "/static/icons/gauntlets.png", "frame": "common", "cat": "gloves"},
    "healing_potion": {"thumb": "/static/icons/healing_potion_thumb.png", "preview": "/static/icons/healing_potion.png", "frame": "common", "cat": "potion"},
    "greater_healing": {"thumb": "/static/icons/greater_healing_thumb.png", "preview": "/static/icons/greater_healing.png", "frame": "uncommon", "cat": "potion"},
    "antidote": {"thumb": "/static/icons/antidote_thumb.png", "preview": "/static/icons/antidote.png", "frame": "uncommon", "cat": "potion"},
    "torch": {"thumb": "/static/icons/torch_thumb.png", "preview": "/static/icons/torch.png", "frame": "common", "cat": "misc"},
    "rope": {"thumb": "/static/icons/rope_thumb.png", "preview": "/static/icons/rope.png", "frame": "common", "cat": "misc"},
    "rations": {"thumb": "/static/icons/rations_thumb.png", "preview": "/static/icons/rations.png", "frame": "common", "cat": "food"},
    "waterskin": {"thumb": "/static/icons/waterskin_thumb.png", "preview": "/static/icons/waterskin.png", "frame": "common", "cat": "water"},
    "backpack": {"thumb": "/static/icons/backpack_thumb.png", "preview": "/static/icons/backpack.png", "frame": "common", "cat": "misc"},
    "wolf_pelt": {"thumb": "/static/icons/wolf_pelt_thumb.png", "preview": "/static/icons/wolf_pelt.png", "frame": "common", "cat": "ingredient"},
    "troll_hide": {"thumb": "/static/icons/troll_hide_thumb.png", "preview": "/static/icons/troll_hide.png", "frame": "uncommon", "cat": "ingredient"},
    "scroll_fireball": {"thumb": "/static/icons/scroll_thumb.png", "preview": "/static/icons/scroll.png", "frame": "rare", "cat": "scroll"},
    "magic_ring": {"thumb": "/static/icons/ring_thumb.png", "preview": "/static/icons/ring.png", "frame": "rare", "cat": "ring"},
    "acid_flask": {"thumb": "/static/icons/acid_thumb.png", "preview": "/static/icons/acid.png", "frame": "uncommon", "cat": "potion"},
    "oil_flask": {"thumb": "/static/icons/oil_thumb.png", "preview": "/static/icons/oil.png", "frame": "common", "cat": "misc"},
    "smokestick": {"thumb": "/static/icons/smokestick_thumb.png", "preview": "/static/icons/smokestick.png", "frame": "common", "cat": "misc"},
}


class IconDB:
    def __init__(self, path: str = "data/icons.json"):
        self.path = path
        self.icons: dict[str, ItemIcon] = {}
        self._load()

    def _load(self):
        if os.path.exists(self.path):
            try:
                with open(self.path, encoding="utf-8") as f:
                    data = json.load(f)
                for item_id, icon_d in data.items():
                    self.icons[item_id] = ItemIcon(
                        item_id=item_id,
                        thumb_url=icon_d.get("thumb", ""),
                        preview_url=icon_d.get("preview", ""),
                        frame_color=RARITY_FRAMES.get(icon_d.get("frame", "common"), {}).get("color", "#555"),
                        frame_rarity=icon_d.get("frame", "common"),
                        category=icon_d.get("cat", "misc"),
                    )
            except Exception:
                pass

        for item_id, icon_d in DEFAULT_ICONS_DB.items():
            if item_id not in self.icons:
                self.icons[item_id] = ItemIcon(
                    item_id=item_id,
                    thumb_url=icon_d.get("thumb", ""),
                    preview_url=icon_d.get("preview", ""),
                    frame_color=RARITY_FRAMES.get(icon_d.get("frame", "common"), {}).get("color", "#555"),
                    frame_rarity=icon_d.get("frame", "common"),
                    category=icon_d.get("cat", "misc"),
                )

    def save(self):
        os.makedirs(os.path.dirname(self.path) or ".", exist_ok=True)
        data = {}
        for item_id, icon in self.icons.items():
            data[item_id] = icon.to_dict()
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def get(self, item_id: str) -> ItemIcon | None:
        return self.icons.get(item_id)

    def get_frame_css(self, item_id: str) -> dict:
        icon = self.icons.get(item_id)
        rarity = icon.frame_rarity if icon else "common"
        return RARITY_FRAMES.get(rarity, RARITY_FRAMES["common"])

    def get_all(self) -> list[dict]:
        return [icon.to_dict() for icon in self.icons.values()]

    def update(self, item_id: str, **kwargs):
        if item_id in self.icons:
            icon = self.icons[item_id]
            for k, v in kwargs.items():
                if hasattr(icon, k):
                    setattr(icon, k, v)

    def add(self, item_id: str, thumb: str = "", preview: str = "", frame: str = "common", cat: str = "misc"):
        self.icons[item_id] = ItemIcon(
            item_id=item_id,
            thumb_url=thumb,
            preview_url=preview,
            frame_color=RARITY_FRAMES.get(frame, {}).get("color", "#555"),
            frame_rarity=frame,
            category=cat,
        )

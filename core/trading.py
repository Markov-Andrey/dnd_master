"""Торговля: золото, магазины NPC, продажа/покупка, цены."""
import random
from dataclasses import dataclass, field
from player.inventory import Item, Inventory


@dataclass
class ShopItem:
    item_id: str
    name: str
    icon: str
    item_type: str
    description: str = ""
    buy_price: int = 10
    sell_price: int = 5
    stock: int = -1  # -1 = бесконечно
    properties: dict = field(default_factory=dict)
    
    def to_dict(self):
        return {
            "item_id": self.item_id, "name": self.name, "icon": self.icon,
            "item_type": self.item_type, "description": self.description,
            "buy_price": self.buy_price, "sell_price": self.sell_price,
            "stock": self.stock, "properties": self.properties,
        }


@dataclass
class Shop:
    name: str
    shopkeeper: str
    shop_type: str  # general, weapon, armor, alchemy
    inventory: list[ShopItem] = field(default_factory=list)
    buy_multiplier: float = 0.5
    sell_multiplier: float = 1.5
    
    def get_buy_price(self, item: ShopItem) -> int:
        return int(item.sell_price * self.buy_multiplier)
    
    def get_sell_price(self, item: ShopItem) -> int:
        return int(item.buy_price * self.sell_multiplier)
    
    def buy_item(self, player_gold: int, item: ShopItem) -> tuple[bool, int, str]:
        price = self.get_buy_price(item)
        if player_gold < price:
            return False, player_gold, f"Недостаточно золота. Нужно: {price}"
        if item.stock == 0:
            return False, player_gold, "Товар закончился."
        
        item.stock -= 1 if item.stock > 0 else 0
        return True, player_gold - price, f"Куплено: {item.name} за {price} золота."
    
    def sell_item(self, player_gold: int, item: ShopItem) -> tuple[bool, int, str]:
        price = self.get_sell_price(item)
        return True, player_gold + price, f"Продано: {item.name} за {price} золота."
    
    def to_dict(self):
        return {
            "name": self.name, "shopkeeper": self.shopkeeper,
            "shop_type": self.shop_type,
            "inventory": [i.to_dict() for i in self.inventory],
        }


SHOP_TEMPLATES = {
    "general": Shop(
        name="Общий магазин",
        shopkeeper="Торговец",
        shop_type="general",
        inventory=[
            ShopItem("healing_potion", "Зелье лечения", "🧪", "potion",
                     "Восстанавливает 2d4+2 HP", buy_price=25, sell_price=12,
                     properties={"healing": "2d4+2", "weight": 0.5}),
            ShopItem("torch", "Факел", "🔥", "misc",
                     "Освещает 20 футов", buy_price=1, sell_price=0,
                     properties={"weight": 1}),
            ShopItem("rope", "Верёвка (50ф)", "🪢", "misc",
                     "Крепкая верёвка", buy_price=10, sell_price=5,
                     properties={"weight": 10}),
            ShopItem("rations", "Пайки (1 день)", "🍖", "misc",
                     "Еда на день", buy_price=5, sell_price=2,
                     properties={"weight": 2}),
            ShopItem("waterskin", "Бурдюк", "🫗", "misc",
                     "Вмещает 1 кварту воды", buy_price=2, sell_price=1,
                     properties={"weight": 1}),
            ShopItem("backpack", "Рюкзак", "🎒", "misc",
                     "Вмещает 30 фунтов", buy_price=2, sell_price=1,
                     properties={"weight": 5}),
        ],
    ),
    "weapon": Shop(
        name="Оружейная",
        shopkeeper="Кузнец",
        shop_type="weapon",
        inventory=[
            ShopItem("dagger", "Кинжал", "🗡", "weapon",
                     "Лёгкое оружие", buy_price=25, sell_price=12,
                     properties={"damage": "1d4", "weight": 1}),
            ShopItem("short_sword", "Короткий меч", "⚔", "weapon",
                     "Лёгкое оружие", buy_price=30, sell_price=15,
                     properties={"damage": "1d6", "weight": 2}),
            ShopItem("longsword", "Длинный меч", "⚔", "weapon",
                     "Среднее оружие", buy_price=75, sell_price=35,
                     properties={"damage": "1d8", "weight": 3}),
            ShopItem("battleaxe", "Боевой топор", "🪓", "weapon",
                     "Среднее оружие", buy_price=70, sell_price=35,
                     properties={"damage": "1d8", "weight": 4}),
            ShopItem("greatsword", "Двуручный меч", "⚔", "weapon",
                     "Тяжёлое оружие", buy_price=150, sell_price=75,
                     properties={"damage": "2d6", "weight": 6}),
            ShopItem("light_crossbow", "Лёгкий арбалет", "🏹", "weapon",
                     "Дальнее оружие", buy_price=75, sell_price=35,
                     properties={"damage": "1d8", "weight": 5, "range": 80}),
            ShopItem("spear", "Копьё", "🔱", "weapon",
                     "Среднее/дальнее", buy_price=10, sell_price=5,
                     properties={"damage": "1d6", "weight": 3}),
        ],
    ),
    "armor": Shop(
        name="Броня",
        shopkeeper="Бронник",
        shop_type="armor",
        inventory=[
            ShopItem("leather", "Кожаная броня", "🦺", "armor",
                     "Лёгкая броня", buy_price=45, sell_price=20,
                     properties={"ac_bonus": 11, "weight": 10}),
            ShopItem("chain_shirt", "Кольчуга", "🦺", "armor",
                     "Средняя броня", buy_price=150, sell_price=75,
                     properties={"ac_bonus": 14, "weight": 20}),
            ShopItem("shield", "Щит", "🛡", "shield",
                     "Щит", buy_price=10, sell_price=5,
                     properties={"ac_bonus": 2, "weight": 6}),
            ShopItem("helmet", "Шлем", "⛑", "helmet",
                     "Шлем", buy_price=15, sell_price=7,
                     properties={"ac_bonus": 1, "weight": 2}),
            ShopItem("boots", "Сапоги", "👢", "boots",
                     "Сапоги", buy_price=10, sell_price=5,
                     properties={"weight": 2}),
            ShopItem("gauntlets", "Рукавицы", "🧤", "gloves",
                     "Рукавицы", buy_price=10, sell_price=5,
                     properties={"weight": 1}),
        ],
    ),
    "alchemy": Shop(
        name="Аптека",
        shopkeeper="Алхимик",
        shop_type="alchemy",
        inventory=[
            ShopItem("healing_potion", "Зелье лечения", "🧪", "potion",
                     "Восстанавливает 2d4+2 HP", buy_price=25, sell_price=12,
                     properties={"healing": "2d4+2", "weight": 0.5}),
            ShopItem("greater_healing", "Большое зелье лечения", "🧪", "potion",
                     "Восстанавливает 4d4+4 HP", buy_price=50, sell_price=25,
                     properties={"healing": "4d4+4", "weight": 0.5}),
            ShopItem("antidote", "Противоядие", "💧", "potion",
                     "Снимает отравление", buy_price=50, sell_price=25,
                     properties={"cure_poison": True, "weight": 0.5}),
            ShopItem("oil_flask", "Фляга с маслом", "🫗", "misc",
                     "Горючее масло", buy_price=1, sell_price=0,
                     properties={"weight": 1}),
            ShopItem("acid_flask", "Фляга с кислотой", "⚗", "misc",
                     "Кислота", buy_price=25, sell_price=12,
                     properties={"damage": "2d6", "weight": 1}),
            ShopItem("smokestick", "Дымовая палочка", "🎇", "misc",
                     "Создаёт дымовое облако", buy_price=12, sell_price=6,
                     properties={"weight": 0.5}),
        ],
    ),
}


def get_shop(shop_type: str) -> Shop | None:
    tmpl = SHOP_TEMPLATES.get(shop_type)
    if not tmpl:
        return None
    import copy
    return copy.deepcopy(tmpl)


def get_item_value(item: Item, is_buying: bool = True) -> int:
    base = {
        "weapon": 50, "armor": 50, "shield": 25, "potion": 25,
        "helmet": 20, "boots": 15, "gloves": 15, "ring": 50,
        "amulet": 50, "misc": 5, "ingredient": 10, "quest": 0,
    }.get(item.item_type, 5)
    
    if is_buying:
        return base // 2
    return base

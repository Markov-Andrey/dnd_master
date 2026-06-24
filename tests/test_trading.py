"""Тесты торговли."""
import pytest
from core.trading import get_shop, ShopItem, Shop, SHOP_TEMPLATES


class TestShopTemplates:
    def test_all_shops_exist(self):
        assert len(SHOP_TEMPLATES) == 4

    def test_shop_types(self):
        assert "general" in SHOP_TEMPLATES
        assert "weapon" in SHOP_TEMPLATES
        assert "armor" in SHOP_TEMPLATES
        assert "alchemy" in SHOP_TEMPLATES


class TestShop:
    def test_get_shop(self):
        shop = get_shop("weapon")
        assert shop is not None
        assert shop.name == "Оружейная"
        assert len(shop.inventory) > 0

    def test_buy_item(self):
        shop = get_shop("general")
        item = shop.inventory[0]
        success, gold, msg = shop.buy_item(1000, item)
        assert success is True
        assert gold < 1000

    def test_buy_insufficient_gold(self):
        shop = get_shop("weapon")
        item = shop.inventory[0]
        success, gold, msg = shop.buy_item(0, item)
        assert success is False

    def test_sell_item(self):
        shop = get_shop("general")
        item = shop.inventory[0]
        success, gold, msg = shop.sell_item(0, item)
        assert success is True
        assert gold > 0

    def test_get_unknown_shop(self):
        shop = get_shop("nonexistent")
        assert shop is None


class TestShopItem:
    def test_create_item(self):
        item = ShopItem(
            item_id="test", name="Test Item", icon="?",
            item_type="misc", sell_price=10, buy_price=5
        )
        assert item.item_id == "test"
        d = item.to_dict()
        assert "item_id" in d
        assert "name" in d

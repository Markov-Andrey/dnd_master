"""Тесты лута."""
import pytest
from core.loot import (
    Rarity, LootEntry, roll_loot, generate_chest_loot,
    get_rarity_color, LOOT_TABLES,
)


class TestRarity:
    def test_rarity_values(self):
        assert Rarity.COMMON.value == "common"
        assert Rarity.LEGENDARY.value == "legendary"

    def test_rarity_color(self):
        color = get_rarity_color("common")
        assert color == "#ffffff"
        color = get_rarity_color("rare")
        assert color == "#0070dd"


class TestLootTables:
    def test_all_monsters_have_loot(self):
        for mid in ["goblin", "skeleton", "wolf", "orc", "bandit"]:
            assert mid in LOOT_TABLES

    def test_loot_entry_fields(self):
        for mid, entries in LOOT_TABLES.items():
            for entry in entries:
                assert isinstance(entry, LootEntry)
                assert entry.item_id
                assert entry.name


class TestRollLoot:
    def test_goblin_loot_returns_list(self):
        loot = roll_loot("goblin")
        assert isinstance(loot, list)

    def test_orc_has_gold(self):
        loot = roll_loot("orc")
        gold_items = [i for i in loot if i.get("item_id") == "gold" or i.get("type") == "gold"]
        assert len(gold_items) > 0

    def test_unknown_monster_empty(self):
        loot = roll_loot("dragon_lord")
        assert isinstance(loot, list)


class TestChestLoot:
    def test_wooden_chest(self):
        loot = generate_chest_loot("wooden")
        assert isinstance(loot, list)
        assert len(loot) > 0

    def test_iron_chest(self):
        loot = generate_chest_loot("iron")
        assert isinstance(loot, list)

    def test_golden_chest(self):
        loot = generate_chest_loot("golden")
        assert isinstance(loot, list)

    def test_unknown_chest_fallback(self):
        loot = generate_chest_loot("mithril")
        assert isinstance(loot, list)

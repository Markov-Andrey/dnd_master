"""Тесты монстров и лута."""
import pytest
from core.monsters import (
    spawn_monster, roll_loot, get_encounter,
    MONSTER_TEMPLATES, LOCATION_ENCOUNTERS, LOOT_TABLES,
)
from core.combat import DamageType


class TestMonsterTemplates:
    def test_all_templates_exist(self):
        assert len(MONSTER_TEMPLATES) == 10

    def test_template_fields(self):
        for tid, tmpl in MONSTER_TEMPLATES.items():
            assert "name" in tmpl
            assert "hp" in tmpl
            assert "ac" in tmpl
            assert "attacks" in tmpl
            assert "xp" in tmpl


class TestSpawnMonster:
    def test_spawn_goblin(self):
        g = spawn_monster("goblin")
        assert g.name == "Гоблин"
        assert g.hp == 7
        assert g.ac == 15
        assert len(g.attacks) == 2

    def test_spawn_orc(self):
        o = spawn_monster("orc")
        assert o.name == "Орк"
        assert o.hp == 15
        assert o.attacks[0].damage_dice == "1d12+3"

    def test_spawn_unknown(self):
        u = spawn_monster("dragon")
        assert u.name == "???"

    def test_all_monsters_spawnable(self):
        for tid in MONSTER_TEMPLATES:
            m = spawn_monster(tid)
            assert m.hp > 0
            assert m.ac >= 8
            assert len(m.attacks) > 0


class TestLootRoll:
    def test_goblin_loot(self):
        loot = roll_loot("goblin")
        assert isinstance(loot, list)
        assert len(loot) > 0

    def test_loot_has_gold(self):
        has_gold_count = 0
        for _ in range(20):
            loot = roll_loot("orc")
            has_gold = any(item.get("gold") or item.get("item_id") == "gold" for item in loot)
            if has_gold:
                has_gold_count += 1
        assert has_gold_count > 0

    def test_empty_for_unknown(self):
        loot = roll_loot("dragon")
        assert isinstance(loot, list)


class TestEncounters:
    def test_all_locations_have_tables(self):
        for loc_id in ["forest", "cave", "ruins", "swamp", "mountain", "crossroads"]:
            assert loc_id in LOCATION_ENCOUNTERS

    def test_village_no_encounters(self):
        enc = get_encounter("village")
        assert enc == []

    def test_get_encounter_returns_list(self):
        enc = get_encounter("forest")
        assert isinstance(enc, list)


class TestLootTables:
    def test_loot_table_count(self):
        assert len(LOOT_TABLES) >= 8

    def test_loot_entry_fields(self):
        for item_id, item in LOOT_TABLES.items():
            assert "name" in item
            assert "icon" in item
            assert "item_type" in item

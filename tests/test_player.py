"""Тесты игрока."""
import pytest
from player.player import Player, ATTRS, make_skill_check, calc_max_hp, XP_BY_LEVEL


class TestPlayerCreation:
    def test_create_default(self):
        p = Player()
        assert p.name == "Герой"
        assert p.level == 1

    def test_create_with_attrs(self):
        attrs = {"str": 14, "dex": 12, "con": 10, "int": 10, "wis": 10, "cha": 10}
        p = Player.create("Test", attrs)
        assert p.name == "Test"
        assert p.attributes["str"] == 14
        assert p.hp > 0

    def test_create_hp_depends_on_con(self):
        attrs_high = {"str": 10, "dex": 10, "con": 16, "int": 10, "wis": 10, "cha": 10}
        attrs_low = {"str": 10, "dex": 10, "con": 8, "int": 10, "wis": 10, "cha": 10}
        p_high = Player.create("High", attrs_high)
        p_low = Player.create("Low", attrs_low)
        assert p_high.max_hp > p_low.max_hp


class TestPlayerStats:
    def test_modifier(self):
        p = Player(attributes={"str": 14, "dex": 10, "con": 10, "int": 10, "wis": 10, "cha": 10})
        assert p.get_modifier("str") == 2
        assert p.get_modifier("dex") == 0

    def test_ac_base(self):
        p = Player(attributes={"str": 10, "dex": 14, "con": 10, "int": 10, "wis": 10, "cha": 10})
        assert p.get_ac() == 12

    def test_take_damage(self):
        p = Player()
        p.hp = 10
        actual = p.take_damage(3)
        assert actual == 3
        assert p.hp == 7

    def test_heal(self):
        p = Player()
        p.hp = 5
        p.max_hp = 10
        actual = p.heal(3)
        assert actual == 3
        assert p.hp == 8

    def test_is_alive(self):
        p = Player()
        p.hp = 1
        assert p.is_alive() is True
        p.hp = 0
        assert p.is_alive() is False


class TestXPSystem:
    def test_gain_xp(self):
        p = Player()
        result = p.gain_xp(100)
        assert result["xp_gained"] == 100
        assert result["total_xp"] == 100

    def test_level_up(self):
        p = Player()
        p.xp = 250
        result = p.gain_xp(100)
        assert result["leveled_up"] is True
        assert p.level == 2

    def test_xp_table(self):
        assert XP_BY_LEVEL[1] == 0
        assert XP_BY_LEVEL[2] == 300


class TestSkillCheck:
    def test_skill_check_result(self):
        p = Player(attributes={"str": 14, "dex": 12, "con": 10, "int": 10, "wis": 10, "cha": 10})
        result = make_skill_check(p, "athletics", "Test")
        assert "roll" in result
        assert "total" in result
        assert "skill_name" in result
        assert 1 <= result["roll"] <= 20

    def test_all_skills_work(self):
        p = Player()
        skills = ["athletics", "acrobatics", "stealth", "perception", "persuasion"]
        for skill in skills:
            result = make_skill_check(p, skill, "Test")
            assert "total" in result


class TestSaveLoad:
    def test_to_dict(self):
        p = Player(name="Test", level=3, xp=500)
        d = p.to_dict()
        assert d["name"] == "Test"
        assert d["level"] == 3
        assert "ac" in d
        assert "modifiers" in d

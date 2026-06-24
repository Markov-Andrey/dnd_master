"""Тесты отдыха."""
import pytest
from core.rest import short_rest, long_rest, can_rest, can_rest


class TestShortRest:
    def test_short_rest_heals(self):
        class FakePlayer:
            hp = 5
            max_hp = 20
            level = 1
            def get_modifier(self, attr): return 0
            def heal(self, amount): self.hp = min(self.max_hp, self.hp + amount)

        p = FakePlayer()
        result = short_rest(p)
        assert result.rest_type == "short"
        assert result.hp_healed >= 0

    def test_short_rest_no_heal_if_full(self):
        class FakePlayer:
            hp = 20
            max_hp = 20
            level = 1
            def get_modifier(self, attr): return 0
            def heal(self, amount): self.hp = min(self.max_hp, self.hp + amount)

        p = FakePlayer()
        result = short_rest(p)
        assert result.hp_healed == 0


class TestLongRest:
    def test_long_rest_full_heal(self):
        class FakePlayer:
            hp = 5
            max_hp = 20
            level = 1
            exhaustion = 1
            conditions = ["poisoned"]
            def heal(self, amount): self.hp = min(self.max_hp, self.hp + amount)

        p = FakePlayer()
        result = long_rest(p)
        assert result.rest_type == "long"
        assert result.spells_restored is True
        assert p.hp == 20


class TestCanRest:
    def test_village_safe(self):
        ok, msg = can_rest("village", "long")
        assert ok is True

    def test_lake_no_rest(self):
        ok, msg = can_rest("lake", "short")
        assert ok is False

    def test_cave_long_rest_possible(self):
        ok, msg = can_rest("cave", "long")
        assert ok is True

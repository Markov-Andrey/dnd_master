"""Тесты боевой системы."""
import pytest
from core.combat import (
    CombatEngine, StatBlock, Attack, Combatant, AttackResult,
    Condition, DamageType, roll_dice, d20, ability_mod, proficiency_bonus,
)


class TestDiceRolls:
    def test_d20_range(self):
        for _ in range(100):
            result = d20()
            assert 1 <= result <= 20

    def test_roll_dice_single(self):
        result = roll_dice("1d6")
        assert 1 <= result <= 6

    def test_roll_dice_multiple(self):
        result = roll_dice("2d6")
        assert 2 <= result <= 12

    def test_roll_dice_with_bonus(self):
        result = roll_dice("1d6+3")
        assert 4 <= result <= 9

    def test_roll_dice_flat(self):
        result = roll_dice("5")
        assert result == 5


class TestAbilityMod:
    def test_mod_10(self):
        assert ability_mod(10) == 0

    def test_mod_16(self):
        assert ability_mod(16) == 3

    def test_mod_8(self):
        assert ability_mod(8) == -1

    def test_mod_1(self):
        assert ability_mod(1) == -5


class TestProficiencyBonus:
    def test_level_1(self):
        assert proficiency_bonus(1) == 2

    def test_level_5(self):
        assert proficiency_bonus(5) == 3

    def test_level_9(self):
        assert proficiency_bonus(9) == 4


class TestStatBlock:
    def test_create(self):
        sb = StatBlock(name="Test", hp=20, max_hp=20, ac=15)
        assert sb.name == "Test"
        assert sb.hp == 20
        assert sb.ac == 15

    def test_take_damage(self):
        sb = StatBlock(hp=10, max_hp=10)
        actual = sb.take_damage(5)
        assert actual == 5
        assert sb.hp == 5

    def test_take_lethal_damage(self):
        sb = StatBlock(hp=5, max_hp=10)
        actual = sb.take_damage(10)
        assert actual == 5
        assert sb.hp == 0
        assert sb.condition == Condition.UNCONSCIOUS

    def test_heal(self):
        sb = StatBlock(hp=5, max_hp=10)
        actual = sb.heal(3)
        assert actual == 3
        assert sb.hp == 8

    def test_heal_overflow(self):
        sb = StatBlock(hp=8, max_hp=10)
        actual = sb.heal(5)
        assert actual == 2
        assert sb.hp == 10

    def test_is_conscious(self):
        sb = StatBlock(hp=10)
        assert sb.is_conscious() is True

    def test_unconscious(self):
        sb = StatBlock(hp=0)
        assert sb.is_conscious() is False

    def test_initiative(self):
        sb = StatBlock(dexterity=14)
        init = sb.get_initiative()
        assert 1 <= init <= 22

    def test_attack_bonus(self):
        sb = StatBlock(strength=14, level=1)
        bonus = sb.get_attack_bonus()
        assert bonus == 4


class TestAttack:
    def test_roll_damage(self):
        atk = Attack(damage_dice="1d8")
        result = atk.roll_damage()
        assert 1 <= result["damage"] <= 8
        assert result["damage_type"] == "slashing"

    def test_attack_with_bonus(self):
        atk = Attack(damage_dice="1d6", bonus=3)
        result = atk.roll_damage()
        assert 4 <= result["damage"] <= 9


class TestCombatEngine:
    def _make_combat(self):
        e = CombatEngine()
        p = StatBlock(name="Hero", hp=20, max_hp=20, ac=15, dexterity=14)
        p.attacks.append(Attack(damage_dice="1d8"))
        e.add_combatant(p, is_player=True, team=0)

        g = StatBlock(name="Goblin", hp=7, max_hp=7, ac=15, dexterity=14)
        g.attacks.append(Attack(damage_dice="1d4"))
        e.add_combatant(g, is_player=False, team=1)
        return e

    def test_start(self):
        e = self._make_combat()
        e.start()
        assert e.is_active
        assert e.round == 1
        assert len(e.log) > 0

    def test_attack_hit(self):
        e = self._make_combat()
        e.start()
        attacker = e.get_current()
        defender = [c for c in e.combatants if c != attacker][0]
        result = e.attack(attacker, defender, 0)
        assert isinstance(result.is_hit, bool)
        assert result.attacker == attacker.name
        assert result.defender == defender.name

    def test_enemy_turn(self):
        e = self._make_combat()
        e.start()
        current = e.get_current()
        if current and not current.is_player:
            results = e.enemy_turn()
            assert len(results) >= 1
        else:
            e.next_turn()
            results = e.enemy_turn()
            assert len(results) >= 1

    def test_next_turn(self):
        e = self._make_combat()
        e.start()
        e.next_turn()
        assert e.current_turn >= 0

    def test_combat_end(self):
        e = self._make_combat()
        e.start()
        for c in e.combatants:
            if not c.is_player:
                c.stat_block.hp = 0
                c.stat_block.is_alive = False
        alive = [c for c in e.combatants if c.is_alive()]
        assert len(alive) == 1
        assert alive[0].is_player is True

    def test_get_state(self):
        e = self._make_combat()
        e.start()
        state = e.get_state()
        assert "round" in state
        assert "combatants" in state
        assert len(state["combatants"]) == 2

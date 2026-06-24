"""Тесты ловушек."""
import pytest
from core.traps import (
    Trap, TrapType, TrapSeverity,
    spawn_trap, check_trap_detection, check_trap_disarm,
    TRAP_TEMPLATES, LOCATION_TRAPS,
)


class TestTrapTemplates:
    def test_all_templates_exist(self):
        assert len(TRAP_TEMPLATES) == 10

    def test_template_fields(self):
        for tid, tmpl in TRAP_TEMPLATES.items():
            assert "name" in tmpl
            assert "dc" in tmpl
            assert "damage_dice" in tmpl
            assert "severity" in tmpl


class TestTrap:
    def test_create_trap(self):
        t = Trap(name="Pit", dc=12, damage_dice="2d6")
        assert t.name == "Pit"
        assert t.dc == 12
        assert t.is_triggered is False

    def test_trigger_trap(self):
        t = Trap(name="Fire", damage_dice="4d6")
        result = t.trigger()
        assert result["triggered"] is True
        assert result["damage"] >= 0
        assert t.is_triggered is True

    def test_trigger_already_triggered(self):
        t = Trap(name="Fire", damage_dice="4d6")
        t.trigger()
        result = t.trigger()
        assert result["triggered"] is False

    def test_disarm_trap(self):
        t = Trap(name="Pit", dc=12)
        result = check_trap_disarm(15, t)
        assert result["disarmed"] is True
        assert t.is_disarmed is True

    def test_fail_disarm(self):
        t = Trap(name="Pit", dc=15)
        result = check_trap_disarm(10, t)
        assert result["disarmed"] is False

    def test_detect_trap(self):
        t = Trap(name="Pit", dc=12)
        result = check_trap_detection(15, t)
        assert result["detected"] is True

    def test_fail_detect(self):
        t = Trap(name="Pit", dc=15)
        result = check_trap_detection(8, t)
        assert result["detected"] is False


class TestLocationTraps:
    def test_cave_has_traps(self):
        assert "cave" in LOCATION_TRAPS

    def test_village_no_traps(self):
        assert LOCATION_TRAPS.get("village", []) == []

    def test_spawn_trap_deterministic(self):
        t = spawn_trap("village")
        assert t is None

    def test_spawn_trap_can_return_none(self):
        t = spawn_trap("forest")
        assert t is None or isinstance(t, Trap)

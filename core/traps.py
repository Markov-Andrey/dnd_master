"""Ловушки и загадки с мини-играми."""
import random
from dataclasses import dataclass, field
from enum import Enum
from core.combat import roll_dice, d20, DamageType


class TrapType(Enum):
    PIT = "pit"
    NEEDLE = "needle"
    GAS = "gas"
    FIRE = "fire"
    ICE = "ice"
    POISON = "poison"
    NET = "net"
    SPEAR = "spear"
    BOLDER = "bolder"
    TAR = "tar"


class TrapSeverity(Enum):
    SIMPLE = "simple"
    MODERATE = "moderate"
    DEADLY = "deadly"


@dataclass
class Trap:
    name: str = "Ловушка"
    trap_type: TrapType = TrapType.PIT
    severity: TrapSeverity = TrapSeverity.SIMPLE
    dc: int = 12
    damage_dice: str = "1d6"
    damage_type: DamageType = DamageType.PIERCING
    description: str = ""
    effect: str = ""
    puzzle_type: str = ""
    puzzle_difficulty: str = "easy"
    is_hidden: bool = True
    is_triggered: bool = False
    is_disarmed: bool = False

    def detect_dc(self) -> int:
        base = self.dc
        if self.severity == TrapSeverity.DEADLY:
            base += 4
        elif self.severity == TrapSeverity.MODERATE:
            base += 2
        return base

    def disarm_dc(self) -> int:
        return self.dc + 2

    def trigger(self) -> dict:
        if self.is_triggered or self.is_disarmed:
            return {"triggered": False}
        self.is_triggered = True
        damage = roll_dice(self.damage_dice)
        return {
            "triggered": True,
            "damage": damage,
            "damage_type": self.damage_type.value,
            "effect": self.effect,
            "puzzle": self.puzzle_type,
            "puzzle_difficulty": self.puzzle_difficulty,
            "message": f"Ловушка сработала! {self.name}: {damage} урона.",
        }


TRAP_TEMPLATES = {
    "pit": {
        "name": "Яма",
        "trap_type": TrapType.PIT,
        "severity": TrapSeverity.SIMPLE,
        "dc": 12,
        "damage_dice": "2d6",
        "damage_type": "bludgeoning",
        "description": "Замаскированная яма в полу.",
        "effect": "Падение. Нужен прыжок (DC 12) чтобы перепрыгнуть.",
        "puzzle_type": "reaction",
        "puzzle_difficulty": "easy",
    },
    "needle": {
        "name": "Игольная ловушка",
        "trap_type": TrapType.NEEDLE,
        "severity": TrapSeverity.MODERATE,
        "dc": 15,
        "damage_dice": "1d4",
        "damage_type": "piercing",
        "description": "Игла в отверстии, отравлена.",
        "effect": "Отравление на 1 час (DC 13 con save).",
        "puzzle_type": "memory_match",
        "puzzle_difficulty": "medium",
    },
    "gas": {
        "name": "Ядовитый газ",
        "trap_type": TrapType.GAS,
        "severity": TrapSeverity.MODERATE,
        "dc": 13,
        "damage_dice": "2d6",
        "damage_type": "poison",
        "description": "Облако зелёного газа.",
        "effect": "Отравление на 1 минуту (DC 13 con save).",
        "puzzle_type": "color_sequence",
        "puzzle_difficulty": "medium",
    },
    "fire": {
        "name": "Огненная ловушка",
        "trap_type": TrapType.FIRE,
        "severity": TrapSeverity.DEADLY,
        "dc": 15,
        "damage_dice": "4d6",
        "damage_type": "fire",
        "description": "Струи пламени из стен.",
        "effect": "Горение на 1d4 раундов.",
        "puzzle_type": "lockpick",
        "puzzle_difficulty": "hard",
    },
    "ice": {
        "name": "Ледяная ловушка",
        "trap_type": TrapType.ICE,
        "severity": TrapSeverity.MODERATE,
        "dc": 14,
        "damage_dice": "2d6",
        "damage_type": "cold",
        "description": "Замёрзшие пол и стены.",
        "effect": "Замедление на 1 минуту (DC 13 con save).",
        "puzzle_type": "slider",
        "puzzle_difficulty": "medium",
    },
    "poison": {
        "name": "Отравленная лужа",
        "trap_type": TrapType.POISON,
        "severity": TrapSeverity.MODERATE,
        "dc": 12,
        "damage_dice": "2d4",
        "damage_type": "poison",
        "description": "Кислотная лужа на полу.",
        "effect": "Урон каждые раунд пока стоишь в ней.",
        "puzzle_type": "word_puzzle",
        "puzzle_difficulty": "medium",
    },
    "net": {
        "name": "Сеть",
        "trap_type": TrapType.NET,
        "severity": TrapSeverity.SIMPLE,
        "dc": 12,
        "damage_dice": "0",
        "damage_type": "bludgeoning",
        "description": "Сеть сверху.",
        "effect": "Опутан. Ст.opend DC 12 athletics или 13 acrobatics.",
        "puzzle_type": "reaction",
        "puzzle_difficulty": "easy",
    },
    "spear": {
        "name": "Копейная ловушка",
        "trap_type": TrapType.SPEAR,
        "severity": TrapSeverity.DEADLY,
        "dc": 16,
        "damage_dice": "2d6",
        "damage_type": "piercing",
        "description": "Копья вылетают из стен.",
        "effect": "Может нанести крит при провале DC 16.",
    },
    "bolder": {
        "name": "Каменная глыба",
        "trap_type": TrapType.BOLDER,
        "severity": TrapSeverity.DEADLY,
        "dc": 15,
        "damage_dice": "6d6",
        "damage_type": "bludgeoning",
        "description": "Огромная глыба катится по коридору.",
        "effect": "Декс. save DC 15 или полный урон.",
    },
    "tar": {
        "name": "Смола",
        "trap_type": TrapType.TAR,
        "severity": TrapSeverity.SIMPLE,
        "dc": 10,
        "damage_dice": "1d4",
        "damage_type": "fire",
        "description": "Лужа горючей смолы.",
        "effect": "Замедление. Может загореться от огня.",
    },
}


LOCATION_TRAPS = {
    "cave": [
        {"trap": "pit", "chance": 0.3},
        {"trap": "spear", "chance": 0.15},
        {"trap": "bolder", "chance": 0.1},
    ],
    "ruins": [
        {"trap": "needle", "chance": 0.25},
        {"trap": "gas", "chance": 0.2},
        {"trap": "net", "chance": 0.2},
        {"trap": "fire", "chance": 0.1},
    ],
    "forest": [
        {"trap": "net", "chance": 0.2},
        {"trap": "pit", "chance": 0.15},
    ],
    "swamp": [
        {"trap": "poison", "chance": 0.3},
        {"trap": "tar", "chance": 0.2},
    ],
    "mountain": [
        {"trap": "bolder", "chance": 0.2},
        {"trap": "pit", "chance": 0.2},
    ],
    "crossroads": [],
    "village": [],
    "lake": [],
}


def spawn_trap(location_id: str) -> Trap | None:
    traps = LOCATION_TRAPS.get(location_id, [])
    if not traps:
        return None
    
    roll = random.random()
    cumulative = 0
    for t in traps:
        cumulative += t["chance"]
        if roll <= cumulative:
            tmpl = TRAP_TEMPLATES.get(t["trap"])
            if tmpl:
                return Trap(
                    name=tmpl["name"],
                    trap_type=tmpl["trap_type"],
                    severity=tmpl["severity"],
                    dc=tmpl["dc"],
                    damage_dice=tmpl["damage_dice"],
                    damage_type=DamageType(tmpl["damage_type"]),
                    description=tmpl["description"],
                    effect=tmpl["effect"],
                )
    return None


def check_trap_detection(perception_roll: int, trap: Trap) -> dict:
    dc = trap.detect_dc()
    detected = perception_roll >= dc
    return {
        "detected": detected,
        "perception_roll": perception_roll,
        "dc": dc,
        "message": f"Замечена ловушка! ({perception_roll} vs DC {dc})" if detected else "Ничего не заметил.",
    }


def check_trap_disarm(thief_roll: int, trap: Trap) -> dict:
    dc = trap.disarm_dc()
    success = thief_roll >= dc
    if success:
        trap.is_disarmed = True
    return {
        "disarmed": success,
        "roll": thief_roll,
        "dc": dc,
        "message": f"Ловушка обезврежена! ({thief_roll} vs DC {dc})" if success else f"Провал! ({thief_roll} vs DC {dc})",
    }

"""Combat AI: тактическое поведение существ в бою.

Каждое существо имеет:
- Паттерн поведения (aggro/defensive/ambush/ranged/caster/support)
- Тактические решения на основе HP, позиции, способностей
- Приоритеты целей
- Паттерны атак (последовательность ударов)
- LLM-наррация для каждого действия
"""
import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class BehaviorPattern(Enum):
    AGGRO = "aggro"           # Берсерк: ближний бой, игнорирует урон
    DEFENSIVE = "defensive"   # Защитник: прикрывает, контратакует
    AMBUSH = "ambush"         # Засада: крит при первом ударе
    RANGED = "ranged"         # Дальний бой: дистанция, уклонение
    CASTER = "caster"         # Заклинатель: магия, слаб в ближнем
    SUPPORT = "support"       # Лечитель: восстанавливает союзников
    COWARD = "coward"         # Трус: убегает при низком HP
    PACK = "pack"             # Стая: координирует атаки
    BOSS = "boss"             # Босс: фазы,特殊攻击ы
    MINDLESS = "mindless"     # Бессмысленный: случайные атаки


class ActionType(Enum):
    ATTACK = "attack"
    SPECIAL = "special"
    DEFEND = "defend"
    FLEE = "flee"
    HEAL = "heal"
    BUFF = "buff"
    DEBUFF = "debuff"
    REPOSITION = "reposition"
    WAIT = "wait"


@dataclass
class CombatAction:
    action_type: ActionType
    attack_index: int = 0
    target_id: str = ""
    ability_name: str = ""
    narrative: str = ""
    reasoning: str = ""
    damage_modifier: float = 1.0
    defense_modifier: float = 1.0


@dataclass
class CreatureAI:
    creature_id: str
    name: str
    pattern: BehaviorPattern
    hp_percent: float = 1.0
    is_aware: bool = True
    has_special: bool = False
    special_cooldown: int = 0
    preferred_distance: str = "melee"
    target_priority: str = "nearest"
    aggression: float = 0.5
    intelligence: float = 0.5
    morale: float = 1.0
    round_number: int = 0
    last_action: ActionType = ActionType.ATTACK
    consecutive_attacks: int = 0
    damage_taken_this_round: int = 0
    allies_alive: int = 1
    enemies_alive: int = 1

    def to_dict(self) -> dict:
        return {
            "id": self.creature_id,
            "name": self.name,
            "pattern": self.pattern.value,
            "hp_percent": round(self.hp_percent, 2),
            "aggression": round(self.aggression, 2),
            "intelligence": round(self.intelligence, 2),
            "morale": round(self.morale, 2),
            "round": self.round_number,
            "last_action": self.last_action.value,
        }


PATTERN_CONFIGS = {
    BehaviorPattern.AGGRO: {
        "aggression": 0.9, "intelligence": 0.3, "preferred_distance": "melee",
        "target_priority": "weakest", "flee_threshold": 0.1,
    },
    BehaviorPattern.DEFENSIVE: {
        "aggression": 0.4, "intelligence": 0.6, "preferred_distance": "melee",
        "target_priority": "attacker", "flee_threshold": 0.15,
    },
    BehaviorPattern.AMBUSH: {
        "aggression": 0.8, "intelligence": 0.7, "preferred_distance": "melee",
        "target_priority": "weakest", "flee_threshold": 0.3,
    },
    BehaviorPattern.RANGED: {
        "aggression": 0.5, "intelligence": 0.6, "preferred_distance": "ranged",
        "target_priority": "nearest", "flee_threshold": 0.25,
    },
    BehaviorPattern.CASTER: {
        "aggression": 0.6, "intelligence": 0.8, "preferred_distance": "ranged",
        "target_priority": "strongest", "flee_threshold": 0.3,
    },
    BehaviorPattern.SUPPORT: {
        "aggression": 0.2, "intelligence": 0.7, "preferred_distance": "ranged",
        "target_priority": "weakest_ally", "flee_threshold": 0.2,
    },
    BehaviorPattern.COWARD: {
        "aggression": 0.2, "intelligence": 0.5, "preferred_distance": "ranged",
        "target_priority": "nearest", "flee_threshold": 0.5,
    },
    BehaviorPattern.PACK: {
        "aggression": 0.7, "intelligence": 0.5, "preferred_distance": "melee",
        "target_priority": "coordinated", "flee_threshold": 0.2,
    },
    BehaviorPattern.BOSS: {
        "aggression": 0.7, "intelligence": 0.9, "preferred_distance": "melee",
        "target_priority": "strongest", "flee_threshold": 0.0,
    },
    BehaviorPattern.MINDLESS: {
        "aggression": 0.6, "intelligence": 0.1, "preferred_distance": "melee",
        "target_priority": "random", "flee_threshold": 0.0,
    },
}


class CombatAIBrain:
    def __init__(self):
        self.creatures: dict[str, CreatureAI] = {}
        self.combat_log: list[dict] = []

    def register_creature(self, creature_id: str, name: str, pattern: BehaviorPattern, hp_max: int = 10):
        config = PATTERN_CONFIGS.get(pattern, PATTERN_CONFIGS[BehaviorPattern.MINDLESS])
        ai = CreatureAI(
            creature_id=creature_id,
            name=name,
            pattern=pattern,
            aggression=config["aggression"],
            intelligence=config["intelligence"],
            preferred_distance=config["preferred_distance"],
            target_priority=config["target_priority"],
        )
        self.creatures[creature_id] = ai
        return ai

    def decide_action(self, creature_id: str, combat_state: dict) -> CombatAction:
        ai = self.creatures.get(creature_id)
        if not ai:
            return CombatAction(ActionType.ATTACK, reasoning="нет AI")

        ai.round_number += 1
        ai.hp_percent = combat_state.get("hp_percent", 1.0)
        ai.allies_alive = combat_state.get("allies_alive", 1)
        ai.enemies_alive = combat_state.get("enemies_alive", 1)
        ai.damage_taken_this_round = combat_state.get("damage_taken", 0)

        if ai.hp_percent <= 0:
            return CombatAction(ActionType.WAIT, reasoning="мёртв")

        if self._should_flee(ai):
            return self._flee_action(ai)

        if ai.pattern == BehaviorPattern.SUPPORT:
            action = self._decide_support(ai, combat_state)
        elif ai.pattern == BehaviorPattern.CASTER:
            action = self._decide_caster(ai, combat_state)
        elif ai.pattern == BehaviorPattern.AMBUSH:
            action = self._decide_ambush(ai, combat_state)
        elif ai.pattern == BehaviorPattern.PACK:
            action = self._decide_pack(ai, combat_state)
        elif ai.pattern == BehaviorPattern.BOSS:
            action = self._decide_boss(ai, combat_state)
        elif ai.pattern == BehaviorPattern.COWARD:
            action = self._decide_coward(ai, combat_state)
        elif ai.pattern == BehaviorPattern.RANGED:
            action = self._decide_ranged(ai, combat_state)
        else:
            action = self._decide_basic(ai, combat_state)

        ai.last_action = action.action_type
        if action.action_type == ActionType.ATTACK:
            ai.consecutive_attacks += 1
        else:
            ai.consecutive_attacks = 0

        self.combat_log.append({
            "creature": ai.name,
            "pattern": ai.pattern.value,
            "action": action.action_type.value,
            "reasoning": action.reasoning,
            "hp": ai.hp_percent,
        })

        return action

    def _should_flee(self, ai: CreatureAI) -> bool:
        thresholds = {
            BehaviorPattern.COWARD: 0.5,
            BehaviorPattern.AMBUSH: 0.3,
            BehaviorPattern.RANGED: 0.25,
            BehaviorPattern.CASTER: 0.3,
            BehaviorPattern.SUPPORT: 0.2,
        }
        threshold = thresholds.get(ai.pattern, 0.1)

        if ai.hp_percent > threshold:
            return False

        if ai.pattern == BehaviorPattern.AGGRO and ai.morale > 0.3:
            return False

        if ai.pattern == BehaviorPattern.BOSS:
            return False

        if ai.intelligence > 0.7 and ai.hp_percent < threshold * 0.5:
            return True

        return random.random() < (1.0 - ai.morale) * 0.5

    def _flee_action(self, ai: CreatureAI) -> CombatAction:
        ai.morale = max(0, ai.morale - 0.2)
        return CombatAction(
            action_type=ActionType.FLEE,
            reasoning=f"HP {ai.hp_percent:.0%}, паттерн {ai.pattern.value} → отступление",
            narrative=f"{ai.name} отступает, ища выход...",
        )

    def _decide_basic(self, ai: CreatureAI, state: dict) -> CombatAction:
        if ai.hp_percent < 0.3 and random.random() < 0.3:
            return CombatAction(
                action_type=ActionType.DEFEND,
                defense_modifier=1.5,
                reasoning=f"HP низкий ({ai.hp_percent:.0%}) → защита",
                narrative=f"{ai.name} принимает защитную стойку.",
            )

        if ai.consecutive_attacks > 3 and random.random() < 0.2:
            return CombatAction(
                action_type=ActionType.REPOSITION,
                reasoning="серия атак → смена позиции",
                narrative=f"{ai.name} перегруппировывается.",
            )

        attack_idx = 0
        if len(state.get("attacks", [])) > 1 and random.random() < 0.3:
            attack_idx = 1

        return CombatAction(
            action_type=ActionType.ATTACK,
            attack_index=attack_idx,
            target_id=self._select_target(ai, state),
            reasoning=f"агрессия {ai.aggression:.0%}, атака #{attack_idx}",
        )

    def _decide_support(self, ai: CreatureAI, state: dict) -> CombatAction:
        wounded_ally = state.get("most_wounded_ally")
        if wounded_ally and wounded_ally.get("hp_percent", 1) < 0.5:
            return CombatAction(
                action_type=ActionType.HEAL,
                target_id=wounded_ally.get("id", ""),
                reasoning=f"союзник {wounded_ally.get('hp_percent', 0):.0%} HP → лечение",
                narrative=f"{ai.name} помогает раненому союзнику.",
            )

        return CombatAction(
            action_type=ActionType.BUFF,
            reasoning="нет раненых → бафф",
            narrative=f"{ai.name} укрепляет союзников.",
        )

    def _decide_caster(self, ai: CreatureAI, state: dict) -> CombatAction:
        if state.get("enemies_alive", 0) > 2 and random.random() < 0.4:
            return CombatAction(
                action_type=ActionType.SPECIAL,
                ability_name="area_attack",
                damage_modifier=0.7,
                reasoning="много врагов → AoE атака",
                narrative=f"{ai.name} призывает магическую волну!",
            )

        if ai.hp_percent < 0.4 and random.random() < 0.5:
            return CombatAction(
                action_type=ActionType.DEFEND,
                defense_modifier=2.0,
                reasoning="HP критический → магический барьер",
                narrative=f"{ai.name} создаёт защитный барьер.",
            )

        return CombatAction(
            action_type=ActionType.ATTACK,
            attack_index=1,
            target_id=self._select_target(ai, state),
            reasoning="заклинатель → магическая атака",
        )

    def _decide_ambush(self, ai: CreatureAI, state: dict) -> CombatAction:
        if ai.round_number == 1 and not state.get("was_damaged", False):
            return CombatAction(
                action_type=ActionType.SPECIAL,
                ability_name="surprise_attack",
                damage_modifier=2.0,
                reasoning="первый раунд, не атакован → засада",
                narrative=f"{ai.name} наносит удар из тени!",
            )

        if ai.hp_percent < 0.4:
            return CombatAction(
                action_type=ActionType.REPOSITION,
                reasoning="низкий HP → перегруппировка",
                narrative=f"{ai.name} скрывается в тенях.",
            )

        return self._decide_basic(ai, state)

    def _decide_pack(self, ai: CreatureAI, state: dict) -> CombatAction:
        target = self._select_target(ai, state)
        allies_attacking = state.get("allies_attacking_target", {}).get(target, 0)

        if allies_attacking >= 2:
            return CombatAction(
                action_type=ActionType.REPOSITION,
                reasoning=f"стая уже атакует цель → смена позиции",
                narrative=f"{ai.name} маневрирует, ища лучший угол.",
            )

        return CombatAction(
            action_type=ActionType.ATTACK,
            target_id=target,
            reasoning=f"стая координирует атаку на {target}",
            narrative=f"{ai.name} атакует вместе с сородичами.",
        )

    def _decide_boss(self, ai: CreatureAI, state: dict) -> CombatAction:
        phase = "normal"
        if ai.hp_percent < 0.3:
            phase = "enrage"
        elif ai.hp_percent < 0.6:
            phase = "desperate"

        if phase == "enrage" and random.random() < 0.5:
            return CombatAction(
                action_type=ActionType.SPECIAL,
                ability_name="berserk",
                damage_modifier=1.8,
                reasoning=f"фаза {phase} → берсерк",
                narrative=f"{ai.name} ВОПИТ и атакует с яростью!",
            )

        if phase == "desperate" and random.random() < 0.3:
            return CombatAction(
                action_type=ActionType.SPECIAL,
                ability_name="desperate_strike",
                damage_modifier=1.5,
                reasoning=f"фаза {phase} → отчаянный удар",
                narrative=f"{ai.name} наносит отчаянный удар!",
            )

        if ai.round_number % 3 == 0 and random.random() < 0.4:
            return CombatAction(
                action_type=ActionType.SPECIAL,
                ability_name="power_attack",
                damage_modifier=1.3,
                reasoning="каждый 3-й раунд → мощная атака",
                narrative=f"{ai.name} готовит мощный удар!",
            )

        return self._decide_basic(ai, state)

    def _decide_coward(self, ai: CreatureAI, state: dict) -> CombatAction:
        if ai.hp_percent < 0.5 and random.random() < 0.6:
            return CombatAction(
                action_type=ActionType.FLEE,
                reasoning="трус, HP низкий → побег",
                narrative=f"{ai.name} в панике бежит!",
            )

        if state.get("allies_alive", 0) > 1 and random.random() < 0.4:
            return CombatAction(
                action_type=ActionType.DEFEND,
                reasoning="трус → прячется за союзников",
                narrative=f"{ai.name} прячется за спинами других.",
            )

        return self._decide_basic(ai, state)

    def _decide_ranged(self, ai: CreatureAI, state: dict) -> CombatAction:
        nearest_enemy = state.get("nearest_enemy_distance", 5)

        if nearest_enemy <= 2 and random.random() < 0.5:
            return CombatAction(
                action_type=ActionType.REPOSITION,
                reasoning=f"враг близко ({nearest_enemy}м) → отход",
                narrative=f"{ai.name} отступает, сохраняя дистанцию.",
            )

        return CombatAction(
            action_type=ActionType.ATTACK,
            attack_index=1,
            target_id=self._select_target(ai, state),
            reasoning="дальний бой → стреляет",
        )

    def _select_target(self, ai: CreatureAI, state: dict) -> str:
        targets = state.get("enemies", [])
        if not targets:
            return ""

        priority = ai.target_priority
        if priority == "nearest":
            return targets[0].get("id", "") if targets else ""
        elif priority == "weakest":
            return min(targets, key=lambda t: t.get("hp_percent", 1)).get("id", "")
        elif priority == "strongest":
            return max(targets, key=lambda t: t.get("level", 1)).get("id", "")
        elif priority == "attacker":
            return state.get("last_attacker", targets[0].get("id", ""))
        elif priority == "random":
            return random.choice(targets).get("id", "")
        else:
            return targets[0].get("id", "")

    def generate_narrative(self, action: CombatAction, result: dict) -> str:
        if action.narrative:
            base = action.narrative
        else:
            base = self._default_narrative(action, result)

        if result.get("is_critical"):
            base += " Критический удар!"
        if result.get("damage", 0) > 15:
            base += " Мощный удар!"
        if not result.get("is_hit"):
            base = f"{action.target_id or 'Цель'} уклоняется."

        return base

    def _default_narrative(self, action: CombatAction, result: dict) -> str:
        if action.action_type == ActionType.ATTACK:
            if result.get("is_hit"):
                return f"Атака попадает! {result.get('damage', 0)} урона."
            return "Атака промахивается."
        elif action.action_type == ActionType.DEFEND:
            return "Защитная стойка."
        elif action.action_type == ActionType.SPECIAL:
            return f"Особая способность: {action.ability_name}!"
        elif action.action_type == ActionType.HEAL:
            return "Лечение союзника."
        elif action.action_type == ActionType.BUFF:
            return "Усиление союзников."
        elif action.action_type == ActionType.FLEE:
            return "Попытка отступить."
        elif action.action_type == ActionType.REPOSITION:
            return "Смена позиции."
        return "Действие."

    def get_state(self) -> dict:
        return {
            "creatures": {cid: ai.to_dict() for cid, ai in self.creatures.items()},
            "log": self.combat_log[-10:],
        }

    def reset(self):
        self.creatures.clear()
        self.combat_log.clear()


MONSTER_BEHAVIORS = {
    "rat": BehaviorPattern.MINDLESS,
    "spider": BehaviorPattern.AMBUSH,
    "wolf": BehaviorPattern.PACK,
    "goblin": BehaviorPattern.COWARD,
    "skeleton": BehaviorPattern.AGGRO,
    "zombie": BehaviorPattern.MINDLESS,
    "bandit": BehaviorPattern.RANGED,
    "orc": BehaviorPattern.AGGRO,
    "troll": BehaviorPattern.AGGRO,
    "skeleton_mage": BehaviorPattern.CASTER,
}


def get_monster_behavior(monster_id: str) -> BehaviorPattern:
    return MONSTER_BEHAVIORS.get(monster_id, BehaviorPattern.MINDLESS)

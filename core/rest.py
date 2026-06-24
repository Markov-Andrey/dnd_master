"""Отдых: короткий/длинный отдых, восстановление HP,spell slots, исцеление."""
import random
from dataclasses import dataclass, field


class RestType:
    SHORT = "short"
    LONG = "long"


@dataclass
class RestResult:
    rest_type: str
    hp_healed: int = 0
    spells_restored: bool = False
    conditions_removed: list = field(default_factory=list)
    exhaustion_removed: bool = False
    message: str = ""
    random_event: str = ""


RANDOM_EVENTS = {
    "long": [
        {"chance": 0.1, "event": "none", "message": ""},
        {"chance": 0.05, "event": "ambush", "message": "Вас атаковали во сне!"},
        {"chance": 0.05, "event": "dream", "message": "Вы видите странный сон..."},
        {"chance": 0.03, "event": "treasure", "message": "Вы нашли спрятанный предмет рядом с лагерем!"},
    ],
    "short": [
        {"chance": 0.1, "event": "none", "message": ""},
        {"chance": 0.02, "event": "disturbance", "message": "Что-то шорохнулось в кустах..."},
    ],
}


def short_rest(player, hit_dice_count: int = 0) -> RestResult:
    result = RestResult(rest_type=RestType.SHORT)
    
    if hit_dice_count == 0:
        hit_dice_count = max(1, player.level if hasattr(player, 'level') else 1)
    
    total_healed = 0
    for _ in range(hit_dice_count):
        roll = random.randint(1, 8)
        con_mod = player.get_modifier("con") if hasattr(player, 'get_modifier') else 0
        healed = max(0, roll + con_mod)
        total_healed += healed
    
    result.hp_healed = min(total_healed, player.max_hp - player.hp) if hasattr(player, 'max_hp') else total_healed
    
    if hasattr(player, 'hp') and hasattr(player, 'max_hp'):
        player.hp = min(player.max_hp, player.hp + result.hp_healed)
    
    result.message = f"Короткий отдых. Восстановлено {result.hp_healed} HP."
    
    roll = random.random()
    cumulative = 0
    for evt in RANDOM_EVENTS["short"]:
        cumulative += evt["chance"]
        if roll <= cumulative:
            result.random_event = evt["event"]
            result.message += f"\n{evt['message']}" if evt["message"] else ""
            break
    
    return result


def long_rest(player) -> RestResult:
    result = RestResult(rest_type=RestType.LONG)
    
    if hasattr(player, 'hp') and hasattr(player, 'max_hp'):
        result.hp_healed = player.max_hp - player.hp
        player.hp = player.max_hp
    
    result.spells_restored = True
    
    if hasattr(player, 'conditions'):
        removable = ["poisoned", "frightened", "charmed"]
        for cond in list(player.conditions):
            if cond in removable:
                result.conditions_removed.append(cond)
                player.conditions.remove(cond)
    
    if hasattr(player, 'exhaustion') and player.exhaustion > 0:
        player.exhaustion -= 1
        result.exhaustion_removed = True
    
    result.message = f"Длинный отдых. HP полностью восстановлены."
    if result.spells_restored:
        result.message += " Заклинания восстановлены."
    if result.conditions_removed:
        result.message += f" Снято: {', '.join(result.conditions_removed)}."
    
    roll = random.random()
    cumulative = 0
    for evt in RANDOM_EVENTS["long"]:
        cumulative += evt["chance"]
        if roll <= cumulative:
            result.random_event = evt["event"]
            result.message += f"\n{evt['message']}" if evt["message"] else ""
            break
    
    return result


def can_rest(location_id: str, rest_type: str) -> tuple[bool, str]:
    safe_locations = ["village"]
    risky_locations = ["forest", "mountain", "crossroads"]
    danger_locations = ["cave", "ruins", "swamp"]
    no_rest_locations = ["lake"]
    
    if location_id in no_rest_locations:
        return False, "Здесь нельзя отдохнуть."
    
    if location_id in safe_locations:
        return True, "Безопасное место для отдыха."
    
    if rest_type == RestType.LONG:
        if location_id in danger_locations:
            return True, "Опасное место. Длинный отдых может быть прерван!"
        if location_id in risky_locations:
            return True, "Можно отдохнуть, но есть риск."
    
    return True, "Можно отдохнуть."


def get_exhaustion_effects(level: int) -> dict:
    effects = {
        1: {"disadvantage": "ability_checks", "message": "Невы advantage на проверках характеристик"},
        2: {"disadvantage": "attack_and_saves", "message": "Невы advantage на атаках и спасениях"},
        3: {"penalty": "half_speed", "message": "Скорость разделена на 2"},
        4: {"penalty": "half_hp_max", "message": "Макс. HP разделены на 2"},
        5: {"penalty": "zero_speed", "message": "Скорость = 0"},
        6: {"penalty": "death", "message": "Смерть"},
    }
    return effects.get(level, {"message": "Нет эффектов"})

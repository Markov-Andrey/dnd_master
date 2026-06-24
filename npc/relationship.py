"""Отношения: детекция действий, дельты ±2, текстовые метки."""
from core.config import RELATIONSHIP_LEVELS, LOVE_LEVELS, RELATIONSHIP_DELTAS

_ACTION_TRIGGERS = {
    "greet": ["привет", "здравствуй", "добрый день", "хай"],
    "insult": ["груби", "идиот", "тупой", "ненавижу", "убь"],
    "help": ["помоги", "спаси", "вытащи", "защити"],
    "betray": ["обман", "предаю", "враг", "сдаю"],
    "compliment": ["красив", "умн", "классн", "молодец", "хорош"],
    "apologize": ["извини", "прости", "сожалею", "вино"],
    "forgive": ["прощаю", "не бери в голову", "всё норм"],
    "fear_trigger": ["боюсь", "ужас", "страшно"],
    "like_trigger": ["нравится", "люблю", "хочу", "мечтаю"],
}

_TRAIT_MODS = {
    "friendship": {
        ("мстительный", -1), ("прощающий", +1), ("добрый", +1), ("злой", -1),
    },
    "love": {
        ("романтик", +1), ("холодный", -1),
    },
}


def _level(value, table): return next((k for k, (lo, hi) in table.items() if lo <= value <= hi), list(table.keys())[0])


def get_relationship_level(f): return _level(f, RELATIONSHIP_LEVELS)
def get_love_level(l): return _level(l, LOVE_LEVELS)


def _calc_delta(action, traits, trait_mods):
    base = RELATIONSHIP_DELTAS.get(action, 0)
    if base == 0 or not traits: return max(-2, min(2, base))
    for trait, mod in trait_mods:
        if trait in traits:
            base += mod if base != 0 else 0
    return max(-2, min(2, base))


def detect_action(msg: str, _mood: str) -> str:
    lower = msg.lower()
    for action, triggers in _ACTION_TRIGGERS.items():
        if any(t in lower for t in triggers): return action
    return "talk"


def evaluate_relationship_change(action, traits=None):
    return {
        "friendship_delta": _calc_delta(action, traits, _TRAIT_MODS["friendship"]),
        "love_delta": _calc_delta(action, traits, _TRAIT_MODS["love"]),
    }

"""Эмоции: привязка к действиям и уровням отношений, затухание за 3 хода."""
from core.config import EMOTION_DECAY

_ACTION_EMOTION = {
    "insult": "злой", "help": "рад", "betray": "грустный",
    "fear_trigger": "испуганный", "apologize": "спокоен",
}


def get_emotion_for_action(action, friendship, love=0):
    if action in _ACTION_EMOTION: return _ACTION_EMOTION[action]
    if action == "compliment" and friendship > 20: return "рад"
    if action == "like_trigger" and (friendship > 40 or love > 30): return "влюблён"
    if action == "compliment" and love > 50: return "влюблён"
    return None


def should_decay_emotion(turns): return turns >= EMOTION_DECAY


def decay_emotion(current):
    return "спокоен" if current in ("рад", "грустный", "злой", "испуганный", "скучающий", "влюблён") else current


def build_emotion_text(mood, turns):
    if turns == 1: return f" (ещё немного {mood})"
    if turns == 2: return " (начинает успокаиваться)"
    return ""

"""Память: классификация, веса, удаление ошибок, прощение."""
from core.config import MEMORY_WEIGHTS, MEMORY_MISTAKE_DECAY, MEMORY_FORGIVE_BONUS

_NO_MEMORY = {"greet", "talk"}
_MISTAKES = {"betray", "insult"}
_EMOTIONALS = {"help", "compliment", "apologize", "forgive"}


def classify_memory(text, action=None):
    if action in _MISTAKES: return "mistake"
    if action in _EMOTIONALS: return "emotional"
    if action in _NO_MEMORY: return None
    return "important"


def get_memory_weight(cat): return MEMORY_WEIGHTS.get(cat, 0.3)


def apply_forgiveness(memories, action):
    if action not in ("apologize", "forgive"): return memories
    for m in memories:
        if m.get("category") == "mistake":
            m["weight"] = min(1.0, m.get("weight", 0.1) + MEMORY_FORGIVE_BONUS)
    return memories


def decay_mistakes(memories, msg_count):
    return [m for m in memories if m.get("category") != "mistake"
            or (msg_count - m.get("msg_index", 0) < MEMORY_MISTAKE_DECAY
                and (m.update(weight=max(0.05, m["weight"] * 0.9)) or True))]


def build_memory_text(memories, limit=5):
    top = sorted(memories, key=lambda m: m.get("weight", 0), reverse=True)[:limit]
    return "\n".join(f"{'Важно:' if m.get('weight', 0) >= 0.7 else 'Помню:' if m.get('weight', 0) >= 0.4 else 'Ещё:'} {m.get('text', '')}" for m in top)

"""NPC-модель: данные, сериализация, диалог, квесты."""
import uuid, json, os
from core.config import NPCS_DB_DIR


def _clamp(v, lo=-100, hi=100): return max(lo, min(hi, v))


def _normalize_quest(q):
    """Приводим старый формат (строка) к новому (dict с статусом)."""
    if isinstance(q, str):
        return {"text": q, "status": "active"}
    return q


class NPC:
    def __init__(self, **kw):
        self.id = kw.get("npc_id") or f"npc_{uuid.uuid4().hex[:8]}"
        self.name = kw.get("name")
        self.name_known = kw.get("name_known", False)
        self.personality = kw.get("personality") or {}
        self.background = kw.get("background", "")
        self.preferences = kw.get("preferences") or {"likes": [], "dislikes": [], "fears": []}
        self.mood = kw.get("mood", "спокоен")
        self.relationships = kw.get("relationships") or {"friendship": 0, "love": 0}
        self.relations = kw.get("relations") or {}
        self.dialogue_history = kw.get("dialogue_history") or []
        self.current_summary = kw.get("current_summary", "")
        self.is_in_dialogue = kw.get("is_in_dialogue", False)
        self.lore = kw.get("lore", "")
        raw_quests = kw.get("quest_hooks") or []
        self.quest_hooks = [_normalize_quest(q) for q in raw_quests]
        self.portrait = kw.get("portrait", "")
        self.config_name = kw.get("config_name")
        self.emotion_turns = kw.get("emotion_turns", 0)
        self.memories = kw.get("memories") or []
        self.msg_count = kw.get("msg_count", 0)

    @classmethod
    def from_config(cls, path: str) -> "NPC":
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        cfg = os.path.basename(path)
        npc_id = data.get("npc_id") or f"npc_{uuid.uuid5(uuid.NAMESPACE_URL, cfg).hex[:8]}"
        return cls(
            npc_id=npc_id,
            config_name=cfg, **{k: data.get(k) for k in (
                "name", "name_known", "personality", "background", "preferences",
                "mood", "relationships", "relations", "lore", "quest_hooks", "portrait",
            )}
        )

    def to_dict(self) -> dict:
        from npc.relationship import get_relationship_level, get_love_level
        d = {k: getattr(self, k) for k in (
            "id", "name", "name_known", "personality", "background", "preferences",
            "mood", "relationships", "relations", "emotion_turns", "memories", "msg_count",
            "dialogue_history", "current_summary", "is_in_dialogue", "lore",
            "quest_hooks", "config_name", "portrait",
        )}
        d["relation_level"] = get_relationship_level(self.relationships["friendship"])
        d["love_level"] = get_love_level(self.relationships["love"])
        return d

    def get_active_quests(self):
        return [q for q in self.quest_hooks if q.get("status") == "active"]

    def get_quest_texts(self, status=None):
        quests = self.quest_hooks if status is None else [q for q in self.quest_hooks if q.get("status") == status]
        return [q["text"] for q in quests]

    def adjust_relationship(self, friendship_delta=0, love_delta=0):
        self.relationships["friendship"] = _clamp(self.relationships["friendship"] + friendship_delta)
        self.relationships["love"] = _clamp(self.relationships["love"] + love_delta)

    def add_message(self, role, content):
        self.dialogue_history.append({"role": role, "content": content})

    def start_dialogue(self):
        self.is_in_dialogue = True
        self.dialogue_history = []

    def end_dialogue(self):
        self.is_in_dialogue = False

    def save(self):
        os.makedirs(NPCS_DB_DIR, exist_ok=True)
        with open(os.path.join(NPCS_DB_DIR, f"{self.id}.json"), "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)

    @classmethod
    def load(cls, npc_id: str) -> "NPC | None":
        path = os.path.join(NPCS_DB_DIR, f"{npc_id}.json")
        if not os.path.exists(path): return None
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return cls(npc_id=data["id"], **{k: data.get(k) for k in (
            "name", "name_known", "personality", "background", "preferences",
            "mood", "relationships", "relations", "dialogue_history", "current_summary",
            "is_in_dialogue", "lore", "quest_hooks", "config_name",
            "emotion_turns", "memories", "msg_count", "portrait",
        )})

    @classmethod
    def load_all(cls) -> dict[str, "NPC"]:
        if not os.path.exists(NPCS_DB_DIR): return {}
        return {n.id: n for f in os.listdir(NPCS_DB_DIR) if f.endswith(".json")
                if (n := cls.load(f[:-5])) is not None}

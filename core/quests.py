"""Квестовая система: выдача, прогресс, награда, привязка к локациям."""
import random
from dataclasses import dataclass, field
from enum import Enum


class QuestStatus(Enum):
    AVAILABLE = "available"
    ACTIVE = "active"
    COMPLETED = "completed"
    FAILED = "failed"


class QuestType(Enum):
    KILL = "kill"
    COLLECT = "collect"
    TALK = "talk"
    EXPLORE = "explore"
    ESCORT = "escort"
    DELIVER = "deliver"
    BOSS = "boss"


@dataclass
class QuestObjective:
    type: QuestType
    target: str
    description: str
    current: int = 0
    required: int = 1
    is_complete: bool = False
    
    def progress(self, amount: int = 1):
        self.current = min(self.current + amount, self.required)
        self.is_complete = self.current >= self.required
    
    def to_dict(self):
        return {
            "type": self.type.value, "target": self.target,
            "description": self.description,
            "current": self.current, "required": self.required,
            "is_complete": self.is_complete,
        }


@dataclass
class QuestReward:
    xp: int = 0
    gold: int = 0
    items: list = field(default_factory=list)
    reputation: int = 0
    unlock_location: str = ""
    
    def to_dict(self):
        return {
            "xp": self.xp, "gold": self.gold,
            "items": self.items, "reputation": self.reputation,
            "unlock_location": self.unlock_location,
        }


@dataclass
class Quest:
    id: str
    name: str
    description: str
    giver_npc: str = ""
    location: str = ""
    objectives: list[QuestObjective] = field(default_factory=list)
    rewards: QuestReward = field(default_factory=QuestReward)
    status: QuestStatus = QuestStatus.AVAILABLE
    level_required: int = 1
    prerequisites: list[str] = field(default_factory=list)
    
    def check_completion(self) -> bool:
        return all(obj.is_complete for obj in self.objectives)
    
    def get_progress_text(self) -> str:
        lines = []
        for obj in self.objectives:
            status = "✓" if obj.is_complete else f"{obj.current}/{obj.required}"
            lines.append(f"  {status} {obj.description}")
        return "\n".join(lines)
    
    def to_dict(self):
        return {
            "id": self.id, "name": self.name, "description": self.description,
            "giver_npc": self.giver_npc, "location": self.location,
            "objectives": [o.to_dict() for o in self.objectives],
            "rewards": self.rewards.to_dict(),
            "status": self.status.value,
            "level_required": self.level_required,
        }


QUEST_TEMPLATES = {
    "goblin_hunt": Quest(
        id="goblin_hunt",
        name="Охота на гоблинов",
        description="Гоблины беспокоят деревню. Убейте 3 гоблинов в лесу.",
        giver_npc="npc_kira",
        location="forest",
        objectives=[QuestObjective(QuestType.KILL, "goblin", "Убить гоблинов", 0, 3)],
        rewards=QuestReward(xp=100, gold=50, items=["healing_potion"]),
        level_required=1,
    ),
    "skeleton_cave": Quest(
        id="skeleton_cave",
        name="Скелеты в пещере",
        description="В пещере завелись скелеты. Разберитесь с ними.",
        giver_npc="npc_kira",
        location="cave",
        objectives=[QuestObjective(QuestType.KILL, "skeleton", "Убить скелетов", 0, 4)],
        rewards=QuestReward(xp=150, gold=75, items=["dagger"]),
        level_required=2,
    ),
    "find_herbs": Quest(
        id="find_herbs",
        name="Поиск трав",
        description="Алхимику нужны редкие травы. Найдите их в лесу.",
        giver_npc="npc_kira",
        location="forest",
        objectives=[QuestObjective(QuestType.COLLECT, "herb", "Найти травы", 0, 5)],
        rewards=QuestReward(xp=75, gold=30, items=["healing_potion", "healing_potion"]),
        level_required=1,
    ),
    "explore_ruins": Quest(
        id="explore_ruins",
        name="Исследование руин",
        description="Древние руины хранят секреты. Исследуйте их.",
        giver_npc="npc_kira",
        location="ruins",
        objectives=[QuestObjective(QuestType.EXPLORE, "ruins", "Исследовать руины", 0, 1)],
        rewards=QuestReward(xp=200, gold=100),
        level_required=3,
    ),
    "bandit_problem": Quest(
        id="bandit_problem",
        name="Проблема с бандитами",
        description="Бандиты орудуют у развилки. Найдите их лагерь.",
        giver_npc="npc_kira",
        location="crossroads",
        objectives=[
            QuestObjective(QuestType.KILL, "bandit", "Убить бандитов", 0, 3),
            QuestObjective(QuestType.EXPLORE, "bandit_camp", "Найти лагерь", 0, 1),
        ],
        rewards=QuestReward(xp=250, gold=150, items=["gold_chest"]),
        level_required=4,
    ),
    "orc_warcamp": Quest(
        id="orc_warcamp",
        name="Лагерь орков",
        description="Орки устроили лагерь в горах. Уничтожьте их вожака.",
        giver_npc="npc_kira",
        location="mountain",
        objectives=[
            QuestObjective(QuestType.KILL, "orc", "Убить орков", 0, 5),
            QuestObjective(QuestType.BOSS, "orc_chief", "Убить вожака", 0, 1),
        ],
        rewards=QuestReward(xp=500, gold=300, items=["great_axe", "gold_chest"]),
        level_required=6,
    ),
    "wolf_pelts": Quest(
        id="wolf_pelts",
        name="Шкуры волков",
        description="Торговец покупает шкуры волков. Принесите 3 шкуры.",
        giver_npc="npc_kira",
        location="forest",
        objectives=[QuestObjective(QuestType.COLLECT, "wolf_pelt", "Собрать шкуры", 0, 3)],
        rewards=QuestReward(xp=60, gold=45),
        level_required=1,
    ),
    "mysterious_artifact": Quest(
        id="mysterious_artifact",
        name="Загадочный артефакт",
        description="В руинах спрятан древний артефакт. Найдите его.",
        giver_npc="npc_kira",
        location="ruins",
        objectives=[QuestObjective(QuestType.EXPLORE, "artifact", "Найти артефакт", 0, 1)],
        rewards=QuestReward(xp=400, gold=200, items=["magic_ring"]),
        level_required=5,
    ),
}


class QuestManager:
    def __init__(self):
        self.quests: dict[str, Quest] = {}
        self.active_quests: list[str] = []
        self.completed_quests: list[str] = []
    
    def load_templates(self):
        for qid, tmpl in QUEST_TEMPLATES.items():
            if qid not in self.quests:
                import copy
                self.quests[qid] = copy.deepcopy(tmpl)
    
    def get_available_quests(self, player_level: int = 1, location: str = "") -> list[Quest]:
        available = []
        for q in self.quests.values():
            if q.status != QuestStatus.AVAILABLE:
                continue
            if q.level_required > player_level:
                continue
            if q.location and q.location != location and location:
                continue
            prereqs_met = all(p in self.completed_quests for p in q.prerequisites)
            if not prereqs_met:
                continue
            available.append(q)
        return available
    
    def accept_quest(self, quest_id: str) -> tuple[bool, str]:
        q = self.quests.get(quest_id)
        if not q:
            return False, "Квест не найден."
        if q.status != QuestStatus.AVAILABLE:
            return False, "Квест уже взят или завершён."
        
        q.status = QuestStatus.ACTIVE
        self.active_quests.append(quest_id)
        return True, f"Квест принят: {q.name}"
    
    def update_quest_progress(self, event_type: str, target: str, amount: int = 1) -> list[dict]:
        updates = []
        for qid in self.active_quests:
            q = self.quests.get(qid)
            if not q or q.status != QuestStatus.ACTIVE:
                continue
            
            for obj in q.objectives:
                if obj.type.value == event_type and obj.target == target and not obj.is_complete:
                    obj.progress(amount)
                    updates.append({
                        "quest": q.name,
                        "objective": obj.description,
                        "progress": f"{obj.current}/{obj.required}",
                        "complete": obj.is_complete,
                    })
            
            if q.check_completion():
                q.status = QuestStatus.COMPLETED
                self.completed_quests.append(qid)
                updates.append({
                    "quest": q.name,
                    "complete": True,
                    "rewards": q.rewards.to_dict(),
                })
        
        return updates
    
    def get_active_quests(self) -> list[Quest]:
        return [self.quests[qid] for qid in self.active_quests if qid in self.quests]
    
    def get_completed_quests(self) -> list[Quest]:
        return [self.quests[qid] for qid in self.completed_quests if qid in self.quests]
    
    def to_dict(self):
        return {
            "available": [q.to_dict() for q in self.get_available_quests(99)],
            "active": [q.to_dict() for q in self.get_active_quests()],
            "completed": [q.to_dict() for q in self.get_completed_quests()],
        }

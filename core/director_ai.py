"""AI Director v2: Left 4 Dead стиль.

Умная система управления интенсивностью:
- Pacing: отслеживает интенсивность во времени
- Context: решения на основе множества факторов
- Debug: полный лог рассуждений
- Anti-frustration: не забрасывает, даёт передышки
- Narrative: события связаны с контекстом
"""
import random
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Callable


class DirectorMood(Enum):
    CALM = "calm"
    TENSION = "tension"
    ACTION = "action"
    REWARD = "reward"
    DRAMA = "drama"
    MYSTERY = "mystery"


class EventType(Enum):
    RANDOM_ENCOUNTER = "random_encounter"
    WEATHER_CHANGE = "weather_change"
    NPC_APPEAR = "npc_appear"
    LOOT_DROP = "loot_drop"
    TRAP_TRIGGER = "trap_trigger"
    AMBIENT_SOUND = "ambient_sound"
    QUEST_HINT = "quest_hint"
    DANGER_WARNING = "danger_warning"
    SAFE_ZONE = "safe_zone"
    TREASURE_FOUND = "treasure_found"
    STORY_EVENT = "story_event"
    DIFFICULTY_UP = "difficulty_up"
    DIFFICULTY_DOWN = "difficulty_down"
    HEALING_SPRING = "healing_spring"
    MYSTERIOUS_NPC = "mysterious_npc"


@dataclass
class DirectorEvent:
    event_type: EventType
    title: str
    description: str
    data: dict = field(default_factory=dict)
    priority: int = 0
    reasoning: str = ""
    timestamp: float = field(default_factory=time.time)


@dataclass
class PlayerMetrics:
    hp_percent: float = 1.0
    level: int = 1
    locations_visited: int = 1
    total_kills: int = 0
    total_deaths: int = 0
    quests_completed: int = 0
    quests_active: int = 0
    gold: int = 0
    time_played_minutes: int = 0
    recent_combats: int = 0
    recent_losses: int = 0
    exploration_score: float = 0.5
    boredom_score: float = 0.0
    tension_score: float = 0.0
    consecutive_wins: int = 0
    consecutive_losses: int = 0
    items_collected: int = 0
    puzzles_solved: int = 0
    traps_triggered: int = 0
    distance_traveled: int = 0


@dataclass
class DirectorConfig:
    encounter_rate: float = 0.3
    difficulty_scale: float = 1.0
    tension_decay: float = 0.1
    boredom_threshold: float = 0.7
    tension_threshold: float = 0.8
    min_time_between_events: float = 8.0
    max_events_per_minute: int = 2
    pacing_window: int = 300
    target_intensity: float = 0.6


@dataclass
class DebugEntry:
    timestamp: float
    reasoning: str
    decision: str
    factors: dict
    mood_before: str
    mood_after: str


class AIDirector:
    def __init__(self, config: DirectorConfig | None = None):
        self.config = config or DirectorConfig()
        self.mood = DirectorMood.CALM
        self.metrics = PlayerMetrics()
        self.event_history: list[DirectorEvent] = []
        self.debug_log: list[DebugEntry] = []
        self.last_event_time: float = 0
        self.events_this_minute: int = 0
        self.minute_start: float = time.time()
        self.is_active: bool = True
        self.hooks: dict[EventType, list[Callable]] = {}
        self.intensity_history: list[float] = []
        self.pacing_phase: str = "buildup"
        self.last_combat_time: float = 0
        self.last_reward_time: float = 0
        self.session_start: float = time.time()

    def register_hook(self, event_type: EventType, callback: Callable):
        if event_type not in self.hooks:
            self.hooks[event_type] = []
        self.hooks[event_type].append(callback)

    def update_metrics(self, **kwargs):
        for key, value in kwargs.items():
            if hasattr(self.metrics, key):
                setattr(self.metrics, key, value)
        self._recalculate_scores()

    def _recalculate_scores(self):
        m = self.metrics
        now = time.time()

        if m.recent_combats > 3:
            m.tension_score = min(1.0, m.tension_score + 0.2)
        else:
            m.tension_score = max(0.0, m.tension_score - self.config.tension_decay)

        if m.recent_losses > 1:
            m.tension_score = max(0.0, m.tension_score - 0.3)
            m.consecutive_losses += 1
            m.consecutive_wins = 0
        elif m.recent_combats > 0:
            m.consecutive_wins += 1
            m.consecutive_losses = 0

        idle_time = now - (self.event_history[-1].timestamp if self.event_history else now)
        if idle_time > 120:
            m.boredom_score = min(1.0, m.boredom_score + 0.15)
        elif idle_time > 60:
            m.boredom_score = min(1.0, m.boredom_score + 0.05)
        else:
            m.boredom_score = max(0.0, m.boredom_score - 0.08)

        if m.hp_percent < 0.3:
            m.tension_score = min(1.0, m.tension_score + 0.3)

        current_intensity = self._calculate_intensity()
        self.intensity_history.append(current_intensity)
        if len(self.intensity_history) > 60:
            self.intensity_history = self.intensity_history[-60:]

    def _calculate_intensity(self) -> float:
        m = self.metrics
        intensity = 0.0
        intensity += (1.0 - m.hp_percent) * 0.3
        intensity += m.tension_score * 0.25
        intensity += min(1.0, m.recent_combats / 5) * 0.2
        intensity += m.boredom_score * 0.15
        if m.consecutive_wins > 3:
            intensity += 0.1
        return min(1.0, intensity)

    def _get_average_intensity(self) -> float:
        if not self.intensity_history:
            return 0.5
        recent = self.intensity_history[-10:]
        return sum(recent) / len(recent)

    def _determine_pacing_phase(self):
        avg = self._get_average_intensity()
        target = self.config.target_intensity

        if avg < target - 0.2:
            self.pacing_phase = "buildup"
        elif avg > target + 0.2:
            self.pacing_phase = "cooldown"
        else:
            self.pacing_phase = "sustain"

    def _log_decision(self, reasoning: str, decision: str, factors: dict):
        entry = DebugEntry(
            timestamp=time.time(),
            reasoning=reasoning,
            decision=decision,
            factors=factors,
            mood_before=self.mood.value,
            mood_after=self.mood.value,
        )
        self.debug_log.append(entry)
        if len(self.debug_log) > 200:
            self.debug_log = self.debug_log[-200:]

    def evaluate(self) -> list[DirectorEvent]:
        if not self.is_active:
            return []

        now = time.time()
        if now - self.minute_start >= 60:
            self.events_this_minute = 0
            self.minute_start = now

        if self.events_this_minute >= self.config.max_events_per_minute:
            return []

        if now - self.last_event_time < self.config.min_time_between_events:
            return []

        self._determine_pacing_phase()
        old_mood = self.mood.value
        self._update_mood()

        events = []
        decisions = []

        e = self._evaluate_encounter()
        if e:
            events.extend(e)
            decisions.append(f"ENCOUNTER: {e[0].reasoning}")

        e = self._evaluate_difficulty()
        if e:
            events.extend(e)
            decisions.append(f"DIFFICULTY: {e[0].reasoning}")

        e = self._evaluate_reward()
        if e:
            events.extend(e)
            decisions.append(f"REWARD: {e[0].reasoning}")

        e = self._evaluate_story()
        if e:
            events.extend(e)
            decisions.append(f"STORY: {e[0].reasoning}")

        e = self._evaluate_environment()
        if e:
            events.extend(e)
            decisions.append(f"ENV: {e[0].reasoning}")

        e = self._evaluate_healing()
        if e:
            events.extend(e)
            decisions.append(f"HEAL: {e[0].reasoning}")

        for event in events:
            self.event_history.append(event)
            self.last_event_time = now
            self.events_this_minute += 1
            self._fire_hooks(event)

        if decisions:
            self._log_decision(
                reasoning=" | ".join(decisions),
                decision=f"{len(events)} events generated",
                factors={
                    "mood": self.mood.value,
                    "pacing": self.pacing_phase,
                    "intensity": round(self._calculate_intensity(), 2),
                    "avg_intensity": round(self._get_average_intensity(), 2),
                    "hp": round(self.metrics.hp_percent, 2),
                    "tension": round(self.metrics.tension_score, 2),
                    "boredom": round(self.metrics.boredom_score, 2),
                    "consecutive_wins": self.metrics.consecutive_wins,
                    "consecutive_losses": self.metrics.consecutive_losses,
                }
            )

        return events

    def _update_mood(self):
        m = self.metrics
        phase = self.pacing_phase

        if m.hp_percent < 0.25:
            self.mood = DirectorMood.TENSION
            return

        if phase == "cooldown":
            self.mood = DirectorMood.REWARD
        elif phase == "buildup":
            if m.boredom_score > 0.5:
                self.mood = DirectorMood.ACTION
            elif m.quests_active > 0:
                self.mood = DirectorMood.MYSTERY
            else:
                self.mood = DirectorMood.CALM
        else:
            if m.recent_combats > 2:
                self.mood = DirectorMood.ACTION
            else:
                self.mood = DirectorMood.CALM

    def _evaluate_encounter(self) -> list[DirectorEvent]:
        m = self.metrics
        now = time.time()
        rate = self.config.encounter_rate

        reasoning_parts = []

        if self.pacing_phase == "cooldown":
            rate *= 0.1
            reasoning_parts.append("фаза cooldown → минимальные встречи")
        elif self.pacing_phase == "buildup":
            rate *= 1.2
            reasoning_parts.append("фаза buildup → встречи нарастают")
        else:
            reasoning_parts.append("фаза sustain → стандартный темп")

        if m.hp_percent < 0.25:
            rate *= 0.05
            reasoning_parts.append(f"HP {m.hp_percent:.0%} → почти нет встреч")
        elif m.hp_percent < 0.5:
            rate *= 0.4
            reasoning_parts.append(f"HP {m.hp_percent:.0%} → мягкие встречи")

        if m.consecutive_wins > 4:
            rate *= 1.5
            reasoning_parts.append(f"серия побед {m.consecutive_wins} → увеличиваю挑战")
        elif m.consecutive_losses > 2:
            rate *= 0.3
            reasoning_parts.append(f"серия поражений {m.consecutive_losses} → уменьшаю встречи")

        if m.boredom_score > 0.6:
            rate *= 1.8
            reasoning_parts.append(f"скука {m.boredom_score:.0%} → провоцирую действие")

        time_since_combat = now - self.last_combat_time
        if time_since_combat < 30:
            rate *= 0.2
            reasoning_parts.append(f"бой {time_since_combat:.0f}с назад → пауза")
        elif time_since_combat > 180:
            rate *= 1.3
            reasoning_parts.append(f"боя нет {time_since_combat:.0f}с → пора")

        reasoning = "; ".join(reasoning_parts)

        if random.random() >= rate:
            self._log_decision(
                reasoning=f"ENCOUNTER skipped: {reasoning}",
                decision="no encounter",
                factors={"rate": round(rate, 3), "phase": self.pacing_phase}
            )
            return []

        difficulty = self.config.difficulty_scale
        if self.pacing_phase == "buildup":
            difficulty *= 0.8
        elif self.pacing_phase == "cooldown":
            difficulty *= 0.5

        if m.consecutive_wins > 3:
            difficulty *= 1.2
        if m.consecutive_losses > 2:
            difficulty *= 0.6

        monsters = self._select_encounter(difficulty)
        if not monsters:
            return []

        self.last_combat_time = now

        return [DirectorEvent(
            event_type=EventType.RANDOM_ENCOUNTER,
            title="Столкновение!",
            description=f"Вы наткнулись на: {', '.join(monsters)}",
            data={"monsters": monsters, "difficulty": difficulty},
            priority=5,
            reasoning=reasoning,
        )]

    def _select_encounter(self, difficulty: float) -> list[str]:
        if difficulty < 0.8:
            pool = ["rat", "spider"]
        elif difficulty < 1.2:
            pool = ["goblin", "skeleton", "wolf"]
        elif difficulty < 1.8:
            pool = ["orc", "bandit"]
        else:
            pool = ["troll", "skeleton_mage"]

        count = random.choices([1, 2, 3], weights=[50, 35, 15])[0]
        return [random.choice(pool) for _ in range(count)]

    def _evaluate_difficulty(self) -> list[DirectorEvent]:
        m = self.metrics
        old_scale = self.config.difficulty_scale

        if m.consecutive_losses >= 3 and self.config.difficulty_scale > 0.5:
            self.config.difficulty_scale = max(0.5, self.config.difficulty_scale - 0.15)
            return [DirectorEvent(
                event_type=EventType.DIFFICULTY_DOWN,
                title="Мир смягчается",
                description="Враги становятся слабее...",
                data={"old": old_scale, "new": self.config.difficulty_scale},
                priority=3,
                reasoning=f"серия поражений {m.consecutive_losses} → снижаю сложность",
            )]
        elif m.consecutive_wins > 5 and self.config.difficulty_scale < 2.0:
            self.config.difficulty_scale = min(2.0, self.config.difficulty_scale + 0.1)
            return [DirectorEvent(
                event_type=EventType.DIFFICULTY_UP,
                title="Мир жестче",
                description="Опасность растёт...",
                data={"old": old_scale, "new": self.config.difficulty_scale},
                priority=3,
                reasoning=f"серия побед {m.consecutive_wins} → повышаю сложность",
            )]
        return []

    def _evaluate_reward(self) -> list[DirectorEvent]:
        m = self.metrics
        now = time.time()
        events = []

        if self.pacing_phase == "cooldown" and m.hp_percent < 0.5:
            time_since_reward = now - self.last_reward_time
            if time_since_reward > 60:
                events.append(DirectorEvent(
                    event_type=EventType.TREASURE_FOUND,
                    title="Находка!",
                    description="Спрятанный сундук с зельями.",
                    data={"chest_type": "iron"},
                    priority=4,
                    reasoning=f"фаза cooldown, HP {m.hp_percent:.0%} → даю награду",
                ))
                self.last_reward_time = now

        if m.total_kills > 0 and m.total_kills % 10 == 0 and m.total_kills != getattr(self, '_last_kill_milestone', 0):
            events.append(DirectorEvent(
                event_type=EventType.LOOT_DROP,
                title="Добыча",
                description="Ценный трофей.",
                data={"loot_quality": "uncommon"},
                priority=3,
                reasoning=f"каждые 10 убийств → трофей",
            ))
            self._last_kill_milestone = m.total_kills

        return events

    def _evaluate_story(self) -> list[DirectorEvent]:
        m = self.metrics
        events = []

        if m.quests_completed > 0 and m.quests_active == 0 and random.random() < 0.1:
            events.append(DirectorEvent(
                event_type=EventType.STORY_EVENT,
                title="Загадочный шёпот",
                description="Тихий зов ветра...",
                priority=6,
                reasoning="квесты выполнены, нет активных → сюжетный хук",
            ))

        if m.time_played_minutes > 20 and m.quests_completed == 0 and random.random() < 0.15:
            events.append(DirectorEvent(
                event_type=EventType.QUEST_HINT,
                title="Подсказка",
                description="Старик намекнул на место...",
                priority=4,
                reasoning=f"игрок {m.time_played_minutes}мин без квестов → подсказка",
            ))

        return events

    def _evaluate_environment(self) -> list[DirectorEvent]:
        m = self.metrics
        if random.random() > 0.06:
            return []

        if m.tension_score > 0.6:
            sounds = [
                ("Тишина", "Неприятная тишина..."),
                ("Треск", "Кто-то наступил на ветку..."),
                ("Шёпот", "Едва слышный шёпот..."),
            ]
        elif m.boredom_score > 0.5:
            sounds = [
                ("Птицы", "Птицы поют весело"),
                ("Ручей", "Журчит ручей"),
                ("Ветер", "Мягкий ветерок"),
            ]
        else:
            sounds = [
                ("Звуки леса", "Птицы вдали"),
                ("Ветер", "Ветер между деревьями"),
            ]

        title, desc = random.choice(sounds)
        return [DirectorEvent(
            event_type=EventType.AMBIENT_SOUND,
            title=title,
            description=desc,
            priority=1,
            reasoning=f"настроение {self.mood.value} → подбираю звук",
        )]

    def _evaluate_healing(self) -> list[DirectorEvent]:
        m = self.metrics
        if m.hp_percent > 0.4:
            return []
        if self.pacing_phase != "cooldown":
            return []
        if random.random() > 0.3:
            return []

        return [DirectorEvent(
            event_type=EventType.HEALING_SPRING,
            title="Целебный источник",
            description="Вы нашли родник с целебной водой.",
            data={"heal_amount": int(m.hp_percent * 30 + 20)},
            priority=5,
            reasoning=f"HP {m.hp_percent:.0%}, фаза cooldown → исцеление",
        )]

    def _fire_hooks(self, event: DirectorEvent):
        for callback in self.hooks.get(event.event_type, []):
            try:
                callback(event)
            except Exception:
                pass

    def get_state(self) -> dict:
        return {
            "mood": self.mood.value,
            "is_active": self.is_active,
            "pacing_phase": self.pacing_phase,
            "difficulty_scale": round(self.config.difficulty_scale, 2),
            "intensity": round(self._calculate_intensity(), 2),
            "avg_intensity": round(self._get_average_intensity(), 2),
            "target_intensity": self.config.target_intensity,
            "metrics": {
                "hp_percent": round(self.metrics.hp_percent, 2),
                "level": self.metrics.level,
                "tension_score": round(self.metrics.tension_score, 2),
                "boredom_score": round(self.metrics.boredom_score, 2),
                "exploration_score": round(self.metrics.exploration_score, 2),
                "total_kills": self.metrics.total_kills,
                "total_deaths": self.metrics.total_deaths,
                "consecutive_wins": self.metrics.consecutive_wins,
                "consecutive_losses": self.metrics.consecutive_losses,
                "quests_completed": self.metrics.quests_completed,
                "quests_active": self.metrics.quests_active,
                "items_collected": self.metrics.items_collected,
                "distance_traveled": self.metrics.distance_traveled,
                "time_played_minutes": self.metrics.time_played_minutes,
            },
            "recent_events": [
                {"type": e.event_type.value, "title": e.title, "reasoning": e.reasoning}
                for e in self.event_history[-5:]
            ],
        }

    def get_debug_state(self) -> dict:
        return {
            **self.get_state(),
            "debug_log": [
                {
                    "time": time.strftime("%H:%M:%S", time.localtime(e.timestamp)),
                    "reasoning": e.reasoning,
                    "decision": e.decision,
                    "factors": e.factors,
                    "mood": f"{e.mood_before} → {e.mood_after}",
                }
                for e in self.debug_log[-20:]
            ],
            "intensity_history": [round(i, 2) for i in self.intensity_history[-30:]],
        }

    def toggle(self):
        self.is_active = not self.is_active
        return self.is_active

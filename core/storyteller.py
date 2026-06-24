"""Storyteller: ИИ модуль генерации сюжета.

Генерирует целостную историю с:
- Макетом сюжета (акты, кульминации, развязки)
- Локациями, связанными с сюжетом
- NPC с ролями в истории
- Квестами, вытекающими из сюжета
- Сюжетными перепитиями и твистами
"""
import json
from dataclasses import dataclass, field
from enum import Enum
from core import llm_client


class StoryAct(Enum):
    PROLOGUE = "prologue"
    ACT_1 = "act_1"
    ACT_2 = "act_2"
    CLIMAX = "climax"
    RESOLUTION = "resolution"


class NpcRole(Enum):
    HERO = "hero"
    VILLAIN = "villain"
    MENTOR = "mentor"
    RIVAL = "rival"
    LOVE_INTEREST = "love_interest"
    MERCHANT = "merchant"
    INNKEEPER = "innkeeper"
    QUEST_GIVER = "quest_giver"
    TRAITOR = "traitor"
    MYSTERIOUS = "mysterious"
    SIDEKICK = "sidekick"
    GUARD = "guard"


class PlotTwistType(Enum):
    BETRAYAL = "betrayal"
    SECRET_IDENTITY = "secret_identity"
    HIDDEN_TRUTH = "hidden_truth"
    UNLIKELY_ALLY = "unlikely_ally"
    SACRIFICE = "sacrifice"
    REVERSAL = "reversal"
    REVELATION = "revelation"


@dataclass
class StoryBeat:
    act: StoryAct
    title: str
    description: str
    location_id: str
    involved_npcs: list[str] = field(default_factory=list)
    quest_id: str = ""
    twist: str = ""
    emotional_tone: str = ""


@dataclass
class StoryArc:
    title: str
    premise: str
    setting: str
    theme: str
    acts: list[StoryBeat] = field(default_factory=list)
    locations: list[dict] = field(default_factory=list)
    npcs: list[dict] = field(default_factory=list)
    quests: list[dict] = field(default_factory=list)
    twists: list[dict] = field(default_factory=list)
    main_quest_chain: list[str] = field(default_factory=list)

    def to_dict(self):
        return {
            "title": self.title,
            "premise": self.premise,
            "setting": self.setting,
            "theme": self.theme,
            "acts": [{"act": a.act.value, "title": a.title, "description": a.description,
                       "location_id": a.location_id, "twist": a.twist,
                       "emotional_tone": a.emotional_tone} for a in self.acts],
            "locations": self.locations,
            "npcs": self.npcs,
            "quests": self.quests,
            "twists": self.twists,
            "main_quest_chain": self.main_quest_chain,
        }


# ─── Промпты ──────────────────────────────────────────────────────────────

PREMISE_PROMPT = """Ты — сценарист RPG. Придумай ОДНУ историю.

Жанр: фэнтези, D&D 5e
Формат: 5 актов (пролог, 2 действия, кульминация, развязка)

Ответь СТРОГО JSON:
{
  "title": "Название истории (2-4 слова)",
  "premise": "Завязка: что происходит (2-3 предложения)",
  "setting": "Мир/регион (1 предложение)",
  "theme": "Тема: месть, спасение, поиск, тайна (1 слово)"
}

Правила:
- История должна быть масштабной (5-8 часов геймплея)
- Должен быть главный злодей и интрига
- Минимум 2 сюжетных твиста
- Локации связаны с сюжетом"""

LOCATIONS_PROMPT = """Ты — локейшн-дизайнер RPG. Создай локации для истории.

История: {title}
Завязка: {premise}
Тема: {theme}

Создай 6-8 локаций. Строго JSON:
{{
  "locations": [
    {{
      "id": "location_id",
      "name": "Название",
      "description": "Описание 1-2 предложения",
      "tile_color": "#RRGGBB",
      "role": "role из: home/town/wilderness/dungeon/sacred/secret/boss_lair",
      "story_importance": "high/medium/low",
      "exits": {{"north": "other_id", "south": "other_id"}}
    }}
  ]
}}

Правила:
- Первая локация — стартовая (деревня/город)
- Последняя — место финальной битвы
- Есть "секретная" локация
- Выходы связывают локации в граф
- Цвета: зелёный=лес, коричневый=город, серый=пещера, синий=вода, красный=опасность"""

NPCS_PROMPT = """Ты — создатель персонажей RPG. Создай NPC для истории.

История: {title}
Локации: {locations}

Создай 6-8 NPC. Строго JSON:
{{
  "npcs": [
    {{
      "id": "npc_id",
      "name": "Имя",
      "personality": {{"core": "Суть характера", "traits": ["черта1", "черта2"]}},
      "background": "Предыстория 2 предложения",
      "role": "role из: hero/villain/mentor/rival/love_interest/merchant/quest_giver/traitor/mysterious/sidekick",
      "location_id": "location_id",
      "quest_gives": "quest_id или пусто",
      "secret": "Секрет персонажа (1 предложение)",
      "arc": "Как меняется персонаж: start → end"
    }}
  ]
}}

Правила:
- 1 главный герой (не игрок), 1 злодей
- Есть предатель
- Есть наставник
- Каждый NPC связан с историей
- У каждого есть секрет"""

QUESTS_PROMPT = """Ты — квест-дизайнер RPG. Создай квестовую цепочку.

История: {title}
NPC: {npcs}
Локации: {locations}

Создай 8-10 квестов (5 основных + 3-5 побочных). Строго JSON:
{{
  "quests": [
    {{
      "id": "quest_id",
      "name": "Название квеста",
      "description": "Описание 2 предложения",
      "type": "kill/collect/talk/explore/boss/deliver/investigate",
      "giver_npc": "npc_id",
      "location": "location_id",
      "target": "цель (монстр/предмет/NPC/локация)",
      "target_count": 1,
      "rewards": {{"xp": 100, "gold": 50}},
      "prerequisite": "quest_id или пусто",
      "story_importance": "main/side",
      "act": "prologue/act_1/act_2/climax/resolution"
    }}
  ]
}}

Правила:
- Квесты идут по порядку актов
- Первый квест — туториал
- Последний — финальный босс
- Есть побочные квесты с наградами
- Квесты раскрывают историю"""

TWISTS_PROMPT = """Ты — сценарист-триллерист. Придумай сюжетные твисты.

История: {title}
NPC: {npcs}
Квесты: {quests}

Придумай 3-4 твиста. Строго JSON:
{{
  "twists": [
    {{
      "id": "twist_id",
      "type": "betrayal/secret_identity/hidden_truth/unlikely_ally/sacrifice/reversal/revelation",
      "title": "Краткое название",
      "description": "Что происходит (2-3 предложения)",
      "trigger_quest": "quest_id который активирует твист",
      "revealed_npc": "npc_id",
      "impact": "Как влияет на историю (1 предложение)",
      "emotional_tone": "шок/горе/радость/злость/удивление"
    }}
  ]
}}

Правила:
- Минимум 1 предательство
- Минимум 1 скрытая личность
- Твисты раскрываются постепенно
- Последний твист — перед финалом"""

FULL_ARC_PROMPT = """Ты — Lead Game Designer. Создай полную структуру истории RPG.

Жанр: фэнтези, D&D 5e
Формат: 5 актов, 6-8 локаций, 6-8 NPC, 8-10 квестов, 3-4 твиста

Строго JSON:
{{
  "title": "Название",
  "premise": "Завязка",
  "setting": "Мир",
  "theme": "Тема",
  "acts": [
    {{"act": "prologue", "title": "...", "description": "...", "location_id": "...", "emotional_tone": "..."}}
  ],
  "locations": [
    {{"id": "...", "name": "...", "description": "...", "tile_color": "#...", "role": "...", "exits": {{}}}}
  ],
  "npcs": [
    {{"id": "...", "name": "...", "personality": {{"core": "...", "traits": ["..."]}}, "background": "...", "role": "...", "location_id": "...", "secret": "..."}}
  ],
  "quests": [
    {{"id": "...", "name": "...", "description": "...", "type": "...", "giver_npc": "...", "location": "...", "target": "...", "target_count": 1, "rewards": {{"xp": 100, "gold": 50}}, "story_importance": "main/side", "act": "..."}}
  ],
  "twists": [
    {{"id": "...", "type": "...", "title": "...", "description": "...", "trigger_quest": "...", "revealed_npc": "...", "impact": "..."}}
  ]
}}"""


class Storyteller:
    def __init__(self):
        self.current_arc: StoryArc | None = None

    def generate_full_story(self, theme: str = "", style: str = "dark_fantasy") -> StoryArc | None:
        """Генерирует полную историю за один LLM-запрос."""
        context = f"Тема: {theme}. Стиль: {style}." if theme else f"Стиль: {style}."
        try:
            result = llm_client.chat_json(
                FULL_ARC_PROMPT,
                [{"role": "user", "content": context}]
            )
            if not isinstance(result, dict) or "title" not in result:
                return None

            arc = StoryArc(
                title=result["title"],
                premise=result.get("premise", ""),
                setting=result.get("setting", ""),
                theme=result.get("theme", ""),
            )

            for act_d in result.get("acts", []):
                arc.acts.append(StoryBeat(
                    act=StoryAct(act_d.get("act", "act_1")),
                    title=act_d.get("title", ""),
                    description=act_d.get("description", ""),
                    location_id=act_d.get("location_id", ""),
                    emotional_tone=act_d.get("emotional_tone", ""),
                ))

            arc.locations = result.get("locations", [])
            arc.npcs = result.get("npcs", [])
            arc.quests = result.get("quests", [])
            arc.twists = result.get("twists", [])

            main_quests = [q["id"] for q in arc.quests if q.get("story_importance") == "main"]
            arc.main_quest_chain = sorted(main_quests, key=lambda qid: next(
                (i for i, q in enumerate(arc.quests) if q["id"] == qid), 0))

            self.current_arc = arc
            return arc

        except Exception as e:
            print(f"Storyteller LLM error: {e}")
            return None

    def generate_step_by_step(self, theme: str = "") -> StoryArc | None:
        """Генерирует историю пошагово (если LLM не может за один запрос)."""
        arc = StoryArc(title="", premise="", setting="", theme=theme)

        try:
            premise_data = llm_client.chat_json(
                PREMISE_PROMPT,
                [{"role": "user", "content": f"Тема: {theme}" if theme else "Придумай историю"}]
            )
            if premise_data:
                arc.title = premise_data.get("title", "Безымянная история")
                arc.premise = premise_data.get("premise", "")
                arc.setting = premise_data.get("setting", "")
                arc.theme = premise_data.get("theme", "")
        except Exception as e:
            print(f"Premise generation failed: {e}")
            return None

        try:
            loc_data = llm_client.chat_json(
                LOCATIONS_PROMPT.format(title=arc.title, premise=arc.premise, theme=arc.theme),
                [{"role": "user", "content": "Создай локации"}]
            )
            if loc_data:
                arc.locations = loc_data.get("locations", [])
        except Exception as e:
            print(f"Location generation failed: {e}")

        locations_str = json.dumps([l.get("id", "") for l in arc.locations], ensure_ascii=False)
        try:
            npc_data = llm_client.chat_json(
                NPCS_PROMPT.format(title=arc.title, locations=locations_str),
                [{"role": "user", "content": "Создай NPC"}]
            )
            if npc_data:
                arc.npcs = npc_data.get("npcs", [])
        except Exception as e:
            print(f"NPC generation failed: {e}")

        npcs_str = json.dumps([n.get("id", "") for n in arc.npcs], ensure_ascii=False)
        try:
            quest_data = llm_client.chat_json(
                QUESTS_PROMPT.format(title=arc.title, npcs=npcs_str, locations=locations_str),
                [{"role": "user", "content": "Создай квесты"}]
            )
            if quest_data:
                arc.quests = quest_data.get("quests", [])
                main_quests = [q["id"] for q in arc.quests if q.get("story_importance") == "main"]
                arc.main_quest_chain = main_quests
        except Exception as e:
            print(f"Quest generation failed: {e}")

        quests_str = json.dumps([q.get("id", "") for q in arc.quests], ensure_ascii=False)
        try:
            twist_data = llm_client.chat_json(
                TWISTS_PROMPT.format(title=arc.title, npcs=npcs_str, quests=quests_str),
                [{"role": "user", "content": "Создай твисты"}]
            )
            if twist_data:
                arc.twists = twist_data.get("twists", [])
        except Exception as e:
            print(f"Twist generation failed: {e}")

        self.current_arc = arc
        return arc

    def get_summary(self) -> str:
        """Краткое описание текущей истории."""
        if not self.current_arc:
            return "История не сгенерирована."
        arc = self.current_arc
        lines = [
            f"=== {arc.title} ===",
            f"Мир: {arc.setting}",
            f"Тема: {arc.theme}",
            f"Завязка: {arc.premise}",
            f"",
            f"Локации: {len(arc.locations)}",
            f"NPC: {len(arc.npcs)}",
            f"Квесты: {len(arc.quests)} (основных: {len([q for q in arc.quests if q.get('story_importance') == 'main'])})",
            f"Твисты: {len(arc.twists)}",
            "",
            "Акты:"
        ]
        for act in arc.acts:
            lines.append(f"  [{act.act.value}] {act.title} — {act.description[:80]}...")
        return "\n".join(lines)

    def apply_to_game(self, app_module) -> dict:
        """Применяет сгенерированную историю к.game state."""
        if not self.current_arc:
            return {"error": "Нет истории"}

        arc = self.current_arc
        results = {"locations": 0, "npcs": 0, "quests": 0}

        for loc_d in arc.locations:
            loc_id = loc_d.get("id", "")
            if loc_id and loc_id not in app_module.world.locations:
                from world.location import Location
                loc = Location(
                    id=loc_id,
                    name=loc_d.get("name", loc_id),
                    description=loc_d.get("description", ""),
                    tile_color=loc_d.get("tile_color", "#808080"),
                    exits=loc_d.get("exits", {}),
                )
                app_module.world.locations[loc_id] = loc
                results["locations"] += 1

        for npc_d in arc.npcs:
            from npc.npc import NPC
            npc = NPC(
                name=npc_d.get("name", "???"),
                personality=npc_d.get("personality", {}),
                background=npc_d.get("background", ""),
                lore=npc_d.get("secret", ""),
            )
            app_module.npcs[npc.id] = npc
            npc.save()
            results["npcs"] += 1

        return results

    def to_dict(self) -> dict:
        if not self.current_arc:
            return {}
        return self.current_arc.to_dict()

    def save(self, path: str = "db/story_arc.json"):
        if self.current_arc:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(self.current_arc.to_dict(), f, ensure_ascii=False, indent=2)

    def load(self, path: str = "db/story_arc.json"):
        try:
            with open(path, encoding="utf-8") as f:
                data = json.load(f)
            arc = StoryArc(
                title=data.get("title", ""),
                premise=data.get("premise", ""),
                setting=data.get("setting", ""),
                theme=data.get("theme", ""),
            )
            for act_d in data.get("acts", []):
                arc.acts.append(StoryBeat(
                    act=StoryAct(act_d.get("act", "act_1")),
                    title=act_d.get("title", ""),
                    description=act_d.get("description", ""),
                    location_id=act_d.get("location_id", ""),
                    emotional_tone=act_d.get("emotional_tone", ""),
                ))
            arc.locations = data.get("locations", [])
            arc.npcs = data.get("npcs", [])
            arc.quests = data.get("quests", [])
            arc.twists = data.get("twists", [])
            arc.main_quest_chain = data.get("main_quest_chain", [])
            self.current_arc = arc
            return True
        except Exception:
            return False

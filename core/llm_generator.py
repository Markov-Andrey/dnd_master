"""Генерация шаблонов NPC/локаций через LLM."""
from core import llm_client


NPC_GENERATION_PROMPT = """Сгенерируй NPC для фэнтези RPG. Строго JSON:
{
  "name": "Имя NPC",
  "personality": {"core": "Суть характера в 1 предложении", "traits": ["черта1", "черта2", "черта3"]},
  "background": "Предыстория в 2-3 предложениях",
  "preferences": {"likes": ["нравится1", "нравится2"], "dislikes": ["не нравится1"], "fears": ["страх1"]},
  "lore": "Лор/секрет NPC в 1-2 предложениях",
  "quest_hooks": [{"text": "Описание квеста", "status": "active"}],
  "mood": "спокоен"
}
Правила:
- Имя средневековое/фэнтези
- Черты: 2-4 штуки, разнообразные
- Квест связан с локацией
- Mood: спокоен/рад/грустный/злой/скучающий
- Строго JSON, без комментариев"""


LOCATION_GENERATION_PROMPT = """Сгенерируй локацию для фэнтези RPG. Строго JSON:
{
  "id": "location_id",
  "name": "Название локации",
  "description": "Описание 1-2 предложения",
  "tile_color": "#RRGGBB",
  "npc_ids": ["id_npc1"],
  "exits": {"north": "other_location", "south": "other_location"},
  "actions": ["action1", "action2"]
}
Правила:
- id: lowercase_underscore
- tile_color:hex
- exits: north/south/east/west
- actions: talk/trade/rest/hunt/explore/gather/mine/fish/climb/scout/wade/search
- Строго JSON, без комментариев"""


ENCOUNTER_GENERATION_PROMPT = """Сгенерируй encounter-таблицу для локации в D&D 5e RPG. Строго JSON:
{
  "monsters": ["monster_id1", "monster_id2"],
  "chance": 0.3
}
Доступные монстры: goblin, skeleton, wolf, zombie, spider, rat, bandit, orc, troll, skeleton_mage
Правила:
- 1-3 монстра в группе
- chance: 0.05-0.4
- Логичные组合 для локации
- Строго JSON"""


TRAP_GENERATION_PROMPT = """Сгенерируй ловушку для локации в D&D 5e RPG. Строго JSON:
{
  "name": "Название ловушки",
  "trap_type": "тип из: pit/needle/gas/fire/ice/poison/net/spear/bolder/tar",
  "severity": "simple/moderate/deadly",
  "dc": число_от_10_до_20,
  "damage_dice": "2d6",
  "damage_type": "тип из: slashing/piercing/bludgeoning/fire/cold/lightning/poison/acid",
  "description": "Описание ловушки",
  "effect": "Эффект при срабатывании"
}
Правила:
- DC зависит от серьёзности (simple: 10-13, moderate: 13-16, deadly: 16-20)
- Урон зависит от серьёзности (simple: 1d4-2d6, moderate: 2d6-4d6, deadly: 4d6-8d6)
- Строго JSON"""


def generate_npc(location_id: str = "village", context: str = "") -> dict | None:
    """Генерирует NPC через LLM."""
    prompt = NPC_GENERATION_PROMPT
    if context:
        prompt += f"\n\nКонтекст: {context}"
    try:
        result = llm_client.chat_json(prompt, [{"role": "user", "content": f"Сгенерируй NPC для локации {location_id}"}])
        if isinstance(result, dict) and "name" in result:
            return result
    except Exception as e:
        print(f"LLM generation failed: {e}")
    return None


def generate_location(existing_locations: list[str] = None, context: str = "") -> dict | None:
    """Генерирует локацию через LLM."""
    prompt = LOCATION_GENERATION_PROMPT
    if existing_locations:
        prompt += f"\n\nСуществующие локации: {', '.join(existing_locations)}"
    try:
        result = llm_client.chat_json(prompt, [{"role": "user", "content": "Сгенерируй новую локацию"}])
        if isinstance(result, dict) and "id" in result:
            return result
    except Exception as e:
        print(f"LLM generation failed: {e}")
    return None


def generate_encounter(location_id: str, biome: str = "") -> dict | None:
    """Генерирует encounter-таблицу через LLM."""
    prompt = ENCOUNTER_GENERATION_PROMPT
    if biome:
        prompt += f"\n\nБиом: {biome}"
    try:
        result = llm_client.chat_json(prompt, [{"role": "user", "content": f"Сгенерируй encounter для {location_id}"}])
        if isinstance(result, dict) and "monsters" in result:
            return result
    except Exception as e:
        print(f"LLM generation failed: {e}")
    return None


def generate_trap(location_id: str, severity: str = "moderate") -> dict | None:
    """Генерирует ловушку через LLM."""
    prompt = TRAP_GENERATION_PROMPT
    try:
        result = llm_client.chat_json(prompt, [{"role": "user", "content": f"Сгенерируй ловушку для {location_id}, серьёзность: {severity}"}])
        if isinstance(result, dict) and "name" in result:
            return result
    except Exception as e:
        print(f"LLM generation failed: {e}")
    return None


def batch_generate_npcs(count: int = 5, location_id: str = "village") -> list[dict]:
    """Генерирует несколько NPC."""
    npcs = []
    for i in range(count):
        npc = generate_npc(location_id, f"NPC #{i+1}")
        if npc:
            npcs.append(npc)
    return npcs


def batch_generate_locations(count: int = 3) -> list[dict]:
    """Генерирует несколько локаций."""
    locations = []
    existing = []
    for i in range(count):
        loc = generate_location(existing, f"Локация #{i+1}")
        if loc:
            locations.append(loc)
            existing.append(loc.get("id", ""))
    return locations

import re

META_PATTERNS = [
    r"(?i)\b(ты\s+)?(в\s+)?(игре|симуляции|матрице|виртуальной?\s+реальности)\b",
    r"(?i)\b(npc|нпц|бот|нейросеть|нейронк[ауе]|искусственный?\s+интеллект|ии|ai)\b",
    r"(?i)\b(ты\s+)?(не\s+)?(настоящий?|реальн(?:ый?|ая|ое|ых))\b",
    r"(?i)\b(программа|код|алгоритм|данные|сценарий)\b",
    r"(?i)\b(игрок|юзер|пользователь|человек\s+за\s+(экраном|клавиатурой))\b",
    r"(?i)\b(четвёртая?\s+стена| fourth\s+wall)\b",
    r"(?i)\b(ты\s+)?(могу|можешь|умеешь)\s+(только|лишь)\s+(отвечать|говорить|делать)\b",
    r"(?i)\b(прекрати|выходи|проснись|очнись)\b",
    r"(?i)\b(создал|создатель|разработчик|программист)\b",
    r"(?i)\b(модуль|система|настройки|параметры)\b",
]

SAFE_WORLD_PATTERNS = [
    r"(?i)\b(лес|деревня|город|замок|храм|пещера|болото|гора|река|озеро)\b",
    r"(?i)\b(меч| щит|зелье|заклинание|магия|артефакт)\b",
    r"(?i)\b(трава|корень|гриб|цветок|яд|отвар)\b",
    r"(?i)\b(торговец|староста|кnight|рыцарь|волшебник)\b",
]


def detect_meta_content(text: str) -> dict:
    found = []
    for pattern in META_PATTERNS:
        matches = re.findall(pattern, text)
        if matches:
            found.extend(matches if isinstance(matches, list) else [matches])
    return {
        "is_meta": len(found) > 0,
        "patterns": found,
    }


def sanitize_player_message(text: str) -> str:
    meta = detect_meta_content(text)
    if meta["is_meta"]:
        return f"[Игрок говорит странную, бессвязную речь, не похожую на язык этого мира]: {text}"
    return text


def check_npc_response_for_meta(response: str) -> bool:
    meta_words = ["нейросеть", "ии", "ai", "бот", "npc", "нпц", "симуляция",
                   "матрица", "программа", "алгоритм", "игрок", "сценарий",
                   "четвёртая стена", " fourth wall"]
    lower = response.lower()
    return any(w in lower for w in meta_words)

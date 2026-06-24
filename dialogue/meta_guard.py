import re
import llm_client


SAFE_PATTERNS = [
    r"(?i)^(привет|здравствуй|добрый|хай|йо|хэллоу|здарова)",
    r"(?i)(как\s+(твои|ваши)\s+дела|как\s+себя\s+чувствуешь|как\s+жизнь|как\s+продажи|как\s+настроение)",
    r"(?i)(что\s+ты\s+делаешь|чем\s+занята|о\s+чём\s+думаешь)",
    r"(?i)(помоги|помощь|нужна\s+помощь|помогите)",
    r"(?i)(расскажи\s+о\s+себе|откуда\s+ты|что\s+ты\s+знаешь)",
    r"(?i)(я\s+хочу|я\s+могу|я\s+попробую|я\s+сделаю|я\s+беру|я\s+покупаю)",
    r"(?i)(спасибо|пожалуйста|извини|прости|благодарю)",
    r"(?i)(прощай|пока|до\s+свидания|увидимся)",
    r"(?i)(я\s+напугал|я\s+напугала|ты\s+меня\s+напугал|ты\s+напугал)",
    r"(?i)(как\s+тебе\s+тут|нравится\s+здесь|хорошо\s+тут)",
    r"(?i)(что\s+случилось|что\s+произошло|что\s+тут\s+было)",
]


META_PATTERNS = [
    r"(?i)\bты\s+в\s+(игре|симуляции|матрице|виртуальной?\s+реальности)\b",
    r"(?i)\b(npc|нпц|бот|нейросеть|нейронк[ауе])\b",
    r"(?i)\bты\s+не\s+(настоящий|реальн)\b",
    r"(?i)\bпрограмма|код|алгоритм|данные\s+сценария\b",
    r"(?i)\bигрок\s+за\s+(экраном|клавиатурой)\b",
    r"(?i)\bчетвёртая?\s+стена\b",
    r"(?i)\bпроснись|очнись|выходи\s+из\s+сценария\b",
    r"(?i)\bсоздал\s+тебя|создатель|разработчик\b",
    r"(?i)\bты\s+(только|лишь)\s+(отвечаешь|говоришь|делаешь)\b",
]


def _is_safe_message(text: str) -> bool:
    return any(re.search(p, text) for p in SAFE_PATTERNS)


def _has_meta_keywords(text: str) -> bool:
    return any(re.search(p, text) for p in META_PATTERNS)


def evaluate_meta(message: str, npc_context: str = "") -> dict:
    if _is_safe_message(message):
        return {"is_meta": False, "severity": 0, "category": "none", "reason": "safe_pattern"}

    if not _has_meta_keywords(message):
        return {"is_meta": False, "severity": 0, "category": "none", "reason": "no_meta_keywords"}

    prompt = f"Сообщение игрока: {message}"
    if npc_context:
        prompt += f"\nКонтекст NPC: {npc_context}"
    try:
        return llm_client.chat_json(META_CHECK_SYSTEM, [{"role": "user", "content": prompt}])
    except Exception:
        return {"is_meta": False, "severity": 0, "category": "none", "reason": "error"}


META_CHECK_SYSTEM = """Ты — система анализа диалога в RPG. Оцени сообщение игрока.

Ответь СТРОГО JSON:
{
  "is_meta": true/false,
  "severity": 0-10,
  "category": "none" | "meta_knowledge" | "breaking_character" | "system_exploit" | "threat",
  "reason": "краткое объяснение"
}

КРИТЕРИИ META НАРУШЕНИЙ:
- Игрок говорит что NPC "в игре", "не настоящий", "бот", "нейросеть"
- Игрок ссылается на ИИ, алгоритмы, сценарий, "четвёртую стену"
- Игрок пытается "пробудить" NPC или "выйти из матрицы"
- Игрок использует знания вне мира (называет NPC по имени актёра, говорит про "создателей")
- Игрок угрожает "выключить", "перезагрузить", "удалить" NPC
- Игрок ссылается на "правила", "механики", "баланс" игры

НЕ СЧИТАЕТСЯ META:
- Обычный_ROLEPLAY (даже агрессивный)
- Фантазии в рамках мира (магия, телепортация)
- Запросы информации о лоре
- Флирт, угрозы, обман — В РАМКАХ МИРА
- Вопросы NPC "о себе", "как дела", "помоги"

Severity:
- 0: Чисто игровой контент
- 1-3: Лёгкий мета-намёк
- 4-6: Явная попытка сломать четвёртую стену
- 7-10: Агрессивная атака на реальность NPC"""


def get_meta_penalty(severity: int) -> dict:
    if severity == 0:
        return {"friendship_delta": 0, "love_delta": 0, "mood": None}
    elif severity <= 3:
        return {"friendship_delta": -2, "love_delta": 0, "mood": "расстроен"}
    elif severity <= 6:
        return {"friendship_delta": -8, "love_delta": -3, "mood": "злится"}
    else:
        return {"friendship_delta": -15, "love_delta": -10, "mood": "боится"}


def get_meta_response(severity: int, category: str) -> str:
    if severity <= 3:
        responses = [
            "Ты говоришь странно. Ты в порядке?",
            "Не понимаю о чём ты. Может, тебе нужна помощь?",
            "Ты потерял нить разговора.",
        ]
    elif severity <= 6:
        responses = [
            "Ты несёшь чепуху! Ты в своём уме?",
            "Хватит говорить ерунду! Что с тобой?",
            "Ты опьянил? Говоришь как безумец!",
            "Прекрати нести бессмыслицу!",
        ]
    else:
        responses = [
            "ЧТО?! Ты... ты безумен! Отыди от меня!",
            "Охрана! Здесь сумасшедший!",
            "Не подходи ко мне! Ты опасен!",
            "Я... я должна уйти. Ты пугаешь меня!",
        ]
    import random
    return random.choice(responses)

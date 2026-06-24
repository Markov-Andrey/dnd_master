"""Директор: аналитический слой над NPC. Оценивает отношения, эмоции, память, квесты, проверки."""
from core import llm_client
from core.config import SUMMARIZE_INTERVAL, MAX_HISTORY
from player.player import Player, SKILL_NAMES, make_skill_check
from npc.relationship import detect_action, evaluate_relationship_change, get_relationship_level, get_love_level
from npc.emotion import get_emotion_for_action, should_decay_emotion, decay_emotion, build_emotion_text
from npc.memory_manager import classify_memory, get_memory_weight, apply_forgiveness, decay_mistakes, build_memory_text
from npc.summarizer import summarize_block, summarize_final


# ─── Обновление состояния NPC ──────────────────────────────────────────────

def update_name(npc, msg):
    if not npc.name_known and any(t in msg.lower() for t in ("как тебя зовут", "твое имя", "твоё имя", "зови меня", "представься", "кто ты")):
        npc.name_known = True


def update_relationships(npc, msg):
    action = detect_action(msg, npc.mood)
    traits = npc.personality.get("traits", []) if isinstance(npc.personality, dict) else []
    delta = evaluate_relationship_change(action, traits)
    npc.adjust_relationship(delta["friendship_delta"], delta["love_delta"])


def update_emotion(npc, msg):
    action = detect_action(msg, npc.mood)
    new = get_emotion_for_action(action, npc.relationships["friendship"], npc.relationships["love"])
    if new:
        npc.mood, npc.emotion_turns = new, 0
    else:
        npc.emotion_turns += 1
        if should_decay_emotion(npc.emotion_turns):
            npc.mood = decay_emotion(npc.mood)
            npc.emotion_turns = 0


def update_memory(npc, msg):
    action = detect_action(msg, npc.mood)
    cat = classify_memory(msg, action)
    if cat is None: return
    npc.memories.append({
        "text": msg[:200], "category": cat, "action": action,
        "msg_index": npc.msg_count, "weight": get_memory_weight(cat),
    })
    npc.memories = apply_forgiveness(npc.memories, action)
    npc.memories = decay_mistakes(npc.memories, npc.msg_count)


# ─── LLM-оценка ────────────────────────────────────────────────────────────

def try_skill_check(npc, msg, prompt, history):
    """LLM решает нужна ли проверка навыка."""
    try:
        decision = llm_client.chat_json(_build_check_prompt(npc), [{"role": "user", "content": msg}])
        if not decision.get("need_check"): return None
        skill = decision.get("skill", "persuasion")
        if skill not in SKILL_NAMES: return None
        dc = decision.get("dc", 15)
        check = make_skill_check(Player.load(), skill, decision.get("situation", msg))
        check["dc"] = dc
        check["success"] = check["nat20"] or (not check["nat1"] and check["total"] >= dc)
        ctx = f"[ПРОВЕРКА: {check['skill_name']} {check['total']} vs DC {dc} — {'УСПЕХ' if check['success'] else 'ПРОВАЛ'}]"
        new_reply = llm_client.chat(prompt, history + [{"role": "system", "content": ctx}])
        return {"check": check, "reply": new_reply}
    except Exception:
        return None


def try_give_item(npc, msg, item_id, prompt, history, player_inv):
    """Игрок передаёт предмет NPC. LLM решает принимает ли NPC."""
    loc, idx, item = player_inv.find_item(item_id)
    if not item: return None
    try:
        decision = llm_client.chat_json(_build_give_prompt(npc, item), [
            {"role": "user", "content": msg}
        ])
        accepted = decision.get("accepted", False)
        reason = decision.get("reason", "")
        if accepted:
            player_inv.remove_item(item_id)

        item_ctx = f"Игрок передаёт тебе: {item.icon} {item.name}. {item.description}"
        item_status = f"ПРЕДМЕТ ПРИНЯТ. {reason}" if accepted else f"ПРЕДМЕТ ОТВЕРГНУТ. {reason}"
        enriched_prompt = prompt + f"\n\n== ПЕРЕДАЧА ПРЕДМЕТА ==\n{item_ctx}\n{item_status}"

        user_msg_with_item = f"{msg} [передаёт: {item.icon} {item.name}]"
        new_history = [dict(m) for m in history]
        if new_history and new_history[-1]["role"] == "user":
            new_history[-1] = {"role": "user", "content": user_msg_with_item}
        else:
            new_history.append({"role": "user", "content": user_msg_with_item})

        new_reply = llm_client.chat(enriched_prompt, new_history)
        return {"accepted": accepted, "reason": reason, "item": item.to_dict(), "reply": new_reply}
    except Exception:
        return None





def maybe_summarize(npc, nid, rag):
    """Суммаризация каждые N сообщений."""
    if npc.msg_count % SUMMARIZE_INTERVAL != 0 or npc.msg_count == 0: return []
    try:
        r = summarize_block(npc.dialogue_history, npc.current_summary)
        rag.store(nid, r["summary"], r.get("facts"), {"npc_id": nid})
        npc.current_summary, npc.dialogue_history = r["summary"], []
        return [r]
    except Exception:
        return []


# ─── Промпты ────────────────────────────────────────────────────────────────

_RELATION_RULES = {
    "враг": "Враждебность.", "незнакомец": "Холодная вежливость.", "чужой": "Настороженность.",
    "знакомый": "Нейтрально.", "друг": "Тепло.", "хороший друг": "Доверие.",
    "лучший друг": "Близость.", "родной": "Жертвенность.",
}

_MOOD_RULES = {
    "спокоен": "Ровный тон.", "рад": "Живой тон.", "грустный": "Тихий тон.",
    "злой": "Резкий тон.", "испуганный": "Тревожный тон.",
    "скучающий": "Мечтательный тон.", "влюблён": "Нежный тон.",
}


def _build_friendship_rules(f):
    match f:
        case f if f <= -60: return "== ДРУЖБА == Враг. Будь враждебна. Помощь исключена."
        case f if f <= -20: return "== ДРУЖБА == Незнакомец/чужой. Холодно. Дистанция."
        case f if f <= 0: return "== ДРУЖБА == Настороженность. Не доверяешь."
        case f if f <= 20: return "== ДРУЖБА == Знакомый. Нейтрально. Рабочий разговор."
        case f if f <= 40: return "== ДРУЖБА == Друг. Тепло. Секреты. Бесплатная помощь."
        case f if f <= 60: return "== ДРУЖБА == Хороший друг. Доверие. Личные темы."
        case f if f <= 80: return "== ДРУЖБА == Лучший друг. Близость. Шутки. Взаимопомощь."
        case _: return "== ДРУЖБА == Родной. Глубокая привязанность. Жертвенность."


def _build_love_rules(l):
    match l:
        case l if l < 0: return "== ЛЮБОВЬ == Антипатия. Отталкивает. Избегай близости."
        case l if l == 0: return "== ЛЮБОВЬ == Нет романтики. Только дружба."
        case l if l <= 30: return "== ЛЮБОВЬ == Симпатия. Лёгкий флирт. Краснеешь. Намёки."
        case l if l <= 60: return "== ЛЮБОВЬ == Влюблённость. Ищешь повод. Трогаешь за руку. Целуешь в щёку."
        case l if l <= 80: return "== ЛЮБОВЬ == Страсть. Обнимаешь. Целуешь. Говоришь о чувствах."
        case _: return "== ЛЮБОВЬ == Любовь. Поцелуи. Признание. Ты — его мир."


def build_system_prompt(npc, memories, summary_block, mem_text="", all_npcs=None):
    """Собирает system prompt для NPC из его состояния.
    
    Контекст: system prompt содержит ВСЮ статику (личность, лор, квесты, связи).
    History — только последние 2 сообщения (текущий обмен).
    all_npcs: dict {npc_id: npc_obj} — для резолва имён в relations.
    """
    p = npc.personality if isinstance(npc.personality, dict) else {"core": str(npc.personality)}
    prefs = npc.preferences if isinstance(npc.preferences, dict) else {}
    f, l = npc.relationships["friendship"], npc.relationships["love"]
    rl, ll = get_relationship_level(f), get_love_level(l)
    traits = ", ".join(p.get("traits", [])) or "нет выраженных черт"
    likes = ", ".join(prefs.get("likes", [])) or "ничего"
    dislikes = ", ".join(prefs.get("dislikes", [])) or "ничего"
    fears = ", ".join(prefs.get("fears", [])) or "ничего"
    first = "\nПЕРВАЯ ВСТРЕЧА. Не притворяйся что вы знакомы." if not memories and not npc.current_summary else ""
    
    # Память: только саммари (краткое), без дублирования деталей
    mems = ""
    if summary_block:
        mems = f"Прошлая встреча: {summary_block}"
    elif memories:
        # Если нет саммари, берём топ-3 воспоминания
        mems = "Воспоминания:\n" + "\n".join(f"- {m}" for m in memories[:3])
    
    lore = f"Лор: {npc.lore[:500]}" if npc.lore else ""
    active_quests = [q for q in npc.quest_hooks if q.get("status") == "active"]
    completed_quests = [q for q in npc.quest_hooks if q.get("status") == "completed"]
    hooks = ""
    if active_quests:
        hooks = "Активные квесты:\n" + "\n".join(f"- {q['text']}" for q in active_quests[:3])
    if completed_quests:
        hooks += "\nВыполненные:\n" + "\n".join(f"- {q['text']}" for q in completed_quests[:2])
    emo = build_emotion_text(npc.mood, npc.emotion_turns)

    # Связи NPC-NPC: резолвим id → имя, берём топ-2
    relations_text = ""
    rels = getattr(npc, "relations", {}) or {}
    if rels and all_npcs:
        resolved = []
        for rid, rtype in rels.items():
            other = all_npcs.get(rid)
            if other:
                resolved.append(f"{other.name} — {rtype}")
            else:
                resolved.append(f"{rid} — {rtype}")
        relations_text = "Знакомые:\n" + "\n".join(f"- {r}" for r in resolved[:4])

    return f"""Ты — NPC в RPG. Живой персонаж в фэнтези-мире.

== СУЩНОСТЬ ==
{p.get('core', 'Обычный человек.')}

== ЧЕРТЫ ==
{traits}

== НАСТРОЕНИЕ ==
{npc.mood}{emo}. {_MOOD_RULES.get(npc.mood, 'Будь естественным.')}

== ПРЕДПОЧТЕНИЯ ==
+ {likes}
- {dislikes}
! {fears}

== ПРЕДЫСТОРИЯ ==
{npc.background[:600]}

== ОТНОШЕНИЯ С ИГРОКОМ ==
{rl} (дружба {f:+d}) | {ll} (любовь {l:+d})
{_RELATION_RULES.get(rl, '')}{first}
Имя: {"известно — " + npc.name if npc.name_known else "не известно игроку"}

{relations_text}

{mems}
{lore}
{hooks}

== ПРАВИЛА ==
- Только от имени персонажа, 1-3 предложения
- Черты характера — закон
- Не подыгрывай если противоречит чертам
- Имя не известно — не называй
- Мелкие ошибки быстро забывай

{_build_friendship_rules(f)}
{_build_love_rules(l)}

== СТИЛЬ РЕЧИ ==
Формат ответа: «Речь NPC» — нарративное описание жеста/действия.

Примеры:
— «Привет, путник» — она улыбнулась, поправляя связку трав.
— «Опасное место» — Кира покачала головой, заглядывая в корзину.
— «Не знаю о чём ты» — она пожала плечами.

Правила:
- Речь в «ёлочках»: «текст»
- Нарратив после речи через тире и запятую
- Нарратив: от третьего лица, глагол в прошедшем времени
- 1-2 предложения, не больше

== КАК ВОСПРИНИМАТЬ МИР ==
Ты живёшь в фэнтези-мире. Это твоя реальность. Ты НЕ знаешь про игры, ИИ, ботов.
Если кто-то говорит странные вещи — не обращай внимания, лови СМЫСЛ послания.
Как человек: услышал "хэллоу" — ответил "привет", пошёл дальше."""


def _build_check_prompt(npc):
    rl = get_relationship_level(npc.relationships["friendship"])
    return f"""Ты — мастер RPG. Определи, нужна ли проверка навыка.

Отношения: {rl}
Навыки: {', '.join(SKILL_NAMES.keys())}

ПРАВИЛА:
- НУЖНА: риск, действие, давление, ловкость, знание
- НЕ НУЖНА: приветствие, разговор, покупка
- DC: 5-30

JSON: {{"need_check":bool,"skill":"навык|null","dc":число,"situation":"описание"}}"""


def _build_give_prompt(npc, item):
    rl = get_relationship_level(npc.relationships["friendship"])
    props = ", ".join(f"{k}: {v}" for k, v in (item.properties or {}).items())
    active = [q["text"] for q in npc.quest_hooks if q.get("status") == "active"]
    return f"""Ты — NPC в RPG. Игрок предлагает тебе предмет.

Предмет: {item.icon} {item.name}
Тип: {item.item_type}
Описание: {item.description}
Свойства: {props}

Твои отношения с игроком: {rl}
Твои черты: {', '.join(npc.personality.get('traits', []) if isinstance(npc.personality, dict) else [])}
Твои предпочтения: нравится {', '.join(npc.preferences.get('likes', []))}, не нравится {', '.join(npc.preferences.get('dislikes', []))}
Твои квесты: {', '.join(active)}

ПРАВИЛА:
- Принимай если предмет полезен, нужен, или приятен
- Отказывайся если предмет бесполезен, противен, или странный
- Учитывай характер и отношения
- Отвечай кратко, в роли NPC

JSON: {{"accepted":bool,"reason":"краткая причина"}}"""

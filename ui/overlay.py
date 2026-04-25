"""Полупрозрачные оверлеи: инвентарь, статус, журнал, меню, диалог."""
import pygame

OVERLAY_BG = (10, 8, 6, 230)

# ── таблицы перевода ──────────────────────────────────────────────────────────
ATTR_RU = {
    "strength":     "Сила",
    "intelligence": "Интеллект",
    "willpower":    "Воля",
    "agility":      "Ловкость",
    "speed":        "Скорость",
    "endurance":    "Выносливость",
    "personality":  "Харизма",
    "luck":         "Удача",
}
SKILL_RU = {
    "blade":       "Клинок",
    "blunt":       "Дробящее",
    "archery":     "Стрельба",
    "block":       "Блок",
    "sneak":       "Скрытность",
    "lockpick":    "Взлом",
    "alchemy":     "Алхимия",
    "speechcraft": "Красноречие",
    "mercantile":  "Торговля",
}
CLASS_RU  = {"warrior": "Воин",   "scholar": "Учёный", "rogue": "Вор"}
RACE_RU   = {"human":   "Человек","elf":     "Эльф",   "orc":   "Орк"}


def _panel(surface, x, y, w, h):
    p = pygame.Surface((w, h), pygame.SRCALPHA)
    p.fill(OVERLAY_BG)
    surface.blit(p, (x, y))
    pygame.draw.rect(surface, (80, 70, 50), (x, y, w, h), 2)


def _bar(surface, x, y, w, h, val, max_val, color):
    pygame.draw.rect(surface, (40, 40, 40), (x, y, w, h))
    fw = int(w * max(0, val) / max(1, max_val))
    if fw:
        pygame.draw.rect(surface, color, (x, y, fw, h))


# ── ГЛАВНОЕ МЕНЮ ──────────────────────────────────────────────────────────────

TITLE_LINES = [
    "  ____  _   _  ____  _  __",
    " |  _ \\| | | |/ ___|| |/ /",
    " | | | | | | |\\___ \\| ' / ",
    " | |_| | |_| | ___) | . \\ ",
    " |____/ \\___/ |____/|_|\\_\\",
]


def render_main_menu(surface, state, font_sm, font_md, font_lg):
    sw, sh = surface.get_size()
    surface.fill((8, 6, 4))

    ty = sh // 5
    for i, line in enumerate(TITLE_LINES):
        t = font_md.render(line, True, (180, 150, 80))
        surface.blit(t, ((sw - t.get_width()) // 2, ty + i * (font_md.get_height() + 2)))

    ty += len(TITLE_LINES) * (font_md.get_height() + 2) + 40

    options = ["Новая игра", "Загрузить", "Выход"]
    sel     = getattr(state, "_menu_sel", 0)
    for i, opt in enumerate(options):
        col  = (255, 220, 80) if i == sel else (160, 140, 100)
        t    = font_md.render(("► " if i == sel else "  ") + opt, True, col)
        surface.blit(t, ((sw - t.get_width()) // 2, ty + i * 40))

    saves = state.list_saves()
    if saves:
        hint = font_sm.render(f"Найдено сохранений: {len(saves)}", True, (100, 120, 100))
        surface.blit(hint, ((sw - hint.get_width()) // 2, sh - 40))


# ── СОЗДАНИЕ ПЕРСОНАЖА ────────────────────────────────────────────────────────

def render_char_creation(surface, state, font_sm, font_md, races, classes):
    sw, sh = surface.get_size()
    surface.fill((8, 6, 4))

    step  = getattr(state, "_cc_step", "race")
    sel   = getattr(state, "_cc_sel",  0)
    steps = ["Раса", "Класс", "Имя"]
    step_idx = {"race": 0, "class": 1, "name": 2}.get(step, 0)

    t = font_md.render("СОЗДАНИЕ ПЕРСОНАЖА", True, (200, 170, 80))
    surface.blit(t, ((sw - t.get_width()) // 2, 20))

    for i, s in enumerate(steps):
        col = (220, 200, 80) if i == step_idx else (80, 80, 60)
        t   = font_sm.render(f"{'►' if i == step_idx else ' '} {i+1}. {s}", True, col)
        surface.blit(t, (40 + i * 200, 60))

    y = 110
    if step == "race":
        keys = list(races.keys())
        t = font_md.render("Выберите расу:", True, (180, 160, 100))
        surface.blit(t, (60, y)); y += 40
        for i, key in enumerate(keys):
            r    = races[key]
            attr = curses_reverse(i == sel, font_md)
            col  = (255, 220, 80) if i == sel else (160, 140, 100)
            t    = font_md.render(("► " if i == sel else "  ") + r["name"], True, col)
            surface.blit(t, (80, y))
            d = font_sm.render(r["description"], True, (120, 110, 80))
            surface.blit(d, (100, y + font_md.get_height() + 2))
            y += font_md.get_height() + font_sm.get_height() + 14

        ht = font_sm.render("↑/↓ выбор   Enter подтвердить", True, (90, 90, 70))
        surface.blit(ht, (60, sh - 40))

    elif step == "class":
        keys = list(classes.keys())
        t = font_md.render("Выберите класс:", True, (180, 160, 100))
        surface.blit(t, (60, y)); y += 40
        for i, key in enumerate(keys):
            c    = classes[key]
            col  = (255, 220, 80) if i == sel else (160, 140, 100)
            t    = font_md.render(("► " if i == sel else "  ") + c["name"], True, col)
            surface.blit(t, (80, y))
            d = font_sm.render(c["description"], True, (120, 110, 80))
            surface.blit(d, (100, y + font_md.get_height() + 2))
            sk_labels = [SKILL_RU.get(s, s) for s in c["primary_skills"]]
            sk = font_sm.render("Навыки: " + ", ".join(sk_labels), True, (100, 130, 100))
            surface.blit(sk, (100, y + font_md.get_height() + font_sm.get_height() + 4))
            y += font_md.get_height() + font_sm.get_height() * 2 + 20

        ht = font_sm.render("↑/↓ выбор   Enter подтвердить   Backspace назад", True, (90, 90, 70))
        surface.blit(ht, (60, sh - 40))

    elif step == "name":
        buf = getattr(state, "_cc_name", "") or ""
        t = font_md.render("Введите имя:", True, (180, 160, 100))
        surface.blit(t, (60, y)); y += 50
        name_txt = font_md.render(f"> {buf}_", True, (220, 200, 80))
        surface.blit(name_txt, (80, y))
        ht = font_sm.render("Введите имя   Enter подтвердить   Backspace удалить", True, (90, 90, 70))
        surface.blit(ht, (60, sh - 40))


def curses_reverse(active, font):
    return None  # helper stub — not needed in pygame


# ── ИНВЕНТАРЬ ─────────────────────────────────────────────────────────────────

SLOT_RU = {
    "weapon": "Оружие",
    "armor":  "Броня",
    "head":   "Голова",
    "hands":  "Руки",
    "feet":   "Ноги",
    "ring":   "Кольцо",
}


def render_inventory(surface, player, font_sm, font_md):
    sw, sh = surface.get_size()
    pw, ph = 700, 460
    px, py = (sw - pw) // 2, (sh - ph) // 2
    _panel(surface, px, py, pw, ph)

    t = font_md.render("ИНВЕНТАРЬ", True, (200, 170, 80))
    surface.blit(t, (px + (pw - t.get_width()) // 2, py + 10))

    inv = player.inventory
    sel = getattr(player, "_inv_sel", 0)

    total_w = sum((i.get("weight", 1) if isinstance(i, dict) else i.weight) for i in inv)
    wt = font_sm.render(f"Вес: {total_w:.1f} / {player.carry_weight}   Золото: {player.gold}",
                        True, (160, 150, 100))
    surface.blit(wt, (px + 10, py + 40))

    iy = py + 65
    for i, item in enumerate(inv[:14]):
        name = item.get("name", "?") if isinstance(item, dict) else item.name
        val  = item.get("value", 0)  if isinstance(item, dict) else item.value
        wgt  = item.get("weight", 1) if isinstance(item, dict) else item.weight
        eq   = item in player.equipped.values()
        col  = (255, 220, 80) if i == sel else (160, 150, 110)
        row  = font_sm.render(f"{'[Э] ' if eq else '    '}{name:<28} {wgt:.1f}кг  {val}з",
                               True, col)
        surface.blit(row, (px + 10, iy + i * 22))

    ex = px + pw // 2 + 10
    t  = font_md.render("Экипировка", True, (160, 140, 80))
    surface.blit(t, (ex, py + 40))
    for si, slot in enumerate(SLOT_RU):
        item = player.equipped.get(slot)
        nm   = (item.get("name") if isinstance(item, dict) else item.name) if item else "—"
        st   = font_sm.render(f"{SLOT_RU[slot]:<12}: {nm}", True, (140, 160, 120))
        surface.blit(st, (ex, py + 70 + si * 22))

    if inv and 0 <= sel < len(inv):
        item  = inv[sel]
        desc  = item.get("description", "") if isinstance(item, dict) else item.description
        dt    = font_sm.render(desc[:80], True, (130, 120, 90))
        surface.blit(dt, (px + 10, py + ph - 50))

    hint = font_sm.render("↑/↓ выбор   E надеть/снять   D выбросить   Esc закрыть",
                           True, (80, 80, 60))
    surface.blit(hint, (px + 10, py + ph - 25))


# ── СТАТУС ПЕРСОНАЖА ──────────────────────────────────────────────────────────

def render_status(surface, player, font_sm, font_md):
    sw, sh = surface.get_size()
    pw, ph = 720, 500
    px, py = (sw - pw) // 2, (sh - ph) // 2
    _panel(surface, px, py, pw, ph)

    race_name  = RACE_RU.get(player.race,       player.race)
    class_name = CLASS_RU.get(player.char_class, player.char_class)

    t = font_md.render(f"ПЕРСОНАЖ — {player.name.upper()}", True, (200, 170, 80))
    surface.blit(t, (px + (pw - t.get_width()) // 2, py + 10))

    info = font_sm.render(
        f"Раса: {race_name}   Класс: {class_name}   Уровень: {player.level}",
        True, (160, 150, 110))
    surface.blit(info, (px + 10, py + 44))
    xp_t = font_sm.render(
        f"До следующего уровня: {player._points_to_level() - player.skill_points_since_level} оч.",
        True, (120, 120, 100))
    surface.blit(xp_t, (px + 10, py + 60))

    t = font_md.render("Атрибуты", True, (160, 140, 80))
    surface.blit(t, (px + 10, py + 82))
    attrs = list(player.attributes.items())
    for i, (name, val) in enumerate(attrs):
        col  = px + 10 + (i % 2) * (pw // 2)
        row  = py + 104 + (i // 2) * 22
        bar_w = 80
        _bar(surface, col + 140, row + 2, bar_w, 12, val, 100, (100, 140, 180))
        label = ATTR_RU.get(name, name)
        t = font_sm.render(f"{label:<14} {val:3d}", True, (160, 150, 120))
        surface.blit(t, (col, row))

    sy = py + 104 + (len(attrs) // 2 + 1) * 22 + 10
    t  = font_md.render("Навыки", True, (160, 140, 80))
    surface.blit(t, (px + 10, sy)); sy += 28
    skills = list(player.skills.items())
    for i, (name, val) in enumerate(skills):
        col = px + 10 + (i % 3) * (pw // 3)
        row = sy + (i // 3) * 22
        _bar(surface, col + 120, row + 2, 60, 12, val, 100, (80, 160, 100))
        label = SKILL_RU.get(name, name)
        t = font_sm.render(f"{label:<12} {val:3d}", True, (140, 160, 120))
        surface.blit(t, (col, row))

    dy = sy + (len(skills) // 3 + 1) * 22 + 6
    t  = font_md.render("Производные", True, (160, 140, 80))
    surface.blit(t, (px + 10, dy))
    info2 = font_sm.render(
        f"ОЗ: {player.hp}/{player.hp_max}   "
        f"Выносл.: {player.stamina}/{player.stamina_max}   "
        f"Грузоподъёмность: {player.carry_weight} кг",
        True, (140, 160, 120))
    surface.blit(info2, (px + 10, dy + 20))
    info3 = font_sm.render(f"Золото: {player.gold}   Репутация: {player.reputation}/100",
                            True, (200, 170, 80))
    surface.blit(info3, (px + 10, dy + 38))

    hint = font_sm.render("Esc закрыть", True, (80, 80, 60))
    surface.blit(hint, (px + 10, py + ph - 25))


# ── ЖУРНАЛ ────────────────────────────────────────────────────────────────────

def render_journal(surface, player, font_sm, font_md):
    sw, sh = surface.get_size()
    pw, ph = 680, 460
    px, py = (sw - pw) // 2, (sh - ph) // 2
    _panel(surface, px, py, pw, ph)

    t = font_md.render("ЖУРНАЛ", True, (200, 170, 80))
    surface.blit(t, (px + (pw - t.get_width()) // 2, py + 10))

    tabs = ["Активные задания", "Завершённые", "Записи"]
    tab  = getattr(player, "_journal_tab", 0)
    tx   = px + 10
    for i, tb in enumerate(tabs):
        col = (220, 190, 80) if i == tab else (100, 90, 60)
        t   = font_sm.render(tb, True, col)
        surface.blit(t, (tx, py + 40))
        tx += t.get_width() + 30

    iy = py + 70
    if tab == 0:
        items = player.active_quests or []
        if not items:
            surface.blit(font_sm.render("Нет активных заданий.", True, (90, 90, 70)), (px+20, iy))
        for q in items[:10]:
            t = font_sm.render("► " + q.get("title", q.get("id", "Задание")), True, (180, 200, 140))
            surface.blit(t, (px + 20, iy)); iy += 22
            d = font_sm.render("  " + q.get("description", ""), True, (120, 110, 80))
            surface.blit(d, (px + 20, iy)); iy += 22
    elif tab == 1:
        if not player.completed_quests:
            surface.blit(font_sm.render("Нет завершённых заданий.", True, (90, 90, 70)), (px+20, iy))
        for qid in player.completed_quests[:14]:
            t = font_sm.render("✓ " + str(qid), True, (100, 160, 100))
            surface.blit(t, (px + 20, iy)); iy += 22
    elif tab == 2:
        for entry in player.journal_entries[-(ph // 22 - 4):]:
            t = font_sm.render(entry[:80], True, (150, 140, 110))
            surface.blit(t, (px + 20, iy)); iy += 20

    hint = font_sm.render("1/2/3 вкладки   Esc закрыть", True, (80, 80, 60))
    surface.blit(hint, (px + 10, py + ph - 25))


# ── ДИАЛОГ ───────────────────────────────────────────────────────────────────

def render_dialogue(surface, npc, sel, dialogue_text, font_sm, font_md):
    sw, sh = surface.get_size()
    pw, ph = 640, 360
    px, py = (sw - pw) // 2, sh - ph - 20
    _panel(surface, px, py, pw, ph)

    t = font_md.render(npc.name.upper(), True, (220, 190, 80))
    surface.blit(t, (px + 10, py + 10))
    sub = font_sm.render(f"({npc.npc_type})", True, (120, 110, 80))
    surface.blit(sub, (px + 10, py + 10 + font_md.get_height()))

    text  = dialogue_text or npc.greet()
    words = text.split()
    lines, cur = [], ""
    max_w = pw - 30
    for word in words:
        test = (cur + " " + word).strip()
        if font_sm.size(test)[0] > max_w:
            lines.append(cur); cur = word
        else:
            cur = test
    if cur:
        lines.append(cur)

    ty = py + 60
    for line in lines[:6]:
        t = font_sm.render(line, True, (200, 190, 160))
        surface.blit(t, (px + 10, ty)); ty += font_sm.get_height() + 2

    options = npc.get_dialogue_options()
    oy = py + ph - len(options) * 26 - 30
    for i, opt in enumerate(options):
        col = (255, 220, 80) if i == sel else (140, 130, 90)
        t   = font_sm.render(("► " if i == sel else "  ") + opt, True, col)
        surface.blit(t, (px + 10, oy + i * 26))

    hint = font_sm.render("↑/↓ выбор   Enter выбрать   Esc покинуть", True, (70, 70, 50))
    surface.blit(hint, (px + 10, py + ph - 22))

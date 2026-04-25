"""Нижний HUD поверх 3D-вида."""
import pygame

HUD_H = 120


def _bar(surface, x, y, w, h, value, max_val, fill_color, bg_color=(40, 40, 40)):
    pygame.draw.rect(surface, bg_color,   (x, y, w, h))
    filled = int(w * max(0, value) / max(1, max_val))
    if filled > 0:
        pygame.draw.rect(surface, fill_color, (x, y, filled, h))
    pygame.draw.rect(surface, (80, 80, 80), (x, y, w, h), 1)


def render_hud(surface: pygame.Surface, player, game_time,
               messages: list[str], font_sm, font_md):
    sw, sh = surface.get_size()
    hud_y  = sh - HUD_H

    panel = pygame.Surface((sw, HUD_H), pygame.SRCALPHA)
    panel.fill((0, 0, 0, 200))
    surface.blit(panel, (0, hud_y))

    pad = 10

    # ОЗ
    _bar(surface, pad, hud_y + 10, 160, 16,
         player.hp, player.hp_max, (180, 40, 40))
    t = font_sm.render(f"ОЗ  {player.hp}/{player.hp_max}", True, (220, 180, 180))
    surface.blit(t, (pad, hud_y + 28))

    # Выносливость
    _bar(surface, pad, hud_y + 48, 160, 16,
         player.stamina, player.stamina_max, (40, 160, 80))
    t = font_sm.render(f"Вын {player.stamina}/{player.stamina_max}", True, (160, 220, 160))
    surface.blit(t, (pad, hud_y + 66))

    # Уровень и золото
    t = font_sm.render(f"Ур.{player.level}  Золото: {player.gold}", True, (220, 200, 100))
    surface.blit(t, (pad, hud_y + 88))

    # Время и дата
    time_txt = font_sm.render(f"{game_time.time_str}  {game_time.date_str}",
                               True, (160, 190, 220))
    surface.blit(time_txt, (sw - time_txt.get_width() - pad, hud_y + 10))

    # Лог сообщений
    log_x = 190
    for i, msg in enumerate(messages[-3:]):
        alpha = 180 + i * 25
        t = font_sm.render(msg, True, (alpha, alpha, alpha))
        surface.blit(t, (log_x, hud_y + 10 + i * 22))

    # Статус-эффекты
    if player.statuses:
        st = font_sm.render("  ".join(player.statuses), True, (220, 80, 80))
        surface.blit(st, (pad, hud_y + HUD_H - 20))

    # Подсказки клавиш
    hints = "[W/A/S/D] движение  [ЛКМ/Пробел] атака  [E] говорить  [I] инвентарь  [C] персонаж  [J] журнал"
    ht = font_sm.render(hints, True, (100, 100, 100))
    surface.blit(ht, (sw - ht.get_width() - pad, hud_y + HUD_H - 20))

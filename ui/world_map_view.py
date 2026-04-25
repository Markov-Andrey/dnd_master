"""Карта мира — вид сверху (pygame)."""
import pygame

TERRAIN_COLORS = {
    "plains":    (100, 140,  70),
    "forest":    ( 40,  90,  40),
    "mountains": (120, 110, 100),
    "coast":     ( 60, 100, 160),
    "desert":    (190, 165,  90),
    "swamp":     ( 60,  90,  60),
    "tundra":    (190, 200, 210),
}
TERRAIN_RU = {
    "plains":    "Равнина",
    "forest":    "Лес",
    "mountains": "Горы",
    "coast":     "Побережье",
    "desert":    "Пустыня",
    "swamp":     "Болото",
    "tundra":    "Тундра",
}
LOC_COLORS = {
    "city":    (220, 180,  60),
    "village": (160, 200, 100),
    "dungeon": (180,  60,  60),
}
LOC_RU = {
    "city":    "город",
    "village": "деревня",
    "dungeon": "подземелье",
}
FOG_COLOR  = (10, 10, 15)
PLAYER_COL = (255, 255, 80)


def render_world_map(surface: pygame.Surface, world, player, font_sm, font_md):
    sw, sh   = surface.get_size()
    size     = world.SIZE
    usable_w = sw - 260
    usable_h = sh - 20
    tile     = max(4, min(usable_w // size, usable_h // size))
    off_x, off_y = 10, 10

    explored = {k for k in player.visited_locations if "," in k}
    surface.fill((15, 12, 10))

    for gy in range(size):
        for gx in range(size):
            rx, ry  = off_x + gx * tile, off_y + gy * tile
            key     = f"{gx},{gy}"
            if key not in explored:
                pygame.draw.rect(surface, FOG_COLOR, (rx, ry, tile - 1, tile - 1))
                continue
            region = world.regions[gy][gx]
            pygame.draw.rect(surface, TERRAIN_COLORS.get(region.terrain, (80,80,80)),
                             (rx, ry, tile - 1, tile - 1))
            locs = world.get_locations_at(gx, gy)
            if locs:
                lcol = LOC_COLORS.get(locs[0].loc_type, (200, 200, 200))
                dot  = max(3, tile // 3)
                cx   = rx + tile // 2 - dot // 2
                cy   = ry + tile // 2 - dot // 2
                pygame.draw.rect(surface, lcol, (cx, cy, dot, dot))

    # игрок
    px = off_x + player.world_x * tile + tile // 2
    py = off_y + player.world_y * tile + tile // 2
    pygame.draw.circle(surface, PLAYER_COL, (px, py), max(3, tile // 3))

    # боковая панель
    panel_x = off_x + size * tile + 20
    region  = world.get_region(player.world_x, player.world_y)

    lines = [
        ("КАРТА МИРА", (220, 200, 100)),
        ("", None),
        (f"Позиция: {player.world_x}, {player.world_y}", (180, 180, 180)),
    ]
    if region:
        terrain_name = TERRAIN_RU.get(region.terrain, region.terrain)
        lines.append((f"Местность: {terrain_name}", (160, 210, 160)))
        locs = world.get_locations_at(player.world_x, player.world_y)
        if locs:
            for loc in locs:
                type_name = LOC_RU.get(loc.loc_type, loc.loc_type)
                lines.append((f"► {loc.name} [{type_name}]",
                              LOC_COLORS.get(loc.loc_type, (200,200,200))))
        else:
            lines.append(("Нет локаций", (100, 100, 100)))

    lines += [
        ("", None),
        ("[E] Войти в локацию",    (120, 200, 120)),
        ("[W/A/S/D] Перемещение",  (120, 120, 200)),
        ("[F5] Быстрое сохранение",(160, 160, 160)),
        ("[Q] Сохранить и выйти",  (160, 100, 100)),
    ]

    cy = off_y
    for text, color in lines:
        if not text:
            cy += 10; continue
        t = font_sm.render(text, True, color or (200, 200, 200))
        surface.blit(t, (panel_x, cy))
        cy += t.get_height() + 4

    # легенда
    cy += 20
    t = font_sm.render("Легенда:", True, (180, 180, 180))
    surface.blit(t, (panel_x, cy)); cy += 20
    for terrain, col in list(TERRAIN_COLORS.items())[:5]:
        pygame.draw.rect(surface, col, (panel_x, cy, 14, 14))
        t = font_sm.render(TERRAIN_RU.get(terrain, terrain), True, (160, 160, 160))
        surface.blit(t, (panel_x + 18, cy)); cy += 18

"""
DDA raycasting renderer (Wolfenstein/Daggerfall style).

pitch  — vertical horizon shift in pixels (positive = look down, negative = up).
         Pass pitch to both cast_rays and render_sprites so walls and sprites
         shift consistently.
"""
import math
import pygame
from engine.dungeon_map import DungeonMap, EMPTY, DOOR

FOV       = math.radians(70)
HALF_FOV  = FOV / 2
MAX_DEPTH = 24

WALL_PALETTE = {
    1: ((110, 90,  70), (75,  60,  48)),
    4: ((130, 80,  60), (90,  55,  40)),
    5: ((100, 75,  50), (70,  52,  35)),
}
DEFAULT_WALL  = ((110, 90, 70), (75, 60, 48))
DOOR_COLOR    = ((160, 120, 60), (120, 90, 45))
CEIL_COLOR    = (20,  20,  25)
FLOOR_COLOR   = (45,  35,  25)
CEIL_OUTDOOR  = (80, 120, 180)
FLOOR_OUTDOOR = (55,  80,  40)


def _shade(color: tuple, dist: float, max_dist: float = MAX_DEPTH) -> tuple:
    t = max(0.05, 1.0 - dist / max_dist)
    return (int(color[0] * t), int(color[1] * t), int(color[2] * t))


# ─────────────────────────────────────────────────────────────────────────────
# Wall raycasting
# ─────────────────────────────────────────────────────────────────────────────

def cast_rays(surface: pygame.Surface, dungeon_map: DungeonMap,
              px: float, py: float, angle: float,
              pitch: int = 0) -> list[float]:
    """
    Render the 3D world into `surface` and return the z_buffer.
    pitch: pixel offset of the horizon (mouse Y look).
    """
    sw, sh   = surface.get_size()
    horizon  = sh // 2 + pitch          # shifted horizon line
    ray_step = FOV / sw
    ray_ang  = angle - HALF_FOV
    z_buffer = [MAX_DEPTH] * sw

    ceil_col  = CEIL_OUTDOOR  if dungeon_map.is_outdoor else CEIL_COLOR
    floor_col = FLOOR_OUTDOOR if dungeon_map.is_outdoor else FLOOR_COLOR

    # floor / ceiling split at the pitched horizon
    split = max(0, min(sh, horizon))
    surface.fill(ceil_col,  (0, 0,     sw, split))
    surface.fill(floor_col, (0, split, sw, sh - split))

    for col in range(sw):
        sin_a = math.sin(ray_ang)
        cos_a = math.cos(ray_ang)
        if abs(cos_a) < 1e-10: cos_a = 1e-10
        if abs(sin_a) < 1e-10: sin_a = 1e-10

        map_x, map_y = int(px), int(py)

        delta_x = abs(1.0 / cos_a)
        delta_y = abs(1.0 / sin_a)

        if cos_a < 0:
            step_x      = -1
            side_dist_x = (px - map_x) * delta_x
        else:
            step_x      = 1
            side_dist_x = (map_x + 1.0 - px) * delta_x

        if sin_a < 0:
            step_y      = -1
            side_dist_y = (py - map_y) * delta_y
        else:
            step_y      = 1
            side_dist_y = (map_y + 1.0 - py) * delta_y

        side    = 0
        is_door = False
        for _ in range(MAX_DEPTH * 2):
            if side_dist_x < side_dist_y:
                side_dist_x += delta_x
                map_x       += step_x
                side         = 0
            else:
                side_dist_y += delta_y
                map_y       += step_y
                side         = 1
            cell = dungeon_map.get_cell(map_x, map_y)
            if cell == 1 or cell >= 4:
                break
            if cell == 2:
                is_door = True
                break

        perp = max(0.05,
                   (map_x - px + (1 - step_x) / 2) / cos_a if side == 0
                   else (map_y - py + (1 - step_y) / 2) / sin_a)
        z_buffer[col] = perp

        wall_h      = int(sh / perp)
        wall_top    = max(0,  horizon - wall_h // 2)
        wall_bottom = min(sh, horizon + wall_h // 2)

        palette    = DOOR_COLOR if is_door else \
                     WALL_PALETTE.get(dungeon_map.get_cell(map_x, map_y), DEFAULT_WALL)
        base_color = palette[side] if isinstance(palette[0], tuple) else palette[side]
        pygame.draw.line(surface, _shade(base_color, perp),
                         (col, wall_top), (col, wall_bottom))

        ray_ang += ray_step

    return z_buffer


# ─────────────────────────────────────────────────────────────────────────────
# Sprite rendering
# ─────────────────────────────────────────────────────────────────────────────

def render_sprites(surface: pygame.Surface, sprites: list,
                   px: float, py: float, angle: float,
                   z_buffer: list[float], pitch: int = 0):
    """
    Billboard sprites, z-buffer clipped, with pitch offset applied.
    Uses real PNG images from assets/sprites/ when available,
    falls back to colored rectangle.
    """
    from ui.sprite_loader import get as get_img

    sw, sh   = surface.get_size()
    horizon  = sh // 2 + pitch

    for sp in sorted(sprites,
                     key=lambda s: (s["x"] - px) ** 2 + (s["y"] - py) ** 2,
                     reverse=True):
        dx   = sp["x"] - px
        dy   = sp["y"] - py
        dist = math.hypot(dx, dy)
        if dist < 0.2:
            continue

        sp_angle = math.atan2(dy, dx) - angle
        while sp_angle >  math.pi: sp_angle -= 2 * math.pi
        while sp_angle < -math.pi: sp_angle += 2 * math.pi

        if abs(sp_angle) > HALF_FOV + 0.2:
            continue

        screen_x = int((sp_angle / FOV + 0.5) * sw)
        sprite_h = max(1, int(sh / dist * sp.get("size", 0.8)))
        sprite_w = sprite_h

        left = screen_x - sprite_w // 2
        top  = horizon  - sprite_h // 2   # shifted by pitch

        draw_top    = max(0,  top)
        draw_bottom = min(sh, top + sprite_h)
        if draw_bottom <= draw_top:
            continue

        src_y    = draw_top - top
        strip_h  = draw_bottom - draw_top

        img = get_img(sp.get("label", ""))
        if img and sprite_w > 0:
            try:
                scaled = pygame.transform.scale(img, (sprite_w, sprite_h))
                for col in range(max(0, left), min(sw, left + sprite_w)):
                    if z_buffer[col] <= dist:
                        continue
                    col_in = col - left
                    if 0 <= col_in < sprite_w:
                        surface.blit(scaled.subsurface((col_in, src_y, 1, strip_h)),
                                     (col, draw_top))
            except Exception:
                img = None   # fall through to color rect

        if not img:
            color = _shade(sp.get("color", (200, 100, 100)), dist, MAX_DEPTH * 0.8)
            for col in range(max(0, left), min(sw, left + sprite_w)):
                if z_buffer[col] <= dist:
                    continue
                pygame.draw.line(surface, color, (col, draw_top), (col, draw_bottom))


# ─────────────────────────────────────────────────────────────────────────────
# Crosshair hit detection
# ─────────────────────────────────────────────────────────────────────────────

def find_aimed_sprite(sprites: list, px: float, py: float,
                      angle: float, z_buffer: list[float],
                      sw: int, sh: int, pitch: int = 0) -> dict | None:
    """
    Returns the first enemy sprite whose billboard covers the screen center
    (crosshair) and is not occluded by a wall. Only checks is_enemy sprites.
    """
    cx      = sw // 2
    cy      = sh // 2        # crosshair is always at screen center
    horizon = sh // 2 + pitch

    best_dist = MAX_DEPTH
    aimed     = None

    for sp in sprites:
        if not sp.get("is_enemy") or sp.get("hp", 0) <= 0:
            continue

        dx   = sp["x"] - px
        dy   = sp["y"] - py
        dist = math.hypot(dx, dy)
        if dist < 0.2 or dist >= best_dist:
            continue

        sp_angle = math.atan2(dy, dx) - angle
        while sp_angle >  math.pi: sp_angle -= 2 * math.pi
        while sp_angle < -math.pi: sp_angle += 2 * math.pi

        if abs(sp_angle) > HALF_FOV + 0.1:
            continue

        screen_x = int((sp_angle / FOV + 0.5) * sw)
        sprite_h = max(1, int(sh / dist * sp.get("size", 0.8)))
        sprite_w = sprite_h

        left = screen_x - sprite_w // 2
        top  = horizon  - sprite_h // 2

        draw_top    = max(0,  top)
        draw_bottom = min(sh, top + sprite_h)

        # crosshair must be inside the sprite's screen rect
        if not (left <= cx < left + sprite_w and draw_top <= cy < draw_bottom):
            continue

        # not behind a wall
        if 0 <= cx < len(z_buffer) and z_buffer[cx] <= dist:
            continue

        best_dist = dist
        aimed     = sp

    return aimed

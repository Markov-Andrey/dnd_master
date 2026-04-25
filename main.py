"""
Project Dusk — entry point.
First-person raycasting RPG (TES2/Daggerfall style).

Combat: real-time in the 3D world.
  Enemies move toward player on aggro, attack with cooldown.
  LMB / Space = player attack (cooldown-gated, range-gated).
  No separate combat screen — everything in the game view.

Controls:
  W/S          forward / backward
  A/D          strafe left / right
  Arrow L/R    rotate (keyboard fallback)
  Mouse move   rotate (primary, cursor captured in game view)
  LMB / Space  attack
  I/C/J        inventory / character / journal
  F5           quick save
  Esc          leave location / quit
"""
import pygame
import sys
import os
import math
import json
import random

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from engine.game        import GameState
from engine.dungeon_map import generate_dungeon, generate_for_location
from engine.world       import World
from ui.raycaster       import cast_rays, render_sprites, find_aimed_sprite
from ui.hud             import render_hud, HUD_H
from ui.world_map_view  import render_world_map
from ui import overlay

# ── window ────────────────────────────────────────────────────────────────────
WIN_W, WIN_H = 960, 640
VIEW_H       = WIN_H - HUD_H
FPS          = 60

# ── movement ──────────────────────────────────────────────────────────────────
MOVE_SPEED        = 2.5
ROT_SPEED         = 2.0
MOUSE_SENSITIVITY  = 0.003        # rad/pixel horizontal
MOUSE_PITCH_SPEED  = 0.40         # pixels/pixel vertical
PITCH_MAX          = VIEW_H // 3  # clamp: don't look too far up/down

# ── camera bob ────────────────────────────────────────────────────────────────
BOB_SPEED     = 9.0   # oscillation frequency (rad/sec)
BOB_MAX       = 6     # max vertical pixel shift
BOB_RISE_RATE = 25.0  # px/sec bob amplitude rise when walking
BOB_FALL_RATE = 15.0  # px/sec bob amplitude fall when standing still

# ── NPC interaction ────────────────────────────────────────────────────────────
NPC_TALK_RANGE = 2.0   # tiles

# ── combat ────────────────────────────────────────────────────────────────────
PLAYER_ATTACK_RANGE = 1.4   # tiles
PLAYER_ATTACK_BASE  = 0.7   # seconds base cooldown
HIT_FLASH_DUR       = 0.12  # seconds red-screen flash on being hit

# ── entity templates ──────────────────────────────────────────────────────────
ENEMY_TEMPLATES = {
    "Skeleton": dict(hp=25, level=1, attack_speed=1.3, attack_range=1.2,
                     aggro_range=7.0, move_speed=1.3, damage_min=3, damage_max=7,
                     armor=1, color=(210, 210, 195), size=0.95),
    "Zombie":   dict(hp=35, level=1, attack_speed=1.8, attack_range=1.1,
                     aggro_range=5.0, move_speed=0.9, damage_min=4, damage_max=9,
                     armor=0, color=(90, 160, 80),  size=1.0),
    "Rat":      dict(hp=10, level=1, attack_speed=0.8, attack_range=0.9,
                     aggro_range=4.0, move_speed=2.2, damage_min=1, damage_max=4,
                     armor=0, color=(160, 120, 80), size=0.55),
    "Goblin":   dict(hp=18, level=1, attack_speed=1.0, attack_range=1.0,
                     aggro_range=6.0, move_speed=1.8, damage_min=2, damage_max=6,
                     armor=2, color=(100, 160, 80), size=0.8),
}
NPC_TEMPLATES = {
    "Житель":   dict(color=(80, 130, 210),  size=0.85, is_enemy=False),
    "Стражник": dict(color=(180, 160, 80),  size=0.9,  is_enemy=False),
    "Торговец": dict(color=(100, 190, 120), size=0.85, is_enemy=False),
    "Путник":   dict(color=(160, 100, 180), size=0.85, is_enemy=False),
    "Фермер":   dict(color=(200, 150, 80),  size=0.85, is_enemy=False),
}


# ── damage helpers (module-level, no closures needed) ─────────────────────────

def _player_damage(player) -> int:
    weapon     = player.equipped.get("weapon") or {}
    dmg_min    = weapon.get("damage_min", 3)  if isinstance(weapon, dict) else weapon.damage_min
    dmg_max    = weapon.get("damage_max", 8)  if isinstance(weapon, dict) else weapon.damage_max
    skill_name = weapon.get("weapon_skill", "blade") if isinstance(weapon, dict) else "blade"
    skill      = player.skills.get(skill_name, 10)
    str_bonus  = (player.attributes["strength"] - 50) // 5
    return max(1, random.randint(dmg_min, dmg_max) + str_bonus + skill // 10)

def _player_attack_speed(player) -> float:
    weapon     = player.equipped.get("weapon") or {}
    skill_name = weapon.get("weapon_skill", "blade") if isinstance(weapon, dict) else "blade"
    skill      = player.skills.get(skill_name, 10)
    return max(0.3, PLAYER_ATTACK_BASE - skill * 0.003)

def _player_mitigation(player) -> int:
    armor = player.equipped.get("armor") or {}
    arm   = armor.get("defense", 0) if isinstance(armor, dict) else getattr(armor, "defense", 0)
    return arm + player.attributes["agility"] // 10

def _enemy_damage(sp: dict) -> int:
    return random.randint(sp["damage_min"], sp["damage_max"])


# ─────────────────────────────────────────────────────────────────────────────
# Minimal NPC wrapper for dialogue (no full NPC class needed)
# ─────────────────────────────────────────────────────────────────────────────

class _QuickNPC:
    """Тонкая обёртка NPC для overlay.render_dialogue. Поддерживает авторские и дефолтные данные."""

    _GREET = {
        "Житель":   "Добрый день, странник. Что привело тебя сюда?",
        "Стражник": "Стой. Назови своё дело, путник.",
        "Торговец": "О, покупатель! Что-то ищешь купить или продать?",
        "Путник":   "Попутчик! Дороги нынче опасны.",
        "Фермер":   "М? А, привет. Тяжёлый день на полях.",
    }
    _REPLY = {
        "Житель":   "Тяжёлые времена. Береги себя в дороге.",
        "Стражник": "Следуй дальше. Не создавай проблем в моём городе.",
        "Торговец": "Как-нибудь в другой раз. Удачи в пути!",
        "Путник":   "Держись дорог и смотри по сторонам.",
        "Фермер":   "Ничего интересного — только поля да грязь.",
    }

    def __init__(self, sprite: dict):
        self.name       = sprite.get("_npc_name") or sprite.get("label", "Незнакомец")
        self.npc_type   = sprite.get("_npc_type", "житель")
        self._greeting  = (sprite.get("_greeting")
                           or self._GREET.get(sprite.get("label", ""), "Привет, странник."))
        self.reply      = (sprite.get("_hello_reply")
                           or self._REPLY.get(sprite.get("label", ""), "Береги себя."))
        self._options   = sprite.get("_options", ["Привет", "До свидания"])

    def greet(self) -> str:
        return self._greeting

    def get_dialogue_options(self) -> list[str]:
        return self._options


# ── top-level render helpers ──────────────────────────────────────────────────

def _render_target(surface, sp: dict, font_sm, font_md):
    """Полоска ОЗ + имя цели под прицелом."""
    cx   = WIN_W // 2
    hp   = sp["hp"]
    hp_m = sp.get("hp_max", hp)
    t    = font_md.render(f"{sp['label']}  {hp}/{hp_m}", True, (220, 180, 80))
    surface.blit(t, (cx - t.get_width() // 2, 14))
    frac = max(0.0, hp / max(1, hp_m))
    bw   = 160
    bx, by = cx - bw // 2, 14 + t.get_height() + 4
    pygame.draw.rect(surface, (40, 40, 40),  (bx, by, bw, 12))
    pygame.draw.rect(surface, (180, 40, 40), (bx, by, int(bw * frac), 12))
    pygame.draw.rect(surface, (80, 60, 40),  (bx, by, bw, 12), 1)


def _draw_minimap(surface, dungeon_map, px, py, angle, ox, oy, size):
    tile = max(2, size // dungeon_map.width)
    mm   = pygame.Surface((dungeon_map.width * tile, dungeon_map.height * tile),
                           pygame.SRCALPHA)
    mm.fill((0, 0, 0, 160))
    for y in range(dungeon_map.height):
        for x in range(dungeon_map.width):
            cell = dungeon_map.get_cell(x, y)
            col  = ((70, 60, 50, 200)  if cell == 0 else
                    (160, 120, 60, 200) if cell == 2 else
                    (30, 25, 20, 200))
            pygame.draw.rect(mm, col, (x * tile, y * tile, tile - 1, tile - 1))
    pdx, pdy = int(px * tile), int(py * tile)
    pygame.draw.circle(mm, (255, 220, 0, 255), (pdx, pdy), max(2, tile))
    pygame.draw.line(mm, (255, 220, 0, 255), (pdx, pdy),
                     (int(pdx + math.cos(angle) * tile * 2),
                      int(pdy + math.sin(angle) * tile * 2)), 1)
    surface.blit(pygame.transform.scale(mm, (size, size)), (ox, oy))
    pygame.draw.rect(surface, (80, 70, 50), (ox, oy, size, size), 1)


# ── main ──────────────────────────────────────────────────────────────────────

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    pygame.display.set_caption("Project Dusk")
    clock  = pygame.time.Clock()

    from ui.sprite_loader import preload_all
    preload_all()   # warm image cache before the main loop

    # Consolas — лучший Cyrillic-совместимый моноширный шрифт на Windows
    _font_names = ["consolas", "couriernew", "lucidaconsole", "dejavusansmono", "monospace"]
    def _mkfont(size, bold=False):
        for name in _font_names:
            f = pygame.font.SysFont(name, size, bold=bold)
            if f:
                return f
        return pygame.font.Font(None, size)

    font_sm = _mkfont(13)
    font_md = _mkfont(17, bold=True)
    font_lg = _mkfont(28, bold=True)

    view3d = pygame.Surface((WIN_W, VIEW_H))
    state  = GameState()

    with open(os.path.join("data", "races.json"),   encoding="utf-8") as f:
        races_data = json.load(f)
    with open(os.path.join("data", "classes.json"), encoding="utf-8") as f:
        classes_data = json.load(f)
    with open(os.path.join("data", "enemies.json"), encoding="utf-8") as f:
        enemies_data = json.load(f)

    # ── mutable game state ────────────────────────────────────────────────────
    player_angle     = 0.0
    pitch_offset     = 0       # vertical look: pixel shift of horizon
    bob_time         = 0.0    # oscillation phase (radians)
    bob_active       = 0.0    # current amplitude (0 → BOB_MAX)
    current_map      = None
    location_sprites = []
    aimed_sprite     = None    # enemy under crosshair this frame
    player_attack_cd = 0.0   # counts DOWN to 0
    player_hit_flash = 0.0   # counts DOWN to 0
    mouse_captured   = False
    last_click_tile  = None  # ((gx,gy), time_ms) for double-click on world map

    # ── mouse capture ─────────────────────────────────────────────────────────
    def capture_mouse():
        nonlocal mouse_captured
        pygame.event.set_grab(True)
        pygame.mouse.set_visible(False)
        mouse_captured = True

    def release_mouse():
        nonlocal mouse_captured
        pygame.event.set_grab(False)
        pygame.mouse.set_visible(True)
        mouse_captured = False

    def sync_mouse():
        if state.current_screen == "game":
            if not mouse_captured: capture_mouse()
        else:
            if mouse_captured: release_mouse()

    # ── location management ───────────────────────────────────────────────────
    def enter_location(loc_id: str):
        nonlocal current_map, player_angle, pitch_offset, player_attack_cd
        loc = state.world.locations.get(loc_id)
        if not loc:
            return
        # generate_for_location uses authored content_file if available,
        # otherwise falls back to proc-gen dungeon
        current_map = generate_for_location(loc)
        state.player.loc_x = current_map.spawn_x
        state.player.loc_y = current_map.spawn_y
        player_angle     = 0.0
        pitch_offset     = 0
        player_attack_cd = 0.0
        state.enter_location(loc_id)
        state.current_screen = "game"
        state.log(f"Вы вошли в {loc.name}.")
        _populate_sprites(loc)
        capture_mouse()

    def leave_location():
        nonlocal current_map
        current_map = None
        location_sprites.clear()
        state.leave_location()
        state.current_screen = "world_map"
        release_mouse()

    def _populate_sprites(loc):
        """
        Fill location_sprites.
        - If current_map has authored_npcs (from content_file): use those.
        - Otherwise: proc-gen NPCs (outdoor) or enemies (dungeon).
        """
        location_sprites.clear()
        loc_id     = loc.location_id
        is_outdoor = loc.loc_type in ("city", "village")
        rng        = random.Random(hash(loc_id) ^ 0xDEAD)

        if current_map.authored_npcs:
            # ── authored NPCs from content file ───────────────────────────────
            for npc in current_map.authored_npcs:
                pos   = npc.get("position", [current_map.spawn_x, current_map.spawn_y])
                label = npc.get("label", "Villager")
                color = NPC_TEMPLATES.get(label, NPC_TEMPLATES["Villager"])["color"]
                size  = NPC_TEMPLATES.get(label, NPC_TEMPLATES["Villager"])["size"]
                location_sprites.append({
                    "x":         float(pos[0]) + 0.5,
                    "y":         float(pos[1]) + 0.5,
                    "label":     label,
                    "is_enemy":  False,
                    "color":     color,
                    "size":      size,
                    # extra authored data — used to build dialogue
                    "_npc_id":       npc.get("id"),
                    "_npc_name":     npc.get("name", label),
                    "_npc_type":     npc.get("type", "villager"),
                    "_greeting":     npc.get("greeting"),
                    "_hello_reply":  npc.get("hello_reply"),
                    "_options":      npc.get("options", ["Hello", "Farewell"]),
                })

        elif is_outdoor:
            # ── proc-gen outdoor NPCs ─────────────────────────────────────────
            names = list(NPC_TEMPLATES.keys())
            for i in range(rng.randint(5, 10)):
                label = names[i % len(names)]
                tmpl  = dict(NPC_TEMPLATES[label])
                for _ in range(40):
                    sx = rng.uniform(3, current_map.width  - 3)
                    sy = rng.uniform(3, current_map.height - 3)
                    if current_map.is_passable(int(sx), int(sy)):
                        location_sprites.append({"x": sx, "y": sy,
                                                  "label": label, **tmpl})
                        break
        else:
            # ── proc-gen dungeon enemies ──────────────────────────────────────
            pool = [e for e in enemies_data.values()
                    if "dungeon" in e.get("locations", [])] or list(enemies_data.values())
            for _ in range(rng.randint(3, 6)):
                base  = dict(rng.choice(pool))
                color = base.get("color", [200, 100, 100])
                sp = {
                    "x": 0.0, "y": 0.0,
                    "label":          base["label"],
                    "is_enemy":       True,
                    "hp":             base["hp"],
                    "hp_max":         base["hp"],
                    "level":          base.get("level", 1),
                    "attack_speed":   base["attack_speed"],
                    "attack_cooldown":rng.uniform(0.5, base["attack_speed"]),
                    "attack_range":   base["attack_range"],
                    "aggro_range":    base["aggro_range"],
                    "move_speed":     base["move_speed"],
                    "damage_min":     base["damage_min"],
                    "damage_max":     base["damage_max"],
                    "armor":          base.get("armor", 0),
                    "color":          tuple(color),
                    "size":           base.get("size", 0.9),
                    "xp":             base.get("xp", 10),
                    "gold_min":       base.get("gold_min", 0),
                    "gold_max":       base.get("gold_max", 5),
                }
                for _ in range(40):
                    sx = rng.uniform(3, current_map.width  - 3)
                    sy = rng.uniform(3, current_map.height - 3)
                    if current_map.is_passable(int(sx), int(sy)):
                        sp["x"], sp["y"] = sx, sy
                        location_sprites.append(sp)
                        break

    # ── player attack ─────────────────────────────────────────────────────────
    def player_attack():
        nonlocal player_attack_cd
        if player_attack_cd > 0:
            return
        p      = state.player
        target = aimed_sprite   # set each frame by find_aimed_sprite
        weapon     = p.equipped.get("weapon") or {}
        skill_name = weapon.get("weapon_skill", "blade") if isinstance(weapon, dict) else "blade"
        if target and math.hypot(target["x"] - p.loc_x, target["y"] - p.loc_y) <= PLAYER_ATTACK_RANGE:
            dmg    = _player_damage(p)
            actual = max(1, dmg - target.get("armor", 0))
            target["hp"] -= actual
            p.gain_skill_xp(skill_name)
            state.log(f"Удар по {target['label']}: -{actual} ОЗ.")
            if target["hp"] <= 0:
                gold = random.randint(1, target.get("level", 1) * 8)
                p.gold += gold
                p.gain_skill_xp(skill_name, 3)
                state.log(f"{target['label']} повержен! +{gold} золота.")
                if target in location_sprites:
                    location_sprites.remove(target)
        else:
            state.log("Нет цели в прицеле.")
        player_attack_cd = _player_attack_speed(p)

    # ── char-creation helpers ─────────────────────────────────────────────────
    def _cc_key(event):
        step = getattr(state, "_cc_step", "race")
        sel  = getattr(state, "_cc_sel",  0)
        if step == "race":
            ks = list(races_data.keys())
            if event.key in (pygame.K_UP, pygame.K_w):
                state._cc_sel = (sel - 1) % len(ks)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                state._cc_sel = (sel + 1) % len(ks)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                state._cc_race = ks[sel]; state._cc_step = "class"; state._cc_sel = 0
        elif step == "class":
            ks = list(classes_data.keys())
            if event.key in (pygame.K_UP, pygame.K_w):
                state._cc_sel = (sel - 1) % len(ks)
            elif event.key in (pygame.K_DOWN, pygame.K_s):
                state._cc_sel = (sel + 1) % len(ks)
            elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                state._cc_class = ks[sel]; state._cc_step = "name"; state._cc_name = ""
            elif event.key == pygame.K_BACKSPACE:
                state._cc_step = "race"; state._cc_sel = 0
        elif step == "name":
            buf = getattr(state, "_cc_name", "")
            if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER) and buf.strip():
                state.new_game(player_name=buf.strip(), race=state._cc_race,
                               char_class=state._cc_class,
                               seed=World.DEFAULT_SEED)
                state.player.loc_x = state.player.loc_y = 0.0
            elif event.key == pygame.K_BACKSPACE:
                if buf: state._cc_name = buf[:-1]
                else: state._cc_step = "class"; state._cc_sel = 0
            elif len(event.unicode) == 1 and ord(event.unicode) >= 32 and len(buf) < 20:
                state._cc_name = buf + event.unicode

    def _cc_click(mx, my):
        step = getattr(state, "_cc_step", "race")
        sel  = getattr(state, "_cc_sel",  0)
        if step == "race":
            ks = list(races_data.keys())
            ih = font_md.get_height() + font_sm.get_height() + 14
            for i, k in enumerate(ks):
                iy = 110 + i * ih
                if iy <= my <= iy + ih:
                    if sel == i: state._cc_race = k; state._cc_step = "class"; state._cc_sel = 0
                    else: state._cc_sel = i
                    break
        elif step == "class":
            ks = list(classes_data.keys())
            ih = font_md.get_height() + font_sm.get_height() * 2 + 20
            for i, k in enumerate(ks):
                iy = 110 + i * ih
                if iy <= my <= iy + ih:
                    if sel == i: state._cc_class = k; state._cc_step = "name"; state._cc_name = ""
                    else: state._cc_sel = i
                    break

    def _menu_select(i: int):
        if i == 0:
            state._cc_step = "race"; state._cc_sel = 0
            state._cc_name = state._cc_race = state._cc_class = None
            state.current_screen = "char_creation"
        elif i == 1:
            if not state.load(0): state.log("Сохранение не найдено.")
            elif state.player.location_id: enter_location(state.player.location_id)
        elif i == 2:
            pygame.quit(); sys.exit()

    def _equip_toggle(item):
        slot = item.get("slot") if isinstance(item, dict) else getattr(item, "slot", None)
        if not slot: return
        if state.player.equipped.get(slot) == item: del state.player.equipped[slot]
        else: state.player.equipped[slot] = item

    def _dlg_select(opt: str):
        if opt in ("До свидания", "Farewell"):
            state.current_screen = "game"
            state._dlg_npc  = None
            state._dlg_text = None
            capture_mouse()
        elif opt in ("Привет", "Hello"):
            npc = getattr(state, "_dlg_npc", None)
            state._dlg_text = npc.reply if npc else "..."
        else:
            state._dlg_text = f"[{opt}] — пока не реализовано."

    # ── NPC proximity search ──────────────────────────────────────────────────
    def _find_nearby_npc(sprites, px, py):
        best, best_dist = None, NPC_TALK_RANGE
        for sp in sprites:
            if sp.get("is_enemy", False):
                continue
            d = math.hypot(sp["x"] - px, sp["y"] - py)
            if d < best_dist:
                best_dist, best = d, sp
        return best

    # ── world map tile coords ─────────────────────────────────────────────────
    def _wm_tile_at(mx, my):
        t = max(4, min((WIN_W - 260) // state.world.SIZE, (WIN_H - 20) // state.world.SIZE))
        gx, gy = (mx - 10) // t, (my - 10) // t
        if 0 <= gx < state.world.SIZE and 0 <= gy < state.world.SIZE:
            return gx, gy
        return None

    # ═════════════════════════════════════════════════════════════════════════
    # MAIN LOOP
    # ═════════════════════════════════════════════════════════════════════════
    while True:
        dt = clock.tick(FPS) / 1000.0

        # ── events ────────────────────────────────────────────────────────────
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            sc = state.current_screen

            if event.type == pygame.MOUSEMOTION and sc == "game":
                player_angle += event.rel[0] * MOUSE_SENSITIVITY
                # negate rel[1]: mouse down = look down = horizon rises = negative offset
                pitch_offset  = max(-PITCH_MAX,
                                    min(PITCH_MAX,
                                        pitch_offset - int(event.rel[1] * MOUSE_PITCH_SPEED)))

            if event.type == pygame.MOUSEWHEEL and sc == "inventory":
                inv = state.player.inventory
                state.player._inv_sel = max(0, min(
                    len(inv) - 1, getattr(state.player, "_inv_sel", 0) - event.y))

            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos

                if event.button == 1:
                    if sc == "game":
                        player_attack()

                    elif sc == "main_menu":
                        ty = WIN_H // 4 + 6 * 20 + 40
                        for i in range(3):
                            if abs(my - (ty + i * 40)) < 20:
                                state._menu_sel = i
                                _menu_select(i)
                                break

                    elif sc == "char_creation":
                        _cc_click(mx, my)

                    elif sc == "world_map":
                        pos = _wm_tile_at(mx, my)
                        if pos:
                            gx, gy = pos
                            now = pygame.time.get_ticks()
                            dx = gx - state.player.world_x
                            dy = gy - state.player.world_y
                            if dx:  state.move_player(1 if dx > 0 else -1, 0)
                            elif dy: state.move_player(0, 1 if dy > 0 else -1)
                            if (last_click_tile and last_click_tile[0] == pos
                                    and now - last_click_tile[1] < 400):
                                locs = state.world.get_locations_at(gx, gy)
                                if locs: enter_location(locs[0].location_id)
                            last_click_tile = (pos, now)

                    elif sc == "inventory":
                        inv = state.player.inventory
                        pw  = 700; px2 = (WIN_W - pw) // 2; py2 = (WIN_H - 460) // 2
                        i   = (my - (py2 + 65)) // 22
                        if px2 <= mx <= px2 + pw // 2 and 0 <= i < len(inv):
                            if getattr(state.player, "_inv_sel", -1) == i:
                                _equip_toggle(inv[i])
                            else:
                                state.player._inv_sel = i

                    elif sc == "dialogue":
                        npc = getattr(state, "_dlg_npc", None)
                        if npc:
                            opts  = npc.get_dialogue_options()
                            pw, ph = 640, 360
                            oy0   = (WIN_H - ph - 20) + ph - len(opts) * 26 - 30
                            i     = (my - oy0) // 26
                            if 0 <= i < len(opts):
                                state._dlg_sel = i; _dlg_select(opts[i])

                elif event.button == 2 and sc == "game":
                    capture_mouse()   # MMB: recapture if focus lost

            # ── keyboard ──────────────────────────────────────────────────────
            if event.type == pygame.KEYDOWN:
                sc = state.current_screen

                if sc == "main_menu":
                    sel = getattr(state, "_menu_sel", 0)
                    if event.key in (pygame.K_UP, pygame.K_w):
                        state._menu_sel = (sel - 1) % 3
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        state._menu_sel = (sel + 1) % 3
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        _menu_select(sel)
                    elif event.key == pygame.K_ESCAPE:
                        pygame.quit(); sys.exit()

                elif sc == "char_creation":
                    _cc_key(event)

                elif sc == "world_map":
                    if event.key == pygame.K_e:
                        locs = state.world.get_locations_at(
                            state.player.world_x, state.player.world_y)
                        if locs: enter_location(locs[0].location_id)
                    elif event.key == pygame.K_i:
                        state.player._inv_sel = 0; state.current_screen = "inventory"
                    elif event.key == pygame.K_c:
                        state.current_screen = "status"
                    elif event.key == pygame.K_j:
                        state.player._journal_tab = 0; state.current_screen = "journal"
                    elif event.key == pygame.K_F5:
                        state.save(0); state.log("Игра сохранена.")
                    elif event.key in (pygame.K_q, pygame.K_ESCAPE):
                        state.save(0); pygame.quit(); sys.exit()

                elif sc == "game":
                    if event.key == pygame.K_ESCAPE:
                        leave_location()
                    elif event.key in (pygame.K_SPACE, pygame.K_RETURN):
                        player_attack()
                    elif event.key == pygame.K_e:
                        npc_sp = _find_nearby_npc(location_sprites,
                                                   state.player.loc_x, state.player.loc_y)
                        if npc_sp:
                            state._dlg_npc  = _QuickNPC(npc_sp)
                            state._dlg_sel  = 0
                            state._dlg_text = None
                            state.current_screen = "dialogue"
                            release_mouse()
                    elif event.key == pygame.K_i:
                        state.player._inv_sel = 0; state.current_screen = "inventory"
                        release_mouse()
                    elif event.key == pygame.K_c:
                        state.current_screen = "status"; release_mouse()
                    elif event.key == pygame.K_j:
                        state.player._journal_tab = 0; state.current_screen = "journal"
                        release_mouse()
                    elif event.key == pygame.K_F5:
                        state.save(0); state.log("Игра сохранена.")

                elif sc == "inventory":
                    inv = state.player.inventory
                    sel = getattr(state.player, "_inv_sel", 0)
                    if event.key == pygame.K_ESCAPE:
                        state.current_screen = "game" if state.player.location_id else "world_map"
                        sync_mouse()
                    elif event.key == pygame.K_UP:
                        state.player._inv_sel = max(0, sel - 1)
                    elif event.key == pygame.K_DOWN:
                        state.player._inv_sel = min(len(inv) - 1, sel + 1)
                    elif event.key == pygame.K_e and inv and 0 <= sel < len(inv):
                        _equip_toggle(inv[sel])

                elif sc in ("status", "journal"):
                    if event.key == pygame.K_ESCAPE:
                        state.current_screen = "game" if state.player.location_id else "world_map"
                        sync_mouse()
                    elif sc == "journal":
                        if event.key == pygame.K_1: state.player._journal_tab = 0
                        elif event.key == pygame.K_2: state.player._journal_tab = 1
                        elif event.key == pygame.K_3: state.player._journal_tab = 2

                elif sc == "dialogue":
                    npc = getattr(state, "_dlg_npc", None)
                    if npc:
                        opts    = npc.get_dialogue_options()
                        dlg_sel = getattr(state, "_dlg_sel", 0)
                        if event.key == pygame.K_UP:
                            state._dlg_sel = (dlg_sel - 1) % len(opts)
                        elif event.key == pygame.K_DOWN:
                            state._dlg_sel = (dlg_sel + 1) % len(opts)
                        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            _dlg_select(opts[dlg_sel])
                        elif event.key == pygame.K_ESCAPE:
                            state.current_screen = "game"; capture_mouse()

        # ── continuous movement ────────────────────────────────────────────────
        sc   = state.current_screen
        keys = pygame.key.get_pressed()

        if sc == "world_map":
            t = getattr(state, "_wm_timer", 0.0) + dt
            if t >= 0.18:
                state._wm_timer = 0.0
                dx = dy = 0
                if keys[pygame.K_w] or keys[pygame.K_UP]:     dy = -1
                elif keys[pygame.K_s] or keys[pygame.K_DOWN]: dy =  1
                if keys[pygame.K_a] or keys[pygame.K_LEFT]:   dx = -1
                elif keys[pygame.K_d] or keys[pygame.K_RIGHT]: dx = 1
                if dx or dy: state.move_player(dx, dy)
            else:
                state._wm_timer = t

        elif sc == "game" and current_map:
            p   = state.player
            spd = MOVE_SPEED * p.move_speed * dt
            rot = ROT_SPEED  * dt

            if keys[pygame.K_LEFT]:  player_angle -= rot
            if keys[pygame.K_RIGHT]: player_angle += rot

            nx, ny = p.loc_x, p.loc_y
            if keys[pygame.K_w] or keys[pygame.K_UP]:
                nx += math.cos(player_angle) * spd
                ny += math.sin(player_angle) * spd
            if keys[pygame.K_s] or keys[pygame.K_DOWN]:
                nx -= math.cos(player_angle) * spd
                ny -= math.sin(player_angle) * spd
            if keys[pygame.K_a]:
                nx += math.cos(player_angle - math.pi / 2) * spd
                ny += math.sin(player_angle - math.pi / 2) * spd
            if keys[pygame.K_d]:
                nx += math.cos(player_angle + math.pi / 2) * spd
                ny += math.sin(player_angle + math.pi / 2) * spd

            R = 0.25
            if (current_map.is_passable(int(nx), int(p.loc_y)) and
                    current_map.is_passable(
                        int(nx + R * math.copysign(1, nx - p.loc_x)), int(p.loc_y))):
                p.loc_x = nx
            if (current_map.is_passable(int(p.loc_x), int(ny)) and
                    current_map.is_passable(
                        int(p.loc_x), int(ny + R * math.copysign(1, ny - p.loc_y)))):
                p.loc_y = ny

            # camera bob — rise when moving, decay when still
            is_moving = (keys[pygame.K_w] or keys[pygame.K_s] or
                         keys[pygame.K_a] or keys[pygame.K_d] or
                         keys[pygame.K_UP] or keys[pygame.K_DOWN])
            if is_moving:
                bob_time   += dt * BOB_SPEED
                bob_active  = min(BOB_MAX, bob_active + dt * BOB_RISE_RATE)
            else:
                bob_active  = max(0.0, bob_active - dt * BOB_FALL_RATE)

        # ── real-time game logic ───────────────────────────────────────────────
        if sc == "game" and current_map:
            p = state.player

            # tick cooldowns and flash
            player_attack_cd = max(0.0, player_attack_cd - dt)
            player_hit_flash = max(0.0, player_hit_flash - dt)

            # stamina regen
            p.stamina = min(p.stamina_max,
                            p.stamina + p.attributes["endurance"] / 200.0 * dt)

            # enemy AI
            dead = []
            for sp in location_sprites:
                if not sp.get("is_enemy"):
                    continue
                if sp.get("hp", 0) <= 0:
                    dead.append(sp); continue

                dx   = p.loc_x - sp["x"]
                dy   = p.loc_y - sp["y"]
                dist = math.hypot(dx, dy)

                if dist < sp.get("aggro_range", 7.0):
                    # chase
                    if dist > sp.get("attack_range", 1.2) + 0.05:
                        step_e = sp.get("move_speed", 1.3) * dt
                        ndx    = sp["x"] + (dx / dist) * step_e
                        ndy    = sp["y"] + (dy / dist) * step_e
                        if current_map.is_passable(int(ndx), int(sp["y"])): sp["x"] = ndx
                        if current_map.is_passable(int(sp["x"]), int(ndy)): sp["y"] = ndy
                    # attack
                    sp["attack_cooldown"] = sp.get("attack_cooldown", 0.0) - dt
                    if sp["attack_cooldown"] <= 0 and dist <= sp.get("attack_range", 1.2):
                        sp["attack_cooldown"] = sp["attack_speed"]
                        dmg    = _enemy_damage(sp)
                        actual = max(1, dmg - _player_mitigation(p))
                        p.hp   = max(0, p.hp - actual)
                        player_hit_flash = HIT_FLASH_DUR
                        state.log(f"{sp['label']} бьёт вас на {actual} урона!")
                        if not p.is_alive:
                            state.log("Вы погибли! Загрузка последнего сохранения...")
                            dead_all = list(location_sprites)
                            if not state.load(0):
                                state.current_screen = "main_menu"
                            else:
                                leave_location()
                else:
                    sp["attack_cooldown"] = sp.get("attack_cooldown", 0.0) - dt

            for sp in dead:
                if sp in location_sprites:
                    location_sprites.remove(sp)

        # ── render ────────────────────────────────────────────────────────────
        screen.fill((0, 0, 0))
        sc = state.current_screen

        if sc == "main_menu":
            overlay.render_main_menu(screen, state, font_sm, font_md, font_lg)

        elif sc == "char_creation":
            overlay.render_char_creation(screen, state, font_sm, font_md,
                                         races_data, classes_data)

        elif sc == "world_map":
            render_world_map(screen, state.world, state.player, font_sm, font_md)

        elif sc == "game":
            p          = state.player
            bob_px     = int(math.sin(bob_time) * bob_active)  # vertical bob in pixels
            eff_pitch  = pitch_offset + bob_px                  # pitch used for rendering
            z_buf = cast_rays(view3d, current_map, p.loc_x, p.loc_y,
                              player_angle, eff_pitch)
            render_sprites(view3d, location_sprites, p.loc_x, p.loc_y,
                           player_angle, z_buf, eff_pitch)
            screen.blit(view3d, (0, 0))

            # aim detection uses raw pitch_offset (no bob) — stable crosshair
            aimed_sprite = find_aimed_sprite(
                location_sprites, p.loc_x, p.loc_y,
                player_angle, z_buf, WIN_W, VIEW_H, pitch_offset)

            # crosshair — green when aimed at enemy in range, red on cooldown, grey otherwise
            cx, cy = WIN_W // 2, VIEW_H // 2
            if aimed_sprite and math.hypot(aimed_sprite["x"] - p.loc_x,
                                           aimed_sprite["y"] - p.loc_y) <= PLAYER_ATTACK_RANGE:
                col_ch = (80, 255, 80) if player_attack_cd == 0 else (255, 80, 80)
            else:
                col_ch = (180, 180, 180)
            pygame.draw.line(screen, col_ch, (cx - 12, cy), (cx + 12, cy), 1)
            pygame.draw.line(screen, col_ch, (cx, cy - 12), (cx, cy + 12), 1)

            # hit flash
            if player_hit_flash > 0:
                a  = int(180 * player_hit_flash / HIT_FLASH_DUR)
                fl = pygame.Surface((WIN_W, VIEW_H), pygame.SRCALPHA)
                fl.fill((200, 0, 0, a))
                screen.blit(fl, (0, 0))

            # target display — only when crosshair is on an enemy
            if aimed_sprite:
                _render_target(screen, aimed_sprite, font_sm, font_md)

            _draw_minimap(screen, current_map, p.loc_x, p.loc_y, player_angle,
                          WIN_W - 130, 10, 120)
            render_hud(screen, p, state.time, state.message_log, font_sm, font_md)

        elif sc in ("inventory", "status", "journal", "dialogue"):
            if current_map and state.player.location_id:
                p     = state.player
                z_buf = cast_rays(view3d, current_map, p.loc_x, p.loc_y,
                                  player_angle, pitch_offset)
                render_sprites(view3d, location_sprites, p.loc_x, p.loc_y,
                               player_angle, z_buf, pitch_offset)
                screen.blit(view3d, (0, 0))
            else:
                render_world_map(screen, state.world, state.player, font_sm, font_md)

            if sc == "inventory":
                overlay.render_inventory(screen, state.player, font_sm, font_md)
            elif sc == "status":
                overlay.render_status(screen, state.player, font_sm, font_md)
            elif sc == "journal":
                overlay.render_journal(screen, state.player, font_sm, font_md)
            elif sc == "dialogue":
                npc = getattr(state, "_dlg_npc", None)
                if npc:
                    overlay.render_dialogue(screen, npc,
                                            getattr(state, "_dlg_sel", 0),
                                            getattr(state, "_dlg_text", None),
                                            font_sm, font_md)

        pygame.display.flip()


if __name__ == "__main__":
    main()

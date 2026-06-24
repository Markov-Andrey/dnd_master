"""Рендер карт: SVG глобальная + локальная, ASCII fallback."""
from world.world_map import WorldMap
from world.location import Location


LOCATION_ICONS = {
    "village": "🏠", "forest": "🌲", "cave": "🕳", "lake": "💧",
    "mountain": "⛰", "ruins": "🏚", "swamp": "🐊", "crossroads": "✕",
}

GRID_POSITIONS = {
    "village": (1, 2),
    "forest": (1, 1),
    "cave": (2, 2),
    "lake": (0, 2),
    "mountain": (1, 3),
    "ruins": (2, 3),
    "swamp": (0, 1),
    "crossroads": (1, 0),
}

TILE_ICONS = {
    "village": "🏠", "forest": "🌲", "cave": "🕳", "lake": "💧",
    "mountain": "⛰", "ruins": "🏚", "swamp": "🐊", "crossroads": "✕",
}


def render_global_svg(world: WorldMap, tile: int = 56, pad: int = 20) -> str:
    """Глобальная карта: тайловая сетка с цветными квадратами."""
    grid = {loc_id: pos for loc_id, pos in GRID_POSITIONS.items()}
    if not grid:
        return ""

    xs = [p[0] for p in grid.values()]
    ys = [p[1] for p in grid.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    cols = max_x - min_x + 1
    rows = max_y - min_y + 1
    w = cols * tile + pad * 2
    h = rows * tile + pad * 2

    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" style="background:#0a0a0a;border-radius:8px;">'

    svg += '<defs>'
    svg += '<filter id="glow"><feGaussianBlur stdDeviation="3" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
    svg += '<filter id="shadow"><feDropShadow dx="0" dy="1" stdDeviation="2" flood-opacity="0.5"/></filter>'
    svg += '</defs>'

    for cy in range(min_y, max_y + 1):
        for cx in range(min_x, max_x + 1):
            px = pad + (cx - min_x) * tile
            py = pad + (cy - min_y) * tile

            loc_id = None
            for lid, pos in grid.items():
                if pos == (cx, cy):
                    loc_id = lid
                    break

            if not loc_id:
                svg += f'<rect x="{px}" y="{py}" width="{tile}" height="{tile}" fill="#111" rx="4" stroke="#1a1a1a" stroke-width="1" opacity="0.3"/>'
                continue

            loc = world.locations.get(loc_id)
            if not loc:
                continue

            is_current = loc_id == world.current_location_id
            is_visited = loc.visited
            bg = loc.tile_color if is_visited else "#2a2a2a"
            stroke = "#d4af37" if is_current else ("#3a3a2a" if is_visited else "#1a1a1a")
            stroke_w = 3 if is_current else 1
            opacity = 1.0 if is_visited else 0.5

            if is_current:
                svg += f'<rect x="{px - 3}" y="{py - 3}" width="{tile + 6}" height="{tile + 6}" fill="none" stroke="#d4af37" stroke-width="2" rx="6" opacity="0.4"><animate attributeName="opacity" values="0.4;0.1;0.4" dur="2s" repeatCount="indefinite"/></rect>'

            svg += f'<rect x="{px}" y="{py}" width="{tile}" height="{tile}" fill="{bg}" stroke="{stroke}" stroke-width="{stroke_w}" rx="4" opacity="{opacity}" filter="url(#shadow)" data-loc="{loc_id}" class="map-tile"/>'

            icon = TILE_ICONS.get(loc_id, "")
            if icon:
                svg += f'<text x="{px + tile // 2}" y="{py + tile // 2 - 2}" text-anchor="middle" dominant-baseline="central" font-size="{tile // 2.5}">{icon}</text>'

            name = loc.name
            svg += f'<text x="{px + tile // 2}" y="{py + tile - 6}" text-anchor="middle" font-size="8" fill="{"#fff" if is_visited else "#555"}" font-family="Segoe UI, sans-serif" opacity="0.9">{name}</text>'

            if is_visited and not is_current:
                svg += f'<rect x="{px}" y="{py}" width="{tile}" height="{tile}" fill="transparent" rx="4" data-loc="{loc_id}" class="map-tile"/>'

    svg += '</svg>'
    return svg


def render_local_svg(loc: Location, tile: int = 72, pad: int = 16, completed_encounters: set = None, current_subarea: str = None) -> str:
    """Локальная карта: тайловая сетка подобластей."""
    if not loc or not loc.local_map:
        return ""

    lm = loc.local_map
    grid = lm.get("grid", {})
    subareas = lm.get("subareas", [])
    if completed_encounters is None:
        completed_encounters = set()

    sa_map = {sa["id"]: sa for sa in subareas}

    if not grid:
        return ""

    xs = [p[0] for p in grid.values()]
    ys = [p[1] for p in grid.values()]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    cols = max_x - min_x + 1
    rows = max_y - min_y + 1
    w = cols * tile + pad * 2
    h = rows * tile + pad * 2

    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" style="background:#0a0a0a;border-radius:8px;">'

    svg += '<defs>'
    svg += '<filter id="shadow"><feDropShadow dx="0" dy="1" stdDeviation="2" flood-opacity="0.5"/></filter>'
    svg += '</defs>'

    for cy in range(min_y, max_y + 1):
        for cx in range(min_x, max_x + 1):
            px = pad + (cx - min_x) * tile
            py = pad + (cy - min_y) * tile

            sa_id = None
            for sid, pos in grid.items():
                if pos == [cx, cy]:
                    sa_id = sid
                    break

            if not sa_id:
                continue

            sa = sa_map.get(sa_id)
            if not sa:
                continue

            color = sa.get("color", "#555")
            has_npc = "npc_id" in sa
            has_enc = "encounter" in sa
            enc_done = has_enc and f'{loc.id}:{sa_id}' in completed_encounters

            is_current = sa_id == current_subarea
            stroke = "#d4af37" if is_current else ("#d4af37" if has_npc else ("#c0392b" if has_enc and not enc_done else ("#555" if enc_done else "#2a2a2a")))
            stroke_w = 3 if is_current or has_npc or (has_enc and not enc_done) else 1
            opacity = 1.0 if not enc_done else 0.4

            npc_attr = f' data-npc="{sa["npc_id"]}"' if has_npc else ""
            enc_attr = f' data-encounter="{sa_id}"' if has_enc and not enc_done else ""
            cls = "local-area"
            if has_npc: cls += " has-npc"
            if has_enc and not enc_done: cls += " has-encounter"
            if is_current: cls += " current"

            if is_current:
                svg += f'<rect x="{px - 3}" y="{py - 3}" width="{tile + 6}" height="{tile + 6}" fill="none" stroke="#d4af37" stroke-width="3" rx="8" opacity="0.6"><animate attributeName="opacity" values="0.6;0.2;0.6" dur="2s" repeatCount="indefinite"/></rect>'
            elif has_npc:
                svg += f'<rect x="{px - 3}" y="{py - 3}" width="{tile + 6}" height="{tile + 6}" fill="none" stroke="#d4af37" stroke-width="2" rx="6" opacity="0.4"><animate attributeName="opacity" values="0.4;0.15;0.4" dur="2s" repeatCount="indefinite"/></rect>'
            elif has_enc and not enc_done:
                svg += f'<rect x="{px - 3}" y="{py - 3}" width="{tile + 6}" height="{tile + 6}" fill="none" stroke="#c0392b" stroke-width="2" rx="6" opacity="0.4"><animate attributeName="opacity" values="0.4;0.2;0.4" dur="1.5s" repeatCount="indefinite"/></rect>'

            svg += f'<rect x="{px}" y="{py}" width="{tile}" height="{tile}" fill="{color}" rx="6" stroke="{stroke}" stroke-width="{stroke_w}" opacity="{opacity}" filter="url(#shadow)" data-area="{sa_id}" class="{cls}"{enc_attr}{npc_attr}/>'

            icon = sa.get("icon", "")
            if icon:
                svg += f'<text x="{px + tile // 2}" y="{py + tile // 2 - 4}" text-anchor="middle" dominant-baseline="central" font-size="{tile // 3}">{icon}</text>'

            name = ("✓ " if enc_done else "") + sa.get("name", "")
            svg += f'<text x="{px + tile // 2}" y="{py + tile - 6}" text-anchor="middle" font-size="10" fill="{"#888" if enc_done else "white"}" font-weight="bold" opacity="0.9" font-family="Segoe UI, sans-serif">{name}</text>'

    svg += '</svg>'
    return svg


def render_ascii(world: WorldMap, view_radius: int = 3) -> str:
    pos = world.get_position()
    if not pos:
        return "Нет позиции"
    cx, cy = pos
    lines = []
    for y in range(cy - view_radius, cy + view_radius + 1):
        row = []
        for x in range(cx - view_radius, cx + view_radius + 1):
            loc_id = world.grid.get((x, y))
            if loc_id == world.current_location_id:
                row.append("@@")
            elif loc_id:
                loc = world.locations[loc_id]
                row.append(loc.name[:2].upper())
            else:
                row.append("··")
        lines.append(" ".join(row))
    return "\n".join(lines)


def render_minimap(world: WorldMap) -> str:
    return render_ascii(world, view_radius=2)


def render_legend(world: WorldMap) -> str:
    lines = ["=== КАРТА МИРА ==="]
    for loc_id, loc in world.locations.items():
        icon = LOCATION_ICONS.get(loc_id, "?")
        marker = " ◀ ВЫ ЗДЕСЬ" if loc_id == world.current_location_id else ""
        lines.append(f"  {icon} {loc.name}{marker}")
        for direction, target_id in loc.exits.items():
            target = world.locations.get(target_id)
            if target:
                t_icon = LOCATION_ICONS.get(target_id, "?")
                lines.append(f"    {direction} → {t_icon} {target.name}")
    return "\n".join(lines)

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


def render_local_svg(loc: Location, w: int = 480, h: int = 380) -> str:
    """Локальная карта: детальный вид текущей локации."""
    if not loc or not loc.local_map:
        return ""

    lm = loc.local_map
    subareas = lm.get("subareas", [])
    paths = lm.get("paths", [])

    sa_map = {sa["id"]: sa for sa in subareas}

    svg = f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="100%" style="background:#0a0a0a;border-radius:8px;">'

    svg += '<defs>'
    svg += '<filter id="glow"><feGaussianBlur stdDeviation="2" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>'
    svg += '<filter id="shadow"><feDropShadow dx="0" dy="1" stdDeviation="1.5" flood-opacity="0.4"/></filter>'
    svg += '</defs>'

    for a_id, b_id in paths:
        a = sa_map.get(a_id)
        b = sa_map.get(b_id)
        if not a or not b:
            continue
        ax = a["x"] + a["w"] // 2
        ay = a["y"] + a["h"] // 2
        bx = b["x"] + b["w"] // 2
        by = b["y"] + b["h"] // 2
        svg += f'<line x1="{ax}" y1="{ay}" x2="{bx}" y2="{by}" stroke="#3a3a2a" stroke-width="1.5" stroke-dasharray="4,3" opacity="0.4"/>'

    for sa in subareas:
        x, y, sw, sh = sa["x"], sa["y"], sa["w"], sa["h"]
        color = sa.get("color", "#555")
        has_npc = "npc_id" in sa
        npc_attr = f' data-npc="{sa["npc_id"]}"' if has_npc else ""

        stroke = "#d4af37" if has_npc else "#2a2a2a"
        stroke_w = 2 if has_npc else 1
        opacity = "0.85"

        svg += f'<rect x="{x}" y="{y}" width="{sw}" height="{sh}" fill="{color}" rx="6" stroke="{stroke}" stroke-width="{stroke_w}" opacity="{opacity}" filter="url(#shadow)" data-area="{sa["id"]}" class="local-area{"" if not has_npc else " has-npc"}"{npc_attr}/>'

        icon = sa.get("icon", "")
        if icon:
            ix = x + sw // 2 - 8
            iy = y + sh // 2 - 12
            svg += f'<text x="{x + sw // 2}" y="{y + sh // 2 + 4}" text-anchor="middle" font-size="20">{icon}</text>'

        label_y = y + sh - 6
        svg += f'<text x="{x + sw // 2}" y="{label_y}" text-anchor="middle" font-size="9" fill="white" font-weight="bold" opacity="0.85" font-family="Segoe UI, sans-serif">{sa["name"]}</text>'

        if has_npc:
            svg += f'<rect x="{x - 2}" y="{y - 2}" width="{sw + 4}" height="{sh + 4}" fill="none" stroke="#d4af37" stroke-width="1.5" rx="8" opacity="0.4"><animate attributeName="opacity" values="0.4;0.15;0.4" dur="2s" repeatCount="indefinite"/></rect>'

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

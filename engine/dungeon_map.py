import json
import os
import random
from dataclasses import dataclass, field
from typing import Optional

# Cell types
EMPTY = 0
WALL  = 1
DOOR  = 2
WATER = 3

# Wall color hints (used by renderer to pick palette)
WALL_STONE  = 1
WALL_BRICK  = 4
WALL_WOOD   = 5


@dataclass
class DungeonMap:
    width: int = 32
    height: int = 32
    grid: list = field(default_factory=list)
    spawn_x: float = 1.5
    spawn_y: float = 1.5
    exit_x: int = 0
    exit_y: int = 0
    name:        str  = "Dungeon"
    is_outdoor:  bool = False
    authored_npcs: list = field(default_factory=list)
    # Each authored NPC dict: id, name, type, label, position[x,y],
    #                          greeting, hello_reply, options

    def __post_init__(self):
        if not self.grid:
            self.grid = [[WALL] * self.width for _ in range(self.height)]

    def is_wall(self, x: int, y: int) -> bool:
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return True
        return self.grid[y][x] == WALL

    def is_passable(self, x: int, y: int) -> bool:
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return False
        return self.grid[y][x] != WALL

    def get_cell(self, x: int, y: int) -> int:
        if x < 0 or y < 0 or x >= self.width or y >= self.height:
            return WALL
        return self.grid[y][x]

    def set_cell(self, x: int, y: int, value: int):
        if 0 <= x < self.width and 0 <= y < self.height:
            self.grid[y][x] = value


def generate_dungeon(seed: int, width: int = 32, height: int = 32,
                     name: str = "Dungeon", is_outdoor: bool = False) -> DungeonMap:
    rng = random.Random(seed)
    dm = DungeonMap(width=width, height=height, name=name, is_outdoor=is_outdoor)

    if is_outdoor:
        _generate_outdoor(dm, rng)
    else:
        _generate_dungeon_rooms(dm, rng)

    return dm


def _generate_dungeon_rooms(dm: DungeonMap, rng: random.Random):
    rooms = []

    for _ in range(15):
        w = rng.randint(3, 8)
        h = rng.randint(3, 8)
        x = rng.randint(1, dm.width - w - 2)
        y = rng.randint(1, dm.height - h - 2)

        # check no overlap (with 1-cell border)
        overlap = any(
            rx - 1 <= x + w and rx + rw + 1 >= x and
            ry - 1 <= y + h and ry + rh + 1 >= y
            for rx, ry, rw, rh in rooms
        )
        if overlap:
            continue

        rooms.append((x, y, w, h))
        for cy in range(y, y + h):
            for cx in range(x, x + w):
                dm.set_cell(cx, cy, EMPTY)

    # connect rooms in order with L-shaped corridors
    for i in range(len(rooms) - 1):
        x1 = rooms[i][0] + rooms[i][2] // 2
        y1 = rooms[i][1] + rooms[i][3] // 2
        x2 = rooms[i + 1][0] + rooms[i + 1][2] // 2
        y2 = rooms[i + 1][1] + rooms[i + 1][3] // 2

        for cx in range(min(x1, x2), max(x1, x2) + 1):
            dm.set_cell(cx, y1, EMPTY)
        for cy in range(min(y1, y2), max(y1, y2) + 1):
            dm.set_cell(x2, cy, EMPTY)

    if rooms:
        r = rooms[0]
        dm.spawn_x = r[0] + r[2] / 2.0
        dm.spawn_y = r[1] + r[3] / 2.0
        if len(rooms) > 1:
            er = rooms[-1]
            dm.exit_x = er[0] + er[2] // 2
            dm.exit_y = er[1] + er[3] // 2
    else:
        dm.spawn_x, dm.spawn_y = 1.5, 1.5
        dm.set_cell(1, 1, EMPTY)


def _generate_outdoor(dm: DungeonMap, rng: random.Random):
    """Open outdoor area with building perimeters as walls."""
    # fill with empty (grass)
    for y in range(dm.height):
        for x in range(dm.width):
            dm.set_cell(x, y, EMPTY)

    # border walls
    for x in range(dm.width):
        dm.set_cell(x, 0, WALL)
        dm.set_cell(x, dm.height - 1, WALL)
    for y in range(dm.height):
        dm.set_cell(0, y, WALL)
        dm.set_cell(dm.width - 1, y, WALL)

    # place building footprints (hollow rectangles)
    for _ in range(rng.randint(3, 7)):
        bw = rng.randint(4, 8)
        bh = rng.randint(4, 7)
        bx = rng.randint(2, dm.width - bw - 2)
        by = rng.randint(2, dm.height - bh - 2)
        for cy in range(by, by + bh):
            for cx in range(bx, bx + bw):
                if cy == by or cy == by + bh - 1 or cx == bx or cx == bx + bw - 1:
                    dm.set_cell(cx, cy, WALL)
        # door on south wall
        door_x = bx + bw // 2
        dm.set_cell(door_x, by + bh - 1, DOOR)

    dm.spawn_x = dm.width / 2.0
    dm.spawn_y = dm.height / 2.0
    dm.set_cell(int(dm.spawn_x), int(dm.spawn_y), EMPTY)


# ── authored content loader ────────────────────────────────────────────────────

_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def generate_for_location(location) -> DungeonMap:
    """
    Generate (or load) the DungeonMap for a Location object.

    If location.content_file is set, loads that JSON and builds an authored map:
      - Buildings are placed as hollow wall rectangles with a door.
      - spawn, map size, and authored_npcs come from the file.

    Falls back to procedural generation when content_file is None.
    """
    if location.content_file:
        path = os.path.join(_DATA_DIR, location.content_file)
        if os.path.exists(path):
            try:
                with open(path, encoding="utf-8") as f:
                    content = json.load(f)
                return _build_from_content(content, location)
            except Exception as e:
                print(f"[dungeon_map] Failed to load {path}: {e}")

    # proc-gen fallback
    is_outdoor = location.loc_type in ("city", "village")
    w = 40 if is_outdoor else 32
    h = 40 if is_outdoor else 32
    return generate_dungeon(
        seed       = hash(location.location_id) & 0xFFFFFF,
        width      = w,
        height     = h,
        name       = location.name,
        is_outdoor = is_outdoor,
    )


def _build_from_content(content: dict, location) -> DungeonMap:
    """Build a DungeonMap from an authored content JSON dict."""
    w  = content.get("map_width",  40)
    h  = content.get("map_height", 40)
    dm = DungeonMap(
        width      = w,
        height     = h,
        name       = content.get("name", location.name),
        is_outdoor = content.get("is_outdoor", True),
    )

    # fill with empty
    for y in range(h):
        for x in range(w):
            dm.set_cell(x, y, EMPTY)

    # border
    for x in range(w):
        dm.set_cell(x, 0, WALL)
        dm.set_cell(x, h - 1, WALL)
    for y in range(h):
        dm.set_cell(0, y, WALL)
        dm.set_cell(w - 1, y, WALL)

    # authored buildings
    for bld in content.get("buildings", []):
        bx, by, bw, bh = bld["x"], bld["y"], bld["w"], bld["h"]
        for cy in range(by, by + bh):
            for cx in range(bx, bx + bw):
                if cy == by or cy == by + bh - 1 or cx == bx or cx == bx + bw - 1:
                    dm.set_cell(cx, cy, WALL)
        # door on south face, centre
        dm.set_cell(bx + bw // 2, by + bh - 1, DOOR)

    # spawn
    sp = content.get("spawn", [w // 2, h // 2])
    dm.spawn_x = float(sp[0]) + 0.5
    dm.spawn_y = float(sp[1]) + 0.5
    dm.set_cell(int(dm.spawn_x), int(dm.spawn_y), EMPTY)

    # authored NPCs — stored on the map, consumed by _populate_sprites in main.py
    dm.authored_npcs = content.get("npcs", [])

    return dm

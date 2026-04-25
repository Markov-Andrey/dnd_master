"""
World — fully authored locations, deterministic terrain.

All cities, villages and dungeons come from data/world_layout.json.
No proc-gen locations. Terrain between locations is generated from a fixed seed
(deterministic, always the same) but can be overridden per-cell in the layout.

Each location may have a content_file pointing to data/content/*.json which
provides the detailed map, buildings, and named NPCs for that location.
If content_file is null the location gets a proc-gen interior at runtime.
"""
import json
import os
import random
from dataclasses import dataclass, field
from typing import Optional

TERRAIN_TYPES = ["plains", "forest", "mountains", "coast", "desert", "swamp", "tundra"]
TERRAIN_CHARS = {
    "plains": ".", "forest": "T", "mountains": "^", "coast": "~",
    "desert": "d", "swamp":  "S", "tundra":    "_",
}
TERRAIN_MOVE_COST = {
    "plains": 1, "forest": 2, "mountains": 3, "coast": 1,
    "desert": 2, "swamp":  3, "tundra":    2,
}

_LAYOUT_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                             "data", "world_layout.json")


@dataclass
class Location:
    location_id:   str
    name:          str
    loc_type:      str    # city | village | dungeon
    region_x:      int
    region_y:      int
    description:   str  = ""
    has_inn:       bool = False
    has_shop:      bool = False
    has_blacksmith:bool = False
    content_file:  Optional[str] = None   # relative to data/ dir


@dataclass
class Region:
    x:          int
    y:          int
    terrain:    str
    locations:  list = field(default_factory=list)
    is_explored:bool = False

    @property
    def char(self) -> str:
        return TERRAIN_CHARS.get(self.terrain, "?")

    @property
    def move_cost(self) -> int:
        return TERRAIN_MOVE_COST.get(self.terrain, 1)


class World:
    DEFAULT_SEED = 7777

    def __init__(self, seed: int = DEFAULT_SEED):
        self.seed      = seed
        self.SIZE      = 16
        self.regions:  list[list[Region]]   = []
        self.locations: dict[str, Location] = {}
        self._build()

    # ── build ──────────────────────────────────────────────────────────────────

    def _build(self):
        layout = self._load_layout()
        # seed may be overridden by layout file
        self.seed = layout.get("world_seed", self.seed)
        self.SIZE = layout.get("world_size", 16)

        rng = random.Random(self.seed)

        # 1. generate terrain grid deterministically
        self.regions = [[self._make_region(x, y, rng) for x in range(self.SIZE)]
                        for y in range(self.SIZE)]

        # 2. apply per-cell terrain overrides from layout
        for key, terrain in layout.get("terrain_overrides", {}).items():
            try:
                gx, gy = map(int, key.split(","))
                r = self.get_region(gx, gy)
                if r:
                    r.terrain = terrain
            except ValueError:
                pass

        # 3. place authored locations — the ONLY source of locations
        for loc_id, data in layout.get("locations", {}).items():
            loc = Location(
                location_id    = loc_id,
                name           = data["name"],
                loc_type       = data.get("type", "city"),
                region_x       = data["world_x"],
                region_y       = data["world_y"],
                description    = data.get("description", ""),
                has_inn        = data.get("has_inn", False),
                has_shop       = data.get("has_shop", False),
                has_blacksmith = data.get("has_blacksmith", False),
                content_file   = data.get("content_file"),
            )
            self.locations[loc_id] = loc
            region = self.get_region(loc.region_x, loc.region_y)
            if region and loc_id not in region.locations:
                region.locations.append(loc_id)

    def _load_layout(self) -> dict:
        if not os.path.exists(_LAYOUT_PATH):
            print("[World] data/world_layout.json not found — empty world.")
            return {}
        try:
            with open(_LAYOUT_PATH, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"[World] Failed to load world_layout.json: {e}")
            return {}

    def _make_region(self, x: int, y: int, rng: random.Random) -> Region:
        weights = {t: 1 for t in TERRAIN_TYPES}
        if x < 3 or x > 12:
            weights["coast"]  = 5
        if y < 3:
            weights["tundra"] = 4
        if y > 12:
            weights["desert"] = 3
        if 5 < x < 11 and 5 < y < 11:
            weights["plains"] = 4
            weights["forest"] = 3
        terrain = rng.choices(list(weights.keys()),
                              weights=list(weights.values()))[0]
        return Region(x=x, y=y, terrain=terrain)

    # ── queries ────────────────────────────────────────────────────────────────

    def get_region(self, x: int, y: int) -> Optional[Region]:
        if 0 <= x < self.SIZE and 0 <= y < self.SIZE:
            return self.regions[y][x]
        return None

    def get_locations_at(self, x: int, y: int) -> list[Location]:
        r = self.get_region(x, y)
        return [self.locations[lid] for lid in (r.locations if r else [])
                if lid in self.locations]

    def ascii_map(self, player_x: int, player_y: int, explored: set) -> list[str]:
        rows = []
        for y in range(self.SIZE):
            row = ""
            for x in range(self.SIZE):
                if x == player_x and y == player_y:
                    row += "@"
                elif f"{x},{y}" in explored:
                    r = self.regions[y][x]
                    if r.locations:
                        loc = self.locations.get(r.locations[0])
                        row += ({"city": "C", "village": "v", "dungeon": "D"}
                                .get(loc.loc_type, "?") if loc else r.char)
                    else:
                        row += r.char
                else:
                    row += " "
            rows.append(row)
        return rows

    def to_dict(self) -> dict:
        return {"seed": self.seed}

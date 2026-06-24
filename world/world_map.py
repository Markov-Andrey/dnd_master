"""Карта мира: сетка тайлов, текущая позиция, перемещение."""
from world.location import Location


class WorldMap:
    def __init__(self):
        self.locations: dict[str, Location] = {}
        self.current_location_id: str | None = None
        self.grid: dict[tuple[int, int], str] = {}  # (x, y) -> location_id

    def load_all(self):
        self.locations = Location.load_all()
        self._build_grid()

    def _build_grid(self):
        """Строим сетку из координат локаций."""
        positions = {
            "village": (0, 0),
            "forest": (0, -1),
            "cave": (1, 0),
            "lake": (-1, 0),
            "mountain": (0, 1),
            "ruins": (1, 1),
            "swamp": (-1, -1),
            "crossroads": (0, -2),
        }
        for loc_id, loc in self.locations.items():
            pos = positions.get(loc_id, (0, 0))
            self.grid[pos] = loc_id

    def set_position(self, location_id: str):
        self.current_location_id = location_id

    def get_current(self) -> Location | None:
        if not self.current_location_id:
            return None
        return self.locations.get(self.current_location_id)

    def get_position(self) -> tuple[int, int] | None:
        for pos, loc_id in self.grid.items():
            if loc_id == self.current_location_id:
                return pos
        return None

    def move(self, direction: str) -> Location | None:
        current = self.get_current()
        if not current or not current.can_go(direction):
            return None

        target_id = current.get_exit(direction)
        if target_id and target_id in self.locations:
            self.current_location_id = target_id
            self.locations[target_id].visited = True
            return self.locations[target_id]
        return None

    def get_visible_locations(self, radius: int = 2) -> list[dict]:
        """Возвращает локации в радиусе видимости для миникарты."""
        pos = self.get_position()
        if not pos:
            return []

        visible = []
        for (x, y), loc_id in self.grid.items():
            if abs(x - pos[0]) <= radius and abs(y - pos[1]) <= radius:
                loc = self.locations[loc_id]
                visible.append({
                    "id": loc.id, "name": loc.name, "x": x, "y": y,
                    "color": loc.tile_color, "current": loc_id == self.current_location_id,
                })
        return visible

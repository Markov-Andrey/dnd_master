from entities.character import Character


class Player(Character):
    """
    Extends Character with world position, location tracking, quests, and
    3D in-location coordinates (loc_x, loc_y) used by the raycaster.
    """

    def __init__(self, name: str, race: str, char_class: str):
        super().__init__(name=name, race=race, char_class=char_class)
        self.world_x: int = 8          # grid position on the 16x16 world map
        self.world_y: int = 8
        self.loc_x: float = 0.0        # float position inside a dungeon/city map
        self.loc_y: float = 0.0
        self.location_id: str | None = None  # None = travelling on world map
        self.visited_locations: set = set()
        self.known_quests: list = []
        self.active_quests: list = []
        self.completed_quests: list = []
        self.journal_entries: list = []
        self.abilities: list = []

    @property
    def position(self) -> tuple[int, int]:
        return (self.world_x, self.world_y)

    def move(self, dx: int, dy: int, world_size: int = 16):
        self.world_x = max(0, min(world_size - 1, self.world_x + dx))
        self.world_y = max(0, min(world_size - 1, self.world_y + dy))

    def enter_location(self, location_id: str):
        self.location_id = location_id
        self.visited_locations.add(location_id)

    def leave_location(self):
        self.location_id = None

    def add_quest(self, quest: dict):
        self.active_quests.append(quest)
        self.known_quests.append(quest["id"])

    def complete_quest(self, quest_id: str):
        self.active_quests = [q for q in self.active_quests if q["id"] != quest_id]
        self.completed_quests.append(quest_id)

    def add_journal(self, entry: str):
        self.journal_entries.append(entry)

    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update({
            "world_x": self.world_x, "world_y": self.world_y,
            "loc_x": self.loc_x, "loc_y": self.loc_y,
            "location_id": self.location_id,
            "visited_locations": list(self.visited_locations),
            "known_quests": self.known_quests,
            "active_quests": self.active_quests,
            "completed_quests": self.completed_quests,
            "journal_entries": self.journal_entries,
            "abilities": self.abilities,
        })
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "Player":
        p = cls(name=data["name"], race=data["race"], char_class=data["char_class"])
        p.attributes               = data["attributes"]
        p.skills                   = data["skills"]
        p.level                    = data["level"]
        p.skill_points_since_level = data["skill_points_since_level"]
        p.hp                       = data["hp"]
        p.hp_max                   = data["hp_max"]
        p.stamina                  = data["stamina"]
        p.stamina_max              = data["stamina_max"]
        p.gold                     = data["gold"]
        p.reputation               = data["reputation"]
        p.statuses                 = data["statuses"]
        p.inventory                = data["inventory"]
        p.equipped                 = data["equipped"]
        p.world_x                  = data["world_x"]
        p.world_y                  = data["world_y"]
        p.loc_x                    = data.get("loc_x", 0.0)
        p.loc_y                    = data.get("loc_y", 0.0)
        p.location_id              = data["location_id"]
        p.visited_locations        = set(data["visited_locations"])
        p.known_quests             = data["known_quests"]
        p.active_quests            = data["active_quests"]
        p.completed_quests         = data["completed_quests"]
        p.journal_entries          = data["journal_entries"]
        p.abilities                = data["abilities"]
        return p

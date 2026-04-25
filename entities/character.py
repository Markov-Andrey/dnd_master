from dataclasses import dataclass, field


BASE_ATTRIBUTES = {
    "strength": 50, "intelligence": 50, "willpower": 50, "agility": 50,
    "speed": 50, "endurance": 50, "personality": 50, "luck": 50,
}

ALL_SKILLS = [
    "blade", "blunt", "archery", "block",
    "sneak", "lockpick", "alchemy", "speechcraft", "mercantile",
]


@dataclass
class Character:
    name: str
    race: str
    char_class: str

    attributes: dict = field(default_factory=lambda: dict(BASE_ATTRIBUTES))
    skills: dict = field(default_factory=lambda: {s: 10 for s in ALL_SKILLS})
    level: int = 1
    skill_points_since_level: int = 0

    hp: int = 0
    hp_max: int = 0
    stamina: int = 0
    stamina_max: int = 0

    gold: int = 0
    reputation: int = 50
    statuses: list = field(default_factory=list)
    inventory: list = field(default_factory=list)
    equipped: dict = field(default_factory=dict)

    def __post_init__(self):
        self.recalculate_derived()

    def recalculate_derived(self):
        end = self.attributes["endurance"]
        agi = self.attributes["agility"]
        self.hp_max = 50 + end * 2 + self.level * (end // 10 + 1)
        self.stamina_max = 100 + agi
        if self.hp == 0:
            self.hp = self.hp_max
        if self.stamina == 0:
            self.stamina = self.stamina_max

    @property
    def carry_weight(self) -> int:
        return 50 + self.attributes["strength"] * 2

    @property
    def move_speed(self) -> float:
        return max(0.5, self.attributes["speed"] / 50.0)

    @property
    def is_alive(self) -> bool:
        return self.hp > 0

    def apply_attribute_bonuses(self, bonuses: dict):
        for attr, value in bonuses.items():
            if attr in self.attributes:
                self.attributes[attr] = max(1, min(100, self.attributes[attr] + value))
        self.recalculate_derived()

    def gain_skill_xp(self, skill: str, amount: int = 1):
        if skill not in self.skills:
            return
        self.skills[skill] = min(100, self.skills[skill] + amount)
        self.skill_points_since_level += amount
        if self.skill_points_since_level >= self._points_to_level():
            self._level_up()

    def _points_to_level(self) -> int:
        return 10 * self.level

    def _level_up(self):
        self.level += 1
        self.skill_points_since_level = 0
        self.recalculate_derived()
        self.hp = self.hp_max
        self.stamina = self.stamina_max

    def take_damage(self, amount: int, damage_type: str = "physical") -> int:
        armor = self.equipped.get("armor") or {}
        reduction = armor.get("defense", 0) if isinstance(armor, dict) else getattr(armor, "defense", 0)
        actual = max(1, amount - reduction)
        self.hp = max(0, self.hp - actual)
        return actual

    def heal(self, amount: int):
        self.hp = min(self.hp_max, self.hp + amount)

    def to_dict(self) -> dict:
        return {
            "name": self.name, "race": self.race, "char_class": self.char_class,
            "attributes": self.attributes, "skills": self.skills,
            "level": self.level, "skill_points_since_level": self.skill_points_since_level,
            "hp": self.hp, "hp_max": self.hp_max,
            "stamina": self.stamina, "stamina_max": self.stamina_max,
            "gold": self.gold, "reputation": self.reputation,
            "statuses": self.statuses, "inventory": self.inventory,
            "equipped": self.equipped,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Character":
        c = cls(name=data["name"], race=data["race"], char_class=data["char_class"])
        c.attributes = data["attributes"]
        c.skills = data["skills"]
        c.level = data["level"]
        c.skill_points_since_level = data["skill_points_since_level"]
        c.hp = data["hp"]
        c.hp_max = data["hp_max"]
        c.stamina = data["stamina"]
        c.stamina_max = data["stamina_max"]
        c.gold = data["gold"]
        c.reputation = data["reputation"]
        c.statuses = data["statuses"]
        c.inventory = data["inventory"]
        c.equipped = data["equipped"]
        return c

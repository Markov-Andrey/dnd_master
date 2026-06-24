"""Система голода и жажды: бонусы при достатке, без наказания при нехватке."""
from dataclasses import dataclass


@dataclass
class Vitals:
    hunger: float = 100.0   # 0-100, 100 = сыт
    thirst: float = 100.0   # 0-100, 100 = напоён

    def decay(self, hunger_rate: float = 2.0, thirst_rate: float = 3.0):
        self.hunger = max(0, self.hunger - hunger_rate)
        self.thirst = max(0, self.thirst - thirst_rate)

    def eat(self, amount: float = 30.0):
        self.hunger = min(100, self.hunger + amount)

    def drink(self, amount: float = 40.0):
        self.thirst = min(100, self.thirst + amount)

    def hunger_percent(self) -> float:
        return self.hunger / 100.0

    def thirst_percent(self) -> float:
        return self.thirst / 100.0

    def is_fed(self) -> bool:
        return self.hunger > 25

    def is_hydrated(self) -> bool:
        return self.thirst > 25

    def get_bonus_text(self) -> str:
        bonuses = []
        if self.hunger > 75:
            bonuses.append("Сытость: +1 к атаке")
        elif self.hunger > 50:
            bonuses.append("Сытость: +1 HP при отдыхе")
        if self.thirst > 75:
            bonuses.append("Напоённость: +1 к проверкам")
        elif self.thirst > 50:
            bonuses.append("Напоённость: +1 к инициативе")
        if not bonuses:
            return ""
        return "Бонусы: " + ", ".join(bonuses)

    def get_attack_bonus(self) -> int:
        if self.hunger > 75:
            return 1
        return 0

    def get_skill_bonus(self) -> int:
        if self.thirst > 75:
            return 1
        return 0

    def get_initiative_bonus(self) -> int:
        if self.thirst > 50:
            return 1
        return 0

    def get_heal_bonus(self) -> int:
        if self.hunger > 50:
            return 1
        return 0

    def to_dict(self) -> dict:
        return {
            "hunger": round(self.hunger, 1),
            "thirst": round(self.thirst, 1),
            "hunger_pct": round(self.hunger_percent() * 100),
            "thirst_pct": round(self.thirst_percent() * 100),
            "bonuses": self.get_bonus_text(),
        }

    def save(self) -> dict:
        return {"hunger": self.hunger, "thirst": self.thirst}

    @classmethod
    def load(cls, data: dict) -> "Vitals":
        return cls(hunger=data.get("hunger", 100), thirst=data.get("thirst", 100))

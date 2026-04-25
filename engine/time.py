class GameTime:
    HOURS_PER_DAY   = 24
    DAYS_PER_MONTH  = 30
    MONTHS_PER_YEAR = 12

    MONTH_NAMES = [
        "Рассвет", "Солнечная Заря", "Первый Сев", "Весенний Дождь",
        "Второй Сев", "Середина Года", "Высота Солнца", "Последний Сев",
        "Очаги", "Листопад", "Сумерки Солнца", "Вечерняя Звезда",
    ]

    def __init__(self, hour: int = 8, day: int = 1, month: int = 1, year: int = 400):
        self.hour   = hour
        self.day    = day
        self.month  = month
        self.year   = year
        self.minute = 0

    def advance(self, minutes: int = 10):
        self.minute += minutes
        while self.minute >= 60:
            self.minute -= 60
            self.hour   += 1
        while self.hour >= self.HOURS_PER_DAY:
            self.hour -= self.HOURS_PER_DAY
            self.day  += 1
        while self.day > self.DAYS_PER_MONTH:
            self.day   -= self.DAYS_PER_MONTH
            self.month += 1
        while self.month > self.MONTHS_PER_YEAR:
            self.month -= self.MONTHS_PER_YEAR
            self.year  += 1

    @property
    def is_night(self) -> bool:
        return self.hour < 6 or self.hour >= 22

    @property
    def time_str(self) -> str:
        period = "дн." if 6 <= self.hour < 18 else ("утра" if self.hour < 12 else "ночи")
        return f"{self.hour}:{self.minute:02d}"

    @property
    def date_str(self) -> str:
        return f"{self.day} {self.MONTH_NAMES[self.month - 1]}, {self.year} г."

    def to_dict(self) -> dict:
        return {"hour": self.hour, "minute": self.minute,
                "day": self.day, "month": self.month, "year": self.year}

    @classmethod
    def from_dict(cls, data: dict) -> "GameTime":
        t = cls(data["hour"], data["day"], data["month"], data["year"])
        t.minute = data["minute"]
        return t

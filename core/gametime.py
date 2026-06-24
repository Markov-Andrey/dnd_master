"""Система времени и погоды: день/ночь, цикл, влияние на gameplay."""
import random
from dataclasses import dataclass
from enum import Enum


class TimeOfDay(Enum):
    DAWN = "dawn"
    MORNING = "morning"
    NOON = "noon"
    AFTERNOON = "afternoon"
    EVENING = "evening"
    NIGHT = "night"
    MIDNIGHT = "midnight"


class Weather(Enum):
    CLEAR = "clear"
    CLOUDY = "cloudy"
    RAIN = "rain"
    STORM = "storm"
    FOG = "fog"
    SNOW = "snow"
    WIND = "wind"


TIME_NAMES = {
    TimeOfDay.DAWN: "Рассвет",
    TimeOfDay.MORNING: "Утро",
    TimeOfDay.NOON: "Полдень",
    TimeOfDay.AFTERNOON: "День",
    TimeOfDay.EVENING: "Вечер",
    TimeOfDay.NIGHT: "Ночь",
    TimeOfDay.MIDNIGHT: "Полночь",
}

WEATHER_NAMES = {
    Weather.CLEAR: "Ясно",
    Weather.CLOUDY: "Облачно",
    Weather.RAIN: "Дождь",
    Weather.STORM: "Гроза",
    Weather.FOG: "Туман",
    Weather.SNOW: "Снег",
    Weather.WIND: "Ветер",
}

WEATHER_EFFECTS = {
    Weather.CLEAR: {"perception": 0, "stealth": 0, "travel": 0},
    Weather.CLOUDY: {"perception": 0, "stealth": 0, "travel": 0},
    Weather.RAIN: {"perception": -1, "stealth": +1, "travel": -5},
    Weather.STORM: {"perception": -2, "stealth": +2, "travel": -10},
    Weather.FOG: {"perception": -2, "stealth": +3, "travel": -5},
    Weather.SNOW: {"perception": -1, "stealth": +1, "travel": -10},
    Weather.WIND: {"perception": 0, "stealth": 0, "travel": -5},
}

NIGHT_PENALTIES = {
    "perception": -1,
    "stealth": +2,
    "attack_ranged": -2,
}

LOCATION_TIME_MODIFIERS = {
    "forest": {"dawn": +1, "morning": 0, "noon": 0, "afternoon": 0, "evening": -1, "night": -2},
    "cave": {"dawn": 0, "morning": 0, "noon": 0, "afternoon": 0, "evening": 0, "night": 0},
    "village": {"dawn": 0, "morning": +1, "noon": 0, "afternoon": 0, "evening": 0, "night": -1},
    "mountain": {"dawn": -1, "morning": 0, "noon": 0, "afternoon": -1, "evening": -2, "night": -3},
}


@dataclass
class GameTime:
    hour: int = 8
    minute: int = 0
    day: int = 1
    time_of_day: TimeOfDay = TimeOfDay.MORNING
    weather: Weather = Weather.CLEAR
    weather_duration: int = 4
    
    def __post_init__(self):
        self.time_of_day = self._calc_time_of_day()
    
    def advance(self, minutes: int = 30):
        self.minute += minutes
        while self.minute >= 60:
            self.minute -= 60
            self.hour += 1
        
        if self.hour >= 24:
            self.hour -= 24
            self.day += 1
        
        self.time_of_day = self._calc_time_of_day()
        
        self.weather_duration -= 1
        if self.weather_duration <= 0:
            self.weather = self._random_weather()
            self.weather_duration = random.randint(2, 8)
    
    def _calc_time_of_day(self) -> TimeOfDay:
        if 5 <= self.hour < 7:
            return TimeOfDay.DAWN
        elif 7 <= self.hour < 12:
            return TimeOfDay.MORNING
        elif 12 <= self.hour < 14:
            return TimeOfDay.NOON
        elif 14 <= self.hour < 18:
            return TimeOfDay.AFTERNOON
        elif 18 <= self.hour < 21:
            return TimeOfDay.EVENING
        elif 21 <= self.hour < 24:
            return TimeOfDay.NIGHT
        else:
            return TimeOfDay.MIDNIGHT
    
    def _random_weather(self) -> Weather:
        weights = [30, 25, 20, 5, 10, 5, 5]
        return random.choices(list(Weather), weights=weights)[0]
    
    def is_night(self) -> bool:
        return self.time_of_day in (TimeOfDay.NIGHT, TimeOfDay.MIDNIGHT)
    
    def get_visibility(self) -> int:
        if self.is_night():
            return -2
        if self.time_of_day == TimeOfDay.DAWN:
            return -1
        return 0
    
    def get_modifiers(self, location_id: str = "") -> dict:
        mods = {"perception": 0, "stealth": 0, "travel": 0}
        
        weather_mods = WEATHER_EFFECTS.get(self.weather, {})
        for k in mods:
            mods[k] += weather_mods.get(k, 0)
        
        if self.is_night():
            for k, v in NIGHT_PENALTIES.items():
                if k in mods:
                    mods[k] += v
        
        loc_mods = LOCATION_TIME_MODIFIERS.get(location_id, {})
        mods["perception"] += loc_mods.get(self.time_of_day.value, 0)
        
        return mods
    
    def to_dict(self):
        return {
            "hour": self.hour,
            "minute": self.minute,
            "day": self.day,
            "time_of_day": self.time_of_day.value,
            "time_name": TIME_NAMES[self.time_of_day],
            "weather": self.weather.value,
            "weather_name": WEATHER_NAMES[self.weather],
            "is_night": self.is_night(),
            "modifiers": self.get_modifiers(),
        }
    
    def save(self):
        return {
            "hour": self.hour, "minute": self.minute, "day": self.day,
            "weather": self.weather.value, "weather_duration": self.weather_duration,
        }
    
    @classmethod
    def load(cls, data: dict) -> "GameTime":
        gt = cls(
            hour=data.get("hour", 8),
            minute=data.get("minute", 0),
            day=data.get("day", 1),
            weather_duration=data.get("weather_duration", 4),
        )
        try:
            gt.weather = Weather(data.get("weather", "clear"))
        except ValueError:
            gt.weather = Weather.CLEAR
        gt.time_of_day = gt._calc_time_of_day()
        return gt

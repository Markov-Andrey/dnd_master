"""Тесты времени и погоды."""
import pytest
from core.gametime import GameTime, TimeOfDay, Weather


class TestGameTime:
    def test_create_default(self):
        gt = GameTime()
        assert gt.hour == 8
        assert gt.day == 1
        assert gt.time_of_day == TimeOfDay.MORNING

    def test_advance_minutes(self):
        gt = GameTime()
        gt.advance(30)
        assert gt.hour == 8
        assert gt.minute == 30

    def test_advance_hours(self):
        gt = GameTime()
        gt.advance(120)
        assert gt.hour == 10

    def test_advance_day(self):
        gt = GameTime(hour=23, minute=30)
        gt.advance(60)
        assert gt.hour == 0
        assert gt.day == 2

    def test_time_of_day(self):
        cases = [
            (6, TimeOfDay.DAWN),
            (8, TimeOfDay.MORNING),
            (13, TimeOfDay.NOON),
            (16, TimeOfDay.AFTERNOON),
            (19, TimeOfDay.EVENING),
            (22, TimeOfDay.NIGHT),
            (2, TimeOfDay.MIDNIGHT),
        ]
        for hour, expected in cases:
            gt = GameTime(hour=hour)
            assert gt.time_of_day == expected, f"Hour {hour} should be {expected}"

    def test_is_night(self):
        gt = GameTime(hour=22)
        assert gt.is_night() is True
        gt = GameTime(hour=12)
        assert gt.is_night() is False

    def test_weather_changes(self):
        gt = GameTime()
        initial_weather = gt.weather
        gt.weather_duration = 0
        gt.advance(30)
        assert gt.weather_duration > 0

    def test_modifiers(self):
        gt = GameTime()
        mods = gt.get_modifiers("forest")
        assert "perception" in mods
        assert "stealth" in mods

    def test_to_dict(self):
        gt = GameTime()
        d = gt.to_dict()
        assert "hour" in d
        assert "time_name" in d
        assert "weather_name" in d

    def test_save_load(self):
        gt = GameTime(hour=14, day=5)
        saved = gt.save()
        loaded = GameTime.load(saved)
        assert loaded.hour == 14
        assert loaded.day == 5

    def test_visibility_night(self):
        gt = GameTime(hour=22)
        assert gt.get_visibility() < 0

    def test_visibility_day(self):
        gt = GameTime(hour=12)
        assert gt.get_visibility() == 0

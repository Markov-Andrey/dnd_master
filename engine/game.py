import json
import os
from engine.world import World
from engine.time import GameTime
from engine.events import bus
from entities.player import Player


SAVE_DIR = "saves"


class GameState:
    def __init__(self):
        self.player: Player | None = None
        self.world: World | None = None
        self.time: GameTime = GameTime()
        self.is_running: bool = False
        self.current_screen: str = "main_menu"
        self.message_log: list[str] = []

    # ---- lifecycle ----

    def new_game(self, player_name: str, race: str, char_class: str, seed: int = 42):
        self.player = Player(name=player_name, race=race, char_class=char_class)
        self._apply_race_class(race, char_class)
        self.world = World(seed=seed)
        self.time = GameTime()
        self.is_running = True
        self.current_screen = "world_map"
        self.log(f"Добро пожаловать, {player_name}. Ваше путешествие начинается.")
        bus.emit("new_game", self)

    def _apply_race_class(self, race: str, char_class: str):
        data_dir = "data"
        with open(os.path.join(data_dir, "races.json")) as f:
            races = json.load(f)
        with open(os.path.join(data_dir, "classes.json")) as f:
            classes = json.load(f)

        if race in races:
            self.player.apply_attribute_bonuses(races[race]["bonuses"])
        if char_class in classes:
            cls_data = classes[char_class]
            self.player.apply_attribute_bonuses(cls_data.get("stat_bonuses", {}))
            for skill in cls_data.get("primary_skills", []):
                if skill in self.player.skills:
                    self.player.skills[skill] += 15
            self.player.abilities = list(cls_data.get("starting_abilities", []))
            self.player.gold = 100

    # ---- saving / loading ----

    def save(self, slot: int = 0) -> str:
        os.makedirs(SAVE_DIR, exist_ok=True)
        path = os.path.join(SAVE_DIR, f"save_{slot}.json")
        data = {
            "player": self.player.to_dict(),
            "world_seed": self.world.seed,
            "time": self.time.to_dict(),
            "message_log": self.message_log[-50:],
        }
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        return path

    def load(self, slot: int = 0) -> bool:
        path = os.path.join(SAVE_DIR, f"save_{slot}.json")
        if not os.path.exists(path):
            return False
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        self.player = Player.from_dict(data["player"])
        self.world = World(seed=data["world_seed"])
        self.time = GameTime.from_dict(data["time"])
        self.message_log = data.get("message_log", [])
        self.is_running = True
        self.current_screen = "world_map"
        bus.emit("game_loaded", self)
        return True

    def list_saves(self) -> list[dict]:
        saves = []
        for slot in range(4):
            path = os.path.join(SAVE_DIR, f"save_{slot}.json")
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    data = json.load(f)
                p = data["player"]
                t = data["time"]
                saves.append({
                    "slot": slot,
                    "name": p["name"],
                    "level": p["level"],
                    "date": f"{t['day']}/{t['month']}/{t['year']}",
                })
        return saves

    # ---- world interaction ----

    def move_player(self, dx: int, dy: int):
        if not self.player or not self.world:
            return
        self.player.move(dx, dy)
        region = self.world.get_region(self.player.world_x, self.player.world_y)
        if region:
            region.is_explored = True
            key = f"{self.player.world_x},{self.player.world_y}"
            self.player.visited_locations.add(key)
            cost = region.move_cost
            self.time.advance(cost * 30)  # minutes per step
        bus.emit("player_moved", self.player.position)

    def enter_location(self, location_id: str):
        self.player.enter_location(location_id)
        self.current_screen = "location"
        self.time.advance(15)
        bus.emit("location_entered", location_id)

    def leave_location(self):
        self.player.leave_location()
        self.current_screen = "world_map"
        bus.emit("location_left", None)

    # ---- utilities ----

    def log(self, msg: str):
        self.message_log.append(msg)
        if len(self.message_log) > 200:
            self.message_log = self.message_log[-200:]

    def quit(self):
        self.is_running = False
        bus.emit("game_quit", None)

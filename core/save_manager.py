"""Система сохранений: полное состояние игры в JSON, загрузка."""
import json, os
from datetime import datetime


class SaveManager:
    def __init__(self, save_dir: str = "db/saves"):
        self.save_dir = save_dir
        os.makedirs(save_dir, exist_ok=True)
    
    def save_game(self, save_name: str, game_state: dict) -> str:
        game_state["saved_at"] = datetime.now().isoformat()
        path = os.path.join(self.save_dir, f"{save_name}.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(game_state, f, ensure_ascii=False, indent=2)
        return path
    
    def load_game(self, save_name: str) -> dict | None:
        path = os.path.join(self.save_dir, f"{save_name}.json")
        if not os.path.exists(path):
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    
    def list_saves(self) -> list[dict]:
        saves = []
        for f in os.listdir(self.save_dir):
            if f.endswith(".json"):
                path = os.path.join(self.save_dir, f)
                try:
                    with open(path, encoding="utf-8") as fh:
                        data = json.load(fh)
                    saves.append({
                        "name": f[:-5],
                        "saved_at": data.get("saved_at", "?"),
                        "player_name": data.get("player", {}).get("name", "?"),
                        "player_level": data.get("player", {}).get("level", 1),
                        "location": data.get("location_id", "?"),
                    })
                except Exception:
                    pass
        return sorted(saves, key=lambda s: s.get("saved_at", ""), reverse=True)
    
    def delete_save(self, save_name: str) -> bool:
        path = os.path.join(self.save_dir, f"{save_name}.json")
        if os.path.exists(path):
            os.remove(path)
            return True
        return False
    
    def get_quick_save_path(self) -> str:
        return os.path.join(self.save_dir, "quicksave.json")
    
    def quick_save(self, game_state: dict) -> str:
        return self.save_game("quicksave", game_state)
    
    def quick_load(self) -> dict | None:
        return self.load_game("quicksave")

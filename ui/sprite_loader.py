"""
Sprite image cache.
Maps entity labels to PNG files in assets/sprites/.
Returns None (silently) if a file doesn't exist yet — raycaster falls back to
the colored-rectangle placeholder in that case.
"""
import os
import pygame

_cache: dict[str, pygame.Surface | None] = {}

_SPRITES_DIR = os.path.join(
    os.path.dirname(os.path.dirname(__file__)),
    "assets", "sprites",
)

# Built from data/enemies.json at import time — label → filename.
# NPC sprites are listed separately (no enemies.json entry for them yet).
def _build_label_map() -> dict[str, str]:
    mapping: dict[str, str] = {
        "Житель":   "villager.png",
        "Стражник": "guard.png",
        "Торговец": "merchant.png",
        "Путник":   "traveller.png",
        "Фермер":   "farmer.png",
    }
    enemies_path = os.path.join(
        os.path.dirname(os.path.dirname(__file__)),
        "data", "enemies.json",
    )
    try:
        import json
        with open(enemies_path, encoding="utf-8") as f:
            data = json.load(f)
        for entry in data.values():
            label    = entry.get("label")
            filename = entry.get("sprite")
            if label and filename:
                mapping[label] = filename
    except Exception:
        pass
    return mapping

LABEL_TO_FILE: dict[str, str] = _build_label_map()


def get(label: str) -> "pygame.Surface | None":
    filename = LABEL_TO_FILE.get(label)
    if not filename:
        return None
    if filename in _cache:
        return _cache[filename]
    path = os.path.join(_SPRITES_DIR, filename)
    if not os.path.exists(path):
        _cache[filename] = None
        return None
    surf = pygame.image.load(path).convert_alpha()
    _cache[filename] = surf
    return surf


def preload_all():
    """Call once after pygame.init() to warm the cache."""
    for label in LABEL_TO_FILE:
        get(label)

"""Глобальные константы: LLM, БД, пороги отношений/эмоций/памяти."""
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(__file__))
BASE_DIR = os.path.join(PROJECT_ROOT, "core")

# LLM
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "http://localhost:8080/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "Qwen3.6-27B-abliterated-v2-Q4_K_M.gguf")
LLM_TEMPERATURE = 0.8
LLM_MAX_TOKENS = 2048

# БД
DB_DIR = os.path.join(PROJECT_ROOT, "db")
NPCS_DB_DIR = os.path.join(DB_DIR, "npcs")
PLAYERS_DB_DIR = os.path.join(DB_DIR, "players")
CHROMA_DB_DIR = os.path.join(DB_DIR, "chroma")
CHROMA_COLLECTION = "npc_memories"
NPC_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "npcs")
LOCATIONS_DATA_DIR = os.path.join(PROJECT_ROOT, "data", "locations")

# Диалог
RAG_TOP_K = 5
MAX_HISTORY = 2
SUMMARIZE_INTERVAL = 20

# Отношения: метки → диапазоны friendship
RELATIONSHIP_LEVELS = {
    "враг": (-100, -60), "незнакомец": (-59, -20), "чужой": (-19, 0),
    "знакомый": (1, 20), "друг": (21, 40), "хороший друг": (41, 60),
    "лучший друг": (61, 80), "родной": (81, 100),
}
LOVE_LEVELS = {
    "нет": (-100, 0), "симпатия": (1, 30), "влюблённость": (31, 60),
    "страсть": (61, 80), "любовь": (81, 100),
}

# Базовые дельты за действия
RELATIONSHIP_DELTAS = {
    "greet": 0, "talk": 0, "compliment": 1, "insult": -1,
    "help": 2, "betray": -2, "fear_trigger": -1, "like_trigger": 1,
    "apologize": 1, "forgive": 1,
}

# Память
MEMORY_WEIGHTS = {"important": 1.0, "emotional": 0.7, "casual": 0.3, "mistake": 0.2}
MEMORY_MISTAKE_DECAY = 20
MEMORY_FORGIVE_BONUS = 0.3

# Эмоции
EMOTION_DECAY = 3

# Карта
TILE_SIZE = 32

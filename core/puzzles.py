"""Система головоломок и мини-игр для ловушек/загадок.

Мини-игры на основе казуальных мобильных паттернов:
- memory_match — классические "Найди пару"
- color_sequence — повтори последовательность (Simon Says)
- slider — собери картинку (15-пазл)
- reaction — быстрое нажатие (Fruit Ninja стиль)
- word解开 — разгадай слово (Wordle)
- lockpick — открой замок (вращение слайдеров)
"""
import random
import time
from dataclasses import dataclass, field
from enum import Enum


class PuzzleType(Enum):
    MEMORY_MATCH = "memory_match"
    COLOR_SEQUENCE = "color_sequence"
    SLIDER = "slider"
    REACTION = "reaction"
    WORD解开 = "word_puzzle"
    LOCKPICK = "lockpick"


class PuzzleDifficulty(Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"


@dataclass
class PuzzleCard:
    id: int
    symbol: str
    is_revealed: bool = False
    is_matched: bool = False


@dataclass
class PuzzleState:
    puzzle_type: PuzzleType
    difficulty: PuzzleDifficulty
    seed: int = 0
    time_limit: int = 30
    moves_allowed: int = 0
    grid: list = field(default_factory=list)
    sequence: list = field(default_factory=list)
    target_word: str = ""
    revealed_pairs: int = 0
    total_pairs: int = 0
    current_step: int = 0
    lock_positions: list = field(default_factory=list)
    lock_targets: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "type": self.puzzle_type.value,
            "difficulty": self.difficulty.value,
            "time_limit": self.time_limit,
            "moves_allowed": self.moves_allowed,
            "grid": self.grid,
            "sequence": self.sequence,
            "target_word": self.target_word,
            "revealed_pairs": self.revealed_pairs,
            "total_pairs": self.total_pairs,
            "current_step": self.current_step,
            "lock_positions": self.lock_positions,
            "lock_targets": self.lock_targets,
        }


PUZZLE_SYMBOLS = ["⚔", "🛡", "🗡", "🏹", "🔮", "💎", "🧪", "📜", "🗝", "💰"]

COLORS = ["#e74c3c", "#3498db", "#2ecc71", "#f1c40f", "#9b59b6", "#e67e22"]

SIMON_COLORS = ["#e74c3c", "#3498db", "#2ecc71", "#f1c40f"]

EASY_WORDS = ["ключ", "меч", "лук", "дым", "огонь", "кость", "щит", "поле", "дуб", "небо"]
MEDIUM_WORDS = ["полынь", "пауза", "ловушка", "кристал", "тариф", "гравий"]
HARD_WORDS = ["алхимик", "кристалл", "подземелье", "скелет", "зельевар", "фехтоваль"]

PUZZLE_TO_TRAP = {
    PuzzleType.MEMORY_MATCH: {
        "name": "Испытание памяти",
        "description": "Древние символы мерцают. Найди пары, прежде чем таймер истечёт.",
        "trap_effect": "Символы сближаются — если ошибиться, пол сдвигается.",
    },
    PuzzleType.COLOR_SEQUENCE: {
        "name": "Хроматическая ловушка",
        "description": "Кристаллы на стенах вспыхивают цветами. Повтори последовательность.",
        "trap_effect": "Неверный порядок активирует магический барьер.",
    },
    PuzzleType.SLIDER: {
        "name": "Механизм Катакомб",
        "description": "Каменные плиты под ногами. Собери рисунок, чтобы открыть проход.",
        "trap_effect": "Неправильное расположение активирует шипы.",
    },
    PuzzleType.REACTION: {
        "name": "Ловкость vs Ловушка",
        "description": "Стрелы вылетают из стен. Ударяй по мишеням пока они видимы!",
        "trap_effect": "Промах — стрела попадает в тебя.",
    },
    PuzzleType.WORD解开: {
        "name": "Загадка Древних",
        "description": "На стене выбиты буквы. Разгадай слово, чтобы разблокировать дверь.",
        "trap_effect": "Неправильная догадка усиливает ядовитый туман.",
    },
    PuzzleType.LOCKPICK: {
        "name": "Взлом Сейфа",
        "description": "Сундук с ловушкой. Поверни слайдеры в правильное положение.",
        "trap_effect": "Лишнее вращение активирует отравляющий газ.",
    },
}


class PuzzleEngine:
    """Генератор и менеджер мини-игр."""

    def create_puzzle(self, puzzle_type: PuzzleType, difficulty: PuzzleDifficulty = PuzzleDifficulty.EASY) -> PuzzleState:
        state = PuzzleState(puzzle_type=puzzle_type, difficulty=difficulty, seed=random.randint(0, 999999))
        random.seed(state.seed)

        if puzzle_type == PuzzleType.MEMORY_MATCH:
            self._init_memory(state)
        elif puzzle_type == PuzzleType.COLOR_SEQUENCE:
            self._init_color_sequence(state)
        elif puzzle_type == PuzzleType.SLIDER:
            self._init_slider(state)
        elif puzzle_type == PuzzleType.REACTION:
            self._init_reaction(state)
        elif puzzle_type == PuzzleType.WORD解开:
            self._init_word_puzzle(state)
        elif puzzle_type == PuzzleType.LOCKPICK:
            self._init_lockpick(state)

        return state

    def _init_memory(self, state: PuzzleState):
        sizes = {PuzzleDifficulty.EASY: 4, PuzzleDifficulty.MEDIUM: 6, PuzzleDifficulty.HARD: 8}
        pairs = sizes[state.difficulty]
        symbols = random.sample(PUZZLE_SYMBOLS, pairs)
        cards = symbols + symbols
        random.shuffle(cards)
        state.grid = [{"id": i, "symbol": s, "revealed": False, "matched": False} for i, s in enumerate(cards)]
        state.total_pairs = pairs
        state.moves_allowed = pairs * 4
        state.time_limit = {PuzzleDifficulty.EASY: 20, PuzzleDifficulty.MEDIUM: 30, PuzzleDifficulty.HARD: 45}[state.difficulty]

    def _init_color_sequence(self, state: PuzzleState):
        lengths = {PuzzleDifficulty.EASY: 3, PuzzleDifficulty.MEDIUM: 5, PuzzleDifficulty.HARD: 7}
        length = lengths[state.difficulty]
        state.sequence = random.choices(range(len(SIMON_COLORS)), k=length)
        state.time_limit = length * 2
        state.moves_allowed = length + 2

    def _init_slider(self, state: PuzzleState):
        state.grid = list(range(1, 16)) + [0]
        for _ in range(50 if state.difficulty == PuzzleDifficulty.EASY else 100 if state.difficulty == PuzzleDifficulty.MEDIUM else 200):
            self._shuffle_slider(state)
        state.time_limit = {PuzzleDifficulty.EASY: 30, PuzzleDifficulty.MEDIUM: 45, PuzzleDifficulty.HARD: 60}[state.difficulty]

    def _shuffle_slider(self, state: PuzzleState):
        idx = state.grid.index(0)
        neighbors = []
        if idx % 4 > 0: neighbors.append(idx - 1)
        if idx % 4 < 3: neighbors.append(idx + 1)
        if idx >= 4: neighbors.append(idx - 4)
        if idx < 12: neighbors.append(idx + 4)
        swap = random.choice(neighbors)
        state.grid[idx], state.grid[swap] = state.grid[swap], state.grid[idx]

    def _init_reaction(self, state: PuzzleState):
        counts = {PuzzleDifficulty.EASY: 5, PuzzleDifficulty.MEDIUM: 8, PuzzleDifficulty.HARD: 12}
        state.moves_allowed = counts[state.difficulty]
        state.time_limit = counts[state.difficulty] * 3

    def _init_word_puzzle(self, state: PuzzleState):
        pool = EASY_WORDS if state.difficulty == PuzzleDifficulty.EASY else MEDIUM_WORDS if state.difficulty == PuzzleDifficulty.MEDIUM else HARD_WORDS
        state.target_word = random.choice(pool)
        hints = max(1, len(state.target_word) - 2 if state.difficulty == PuzzleDifficulty.EASY else len(state.target_word) - 1)
        hint_positions = random.sample(range(len(state.target_word)), hints)
        state.grid = [("_" if i not in hint_positions else state.target_word[i]) for i in range(len(state.target_word))]
        state.moves_allowed = len(state.target_word) + 2
        state.time_limit = len(state.target_word) * 4

    def _init_lockpick(self, state: PuzzleState):
        positions = {PuzzleDifficulty.EASY: 3, PuzzleDifficulty.MEDIUM: 4, PuzzleDifficulty.HARD: 5}
        count = positions[state.difficulty]
        state.lock_positions = [0] * count
        state.lock_targets = [random.randint(1, 10) for _ in range(count)]
        state.moves_allowed = count * 3
        state.time_limit = count * 5

    def check_move(self, state: PuzzleState, action: dict) -> dict:
        """Проверяет ход игрока."""
        ptype = state.puzzle_type
        if ptype == PuzzleType.MEMORY_MATCH:
            return self._check_memory(state, action)
        elif ptype == PuzzleType.COLOR_SEQUENCE:
            return self._check_color(state, action)
        elif ptype == PuzzleType.SLIDER:
            return self._check_slider(state, action)
        elif ptype == PuzzleType.REACTION:
            return self._check_reaction(state, action)
        elif ptype == PuzzleType.WORD解开:
            return self._check_word(state, action)
        elif ptype == PuzzleType.LOCKPICK:
            return self._check_lockpick(state, action)
        return {"success": False, "message": "Неизвестный тип"}

    def _check_memory(self, state: PuzzleState, action: dict) -> dict:
        idx = action.get("index", -1)
        if idx < 0 or idx >= len(state.grid):
            return {"success": False, "message": "Неверный индекс"}
        card = state.grid[idx]
        if card["matched"] or card["revealed"]:
            return {"success": False, "message": "Карта уже открыта"}
        card["revealed"] = True
        revealed = [c for c in state.grid if c["revealed"] and not c["matched"]]
        if len(revealed) == 2:
            state.moves_allowed -= 1
            if revealed[0]["symbol"] == revealed[1]["symbol"]:
                revealed[0]["matched"] = True
                revealed[1]["matched"] = True
                state.revealed_pairs += 1
                if state.revealed_pairs >= state.total_pairs:
                    return {"success": True, "message": "Все пары найдены!", "complete": True}
                return {"success": True, "message": "Пара найдена!", "matched": True}
            else:
                for c in revealed:
                    c["revealed"] = False
                return {"success": False, "message": "Не пара", "matched": False}
        return {"success": None, "message": f"Открыто: {card['symbol']}"}

    def _check_color(self, state: PuzzleState, action: dict) -> dict:
        color_idx = action.get("color", -1)
        expected = state.sequence[state.current_step]
        if color_idx == expected:
            state.current_step += 1
            if state.current_step >= len(state.sequence):
                return {"success": True, "message": "Последовательность верна!", "complete": True}
            return {"success": None, "message": f"Верно! ({state.current_step}/{len(state.sequence)})"}
        state.moves_allowed -= 1
        return {"success": False, "message": "Неверный цвет!"}

    def _check_slider(self, state: PuzzleState, action: dict) -> dict:
        tile = action.get("tile", -1)
        idx = state.grid.index(tile) if tile in state.grid else -1
        zero_idx = state.grid.index(0)
        neighbors = []
        if zero_idx % 4 > 0: neighbors.append(zero_idx - 1)
        if zero_idx % 4 < 3: neighbors.append(zero_idx + 1)
        if zero_idx >= 4: neighbors.append(zero_idx - 4)
        if zero_idx < 12: neighbors.append(zero_idx + 4)
        if idx not in neighbors:
            return {"success": False, "message": "Нельзя сдвинуть"}
        state.grid[idx], state.grid[zero_idx] = state.grid[zero_idx], state.grid[idx]
        state.moves_allowed -= 1
        if state.grid == list(range(1, 16)) + [0]:
            return {"success": True, "message": "Механизм собран!", "complete": True}
        correct = sum(1 for i, v in enumerate(state.grid) if v == i + 1 or v == 0)
        return {"success": None, "message": f"Совпадений: {correct}/15"}

    def _check_reaction(self, state: PuzzleState, action: dict) -> dict:
        hit = action.get("hit", False)
        state.moves_allowed -= 1
        if hit:
            return {"success": None, "message": "Попал!", "score": state.moves_allowed}
        if state.moves_allowed <= 0:
            return {"success": True, "message": "Время вышло!", "complete": True}
        return {"success": False, "message": "Промах!"}

    def _check_word(self, state: PuzzleState, action: dict) -> dict:
        guess = action.get("word", "")
        state.moves_allowed -= 1
        if guess.lower() == state.target_word.lower():
            state.grid = list(state.target_word)
            return {"success": True, "message": f"Верно: {state.target_word}!", "complete": True}
        hints = []
        for i, (g, t) in enumerate(zip(guess.lower(), state.target_word.lower())):
            if g == t:
                hints.append(f"{i+1}:{g}")
            elif g in state.target_word.lower():
                hints.append(f"{i+1}:{g}*")
        return {"success": False, "message": f"Подсказки: {', '.join(hints) if hints else 'Нет совпадений'}"}

    def _check_lockpick(self, state: PuzzleState, action: dict) -> dict:
        pos = action.get("position", -1)
        direction = action.get("direction", 0)
        if pos < 0 or pos >= len(state.lock_positions):
            return {"success": False, "message": "Неверная позиция"}
        state.lock_positions[pos] = (state.lock_positions[pos] + direction) % 11
        state.moves_allowed -= 1
        if state.lock_positions == state.lock_targets:
            return {"success": True, "message": "Замок открыт!", "complete": True}
        close = sum(1 for p, t in zip(state.lock_positions, state.lock_targets) if abs(p - t) <= 1)
        return {"success": None, "message": f"Близко: {close}/{len(state.lock_targets)}"}

    def get_puzzle_info(self, ptype: PuzzleType) -> dict:
        return PUZZLE_TO_TRAP.get(ptype, {})


def get_random_puzzle_for_trap(severity: str = "simple") -> PuzzleType:
    if severity == "simple":
        return random.choice([PuzzleType.MEMORY_MATCH, PuzzleType.REACTION])
    elif severity == "moderate":
        return random.choice([PuzzleType.COLOR_SEQUENCE, PuzzleType.LOCKPICK, PuzzleType.WORD解开])
    else:
        return random.choice([PuzzleType.SLIDER, PuzzleType.LOCKPICK, PuzzleType.WORD解开])

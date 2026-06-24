"""Боевая система по D&D 5e: инициатива, атаки, урон, условия, хитпоинты."""
import random
from dataclasses import dataclass, field
from enum import Enum


class Condition(Enum):
    NORMAL = "normal"
    BLINDED = "blinded"
    Charmed = "charmed"
    DEAFENED = "deafened"
    FRIGHTENED = "frightened"
    GRAPPLED = "grappled"
    INCAPACITATED = "incapacitated"
    INVISIBLE = "invisible"
    PARALYZED = "paralyzed"
    PETRIFIED = "petrified"
    POISONED = "poisoned"
    PRONE = "prone"
    RESTRAINED = "restrained"
    STUNNED = "stunned"
    UNCONSCIOUS = "unconscious"


class DamageType(Enum):
    SLASHING = "slashing"
    PIERCING = "piercing"
    BLUDGEONING = "bludgeoning"
    FIRE = "fire"
    COLD = "cold"
    LIGHTNING = "lightning"
    THUNDER = "thunder"
    POISON = "poison"
    ACID = "acid"
    NECROTIC = "necrotic"
    RADIANT = "radiant"
    PSYCHIC = "psychic"
    FORCE = "force"


def roll_dice(expr: str) -> int:
    """Бросок кубика: '2d6+3', '1d20', 'd4'."""
    expr = expr.strip().lower().replace(" ", "")
    total = 0
    i = 0
    while i < len(expr):
        if expr[i] in "d+-":
            break
        i += 1
    num = int(expr[:i]) if i > 0 else 1
    rest = expr[i:]
    sign = 1
    if rest.startswith("d"):
        dice_expr = rest[1:]
        d_idx = dice_expr.find(("d"))
        plus_idx = dice_expr.find("+")
        minus_idx = dice_expr.find("-")
        split_at = len(dice_expr)
        for idx in [plus_idx, minus_idx]:
            if idx != -1 and idx < split_at:
                split_at = idx
        
        sides_str = dice_expr[:split_at]
        sides = int(sides_str)
        for _ in range(num):
            total += random.randint(1, sides)
        
        remaining = dice_expr[split_at:]
        if remaining.startswith("+"):
            total += int(remaining[1:])
        elif remaining.startswith("-"):
            total -= int(remaining[1:])
    elif rest.startswith("+"):
        total = num + int(rest[1:])
    elif rest.startswith("-"):
        total = num - int(rest[1:])
    else:
        total = num
    
    return max(0, total)


def d20() -> int:
    return random.randint(1, 20)


def ability_mod(score: int) -> int:
    return (score - 10) // 2


def proficiency_bonus(level: int) -> int:
    return 2 + (level - 1) // 4


@dataclass
class StatBlock:
    name: str = "Существо"
    hp: int = 10
    max_hp: int = 10
    ac: int = 10
    speed: int = 30
    level: int = 1
    
    strength: int = 10
    dexterity: int = 10
    constitution: int = 10
    intelligence: int = 10
    wisdom: int = 10
    charisma: int = 10
    
    condition: Condition = Condition.NORMAL
    is_alive_flag: bool = True
    
    attacks: list = field(default_factory=list)
    abilities: list = field(default_factory=list)
    
    def get_mod(self, attr: str) -> int:
        scores = {
            "str": self.strength, "dex": self.dexterity,
            "con": self.constitution, "int": self.intelligence,
            "wis": self.wisdom, "cha": self.charisma,
        }
        return ability_mod(scores.get(attr, 10))
    
    def get_initiative(self) -> int:
        return d20() + self.get_mod("dex")
    
    def get_attack_bonus(self) -> int:
        prof = proficiency_bonus(self.level)
        return self.get_mod("str") + prof
    
    def get_ranged_attack_bonus(self) -> int:
        prof = proficiency_bonus(self.level)
        return self.get_mod("dex") + prof
    
    def take_damage(self, amount: int) -> int:
        actual = min(amount, self.hp)
        self.hp -= actual
        if self.hp <= 0:
            self.hp = 0
            self.condition = Condition.UNCONSCIOUS
            self.is_alive_flag = False
        return actual
    
    def heal(self, amount: int) -> int:
        actual = min(amount, self.max_hp - self.hp)
        self.hp += actual
        if self.hp > 0 and self.condition == Condition.UNCONSCIOUS:
            self.condition = Condition.NORMAL
            self.is_alive_flag = True
        return actual
    
    def is_conscious(self) -> bool:
        return self.hp > 0 and self.condition not in (
            Condition.UNCONSCIOUS, Condition.PARALYZED,
            Condition.PETRIFIED, Condition.INCAPACITATED, Condition.STUNNED
        )

    def respawn(self, heal_percent: float = 0.5):
        """GTA-стиль: респавн у лекаря с частичным исцелением."""
        self.hp = int(self.max_hp * heal_percent)
        self.condition = Condition.NORMAL
        self.is_alive_flag = True


@dataclass
class Attack:
    name: str = "Атака"
    damage_dice: str = "1d6"
    damage_type: DamageType = DamageType.SLASHING
    bonus: int = 0
    range: int = 5
    is_ranged: bool = False
    extra_damage_dice: str = ""
    extra_damage_type: DamageType = DamageType.FORCE
    
    def roll_damage(self) -> dict:
        dmg = roll_dice(self.damage_dice) + self.bonus
        extra = roll_dice(self.extra_damage_dice) if self.extra_damage_dice else 0
        return {
            "damage": dmg,
            "extra_damage": extra,
            "damage_type": self.damage_type.value,
            "extra_type": self.extra_damage_type.value if extra > 0 else None,
            "total": dmg + extra,
        }


@dataclass
class Combatant:
    stat_block: StatBlock
    initiative: int = 0
    is_player: bool = False
    position: tuple = (0, 0)
    team: int = 0
    
    def __post_init__(self):
        if self.initiative == 0:
            self.initiative = self.stat_block.get_initiative()
    
    @property
    def name(self):
        return self.stat_block.name
    
    @property
    def hp(self):
        return self.stat_block.hp
    
    @property
    def ac(self):
        return self.stat_block.ac
    
    def is_alive(self):
        return self.stat_block.hp > 0 and self.stat_block.is_alive_flag
    
    def is_conscious(self):
        return self.stat_block.is_conscious()


@dataclass
class AttackResult:
    attacker: str
    defender: str
    attack_roll: int
    attack_bonus: int
    total_attack: int
    is_critical: bool
    is_hit: bool
    damage: int
    damage_type: str
    extra_damage: int = 0
    extra_type: str = ""
    message: str = ""


class CombatEngine:
    def __init__(self):
        self.combatants: list[Combatant] = []
        self.current_turn: int = 0
        self.round: int = 0
        self.log: list[dict] = []
        self.is_active: bool = False
        self.winner_team: int | None = None
    
    def add_combatant(self, stat_block: StatBlock, is_player: bool = False, team: int = 0, position: tuple = (0, 0)):
        c = Combatant(stat_block=stat_block, is_player=is_player, team=team, position=position)
        self.combatants.append(c)
        return c
    
    def start(self):
        self.combatants.sort(key=lambda c: c.initiative, reverse=True)
        self.current_turn = 0
        self.round = 1
        self.is_active = True
        self.log = []
        self._log("system", f"=== Бой начинается! Раунд {self.round} ===")
        self._log("system", f"Порядок: {', '.join(f'{c.name}({c.initiative})' for c in self.combatants)}")
    
    def get_current(self) -> Combatant | None:
        if not self.is_active:
            return None
        for i in range(len(self.combatants)):
            idx = (self.current_turn + i) % len(self.combatants)
            c = self.combatants[idx]
            if c.is_alive():
                return c
        return None
    
    def next_turn(self):
        alive = [c for c in self.combatants if c.is_alive()]
        if len(alive) <= 1:
            self.is_active = False
            if alive:
                self.winner_team = alive[0].team
                self._log("system", f"Победа команды {self.winner_team}!")
            return
        
        self.current_turn += 1
        if self.current_turn >= len(self.combatants):
            self.current_turn = 0
            self.round += 1
            self._log("system", f"=== Раунд {self.round} ===")
    
    def attack(self, attacker: Combatant, defender: Combatant, attack_idx: int = 0) -> AttackResult:
        atk = attacker.stat_block.attacks[attack_idx] if attack_idx < len(attacker.stat_block.attacks) else Attack()
        
        is_ranged = atk.is_ranged
        attack_roll = d20()
        attack_bonus = attacker.stat_block.get_ranged_attack_bonus() if is_ranged else attacker.stat_block.get_attack_bonus()
        total_attack = attack_roll + attack_bonus
        is_critical = attack_roll == 20
        is_hit = is_critical or total_attack >= defender.ac
        
        result = AttackResult(
            attacker=attacker.name, defender=defender.name,
            attack_roll=attack_roll, attack_bonus=attack_bonus,
            total_attack=total_attack, is_critical=is_critical,
            is_hit=is_hit, damage=0, damage_type=atk.damage_type.value,
        )
        
        if is_hit:
            dmg_info = atk.roll_damage()
            damage = dmg_info["total"]
            if is_critical:
                crit_dmg = roll_dice(atk.damage_dice)
                damage += crit_dmg
                result.extra_damage += crit_dmg
                result.extra_type = "critical"
            
            actual = defender.stat_block.take_damage(damage)
            result.damage = actual
            result.message = f"{attacker.name} попадает! {damage} урона."
            
            if not defender.is_alive():
                result.message += f" {defender.name} повержен!"
            elif defender.hp <= defender.stat_block.max_hp // 4:
                result.message += f" {defender.name} сильно ранен!"
        else:
            result.message = f"{attacker.name} промахивается!"
        
        self._log("attack", result.__dict__)
        return result
    
    def get_state(self) -> dict:
        return {
            "round": self.round,
            "is_active": self.is_active,
            "winner_team": self.winner_team,
            "current_turn": self.current_turn,
            "combatants": [{
                "name": c.name,
                "hp": c.hp,
                "max_hp": c.stat_block.max_hp,
                "ac": c.ac,
                "initiative": c.initiative,
                "is_player": c.is_player,
                "team": c.team,
                "is_alive": c.is_alive(),
                "condition": c.stat_block.condition.value,
            } for c in self.combatants],
            "log": self.log[-20:],
        }
    
    def enemy_turn(self) -> list[AttackResult]:
        """ИИ врага: атакует ближайшего живого игрока."""
        results = []
        current = self.get_current()
        if not current or current.is_player:
            return results
        
        players = [c for c in self.combatants if c.is_player and c.is_alive()]
        if not players:
            return results
        
        target = min(players, key=lambda p: p.hp)
        
        hp_ratio = current.hp / current.stat_block.max_hp if current.stat_block.max_hp > 0 else 1
        if hp_ratio < 0.3 and len(current.stat_block.attacks) > 1:
            attack_idx = 1
        else:
            attack_idx = 0
        
        result = self.attack(current, target, attack_idx)
        results.append(result)
        
        return results
    
    def run_enemy_turns(self) -> list[AttackResult]:
        """Запускает все ходы врагов до хода игрока."""
        all_results = []
        while True:
            current = self.get_current()
            if not current or current.is_player or not self.is_active:
                break
            results = self.enemy_turn()
            all_results.extend(results)
            self.next_turn()
        return all_results
    
    def _log(self, log_type: str, data):
        if isinstance(data, str):
            self.log.append({"type": log_type, "message": data})
        else:
            self.log.append({"type": log_type, **data})

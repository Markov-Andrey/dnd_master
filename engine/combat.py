"""
Skill-based combat (no to-hit dice roll).
Damage output and defense are derived from character skill + attributes.
Player wins or loses based on strategic decisions each round.
"""
import random
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from entities.character import Character


COMBAT_ACTIONS = ["attack", "power_attack", "block", "dodge", "use_item", "flee"]
STATUS_DURATIONS = {"bleeding": 3, "poisoned": 5, "stunned": 1}


class CombatResult:
    def __init__(self):
        self.log: list[str] = []
        self.player_won: bool = False
        self.fled: bool = False
        self.enemy_dead: bool = False
        self.player_dead: bool = False
        self.loot: list = []
        self.xp_gained: int = 0
        self.gold_gained: int = 0


class Combat:
    def __init__(self, player: "Character", enemy: "Character"):
        self.player = player
        self.enemy = enemy
        self.round = 0
        self.player_stance: str = "neutral"   # neutral | blocking | dodging
        self.enemy_stance: str = "neutral"
        self.log: list[str] = []

    # ---- damage formula ----
    # No dice on whether attack connects; all hits land.
    # Damage is deterministic (skill + strength) minus target mitigation.
    # Player choice of action is the primary lever, not RNG.

    def _base_damage(self, attacker: "Character") -> int:
        weapon = attacker.equipped.get("weapon") or {}
        dmg_min = weapon.get("damage_min", 2)
        dmg_max = weapon.get("damage_max", 6)
        skill_name = weapon.get("weapon_skill", "blade")
        skill = attacker.skills.get(skill_name, 10)
        str_bonus = (attacker.attributes["strength"] - 50) // 5
        # small variance (±20% of base) to avoid pure determinism
        base = (dmg_min + dmg_max) // 2
        variance = max(1, base // 5)
        return max(1, base + str_bonus + skill // 10 + random.randint(-variance, variance))

    def _mitigation(self, defender: "Character", stance: str) -> int:
        armor = defender.equipped.get("armor") or {}
        armor_def = armor.get("defense", 0)
        skill_agi = defender.attributes["agility"] // 10
        if stance == "blocking":
            block_skill = defender.skills.get("block", 10)
            return armor_def + skill_agi + block_skill // 5 + 5
        if stance == "dodging":
            speed = defender.attributes["speed"] // 10
            return armor_def + skill_agi + speed + 3
        return armor_def + skill_agi

    def _deal_damage(self, attacker: "Character", defender: "Character",
                     defender_stance: str, multiplier: float = 1.0) -> tuple[int, str]:
        raw = int(self._base_damage(attacker) * multiplier)
        reduction = self._mitigation(defender, defender_stance)
        actual = max(1, raw - reduction)
        defender.take_damage(actual)
        weapon = attacker.equipped.get("weapon") or {}
        skill_name = weapon.get("weapon_skill", "blade")
        attacker.gain_skill_xp(skill_name)
        detail = f"({raw} - {reduction} armor = {actual})"
        return actual, detail

    # ---- player actions ----

    def action_attack(self) -> list[str]:
        self.player_stance = "neutral"
        dmg, detail = self._deal_damage(self.player, self.enemy, self.enemy_stance)
        return [f"You attack {self.enemy.name} for {dmg} damage. {detail}"]

    def action_power_attack(self) -> list[str]:
        """High damage but costs more stamina and leaves player open."""
        stamina_cost = 20
        if self.player.stamina < stamina_cost:
            return ["Not enough stamina for a power attack!"]
        self.player.stamina -= stamina_cost
        self.player_stance = "neutral"
        dmg, detail = self._deal_damage(self.player, self.enemy, self.enemy_stance,
                                        multiplier=2.0)
        msgs = [f"POWER ATTACK! You hit {self.enemy.name} for {dmg} damage. {detail}"]
        # power attack leaves player open — next enemy attack ignores stance
        self._player_open = True
        return msgs

    def action_block(self) -> list[str]:
        self.player_stance = "blocking"
        block_skill = self.player.skills.get("block", 10)
        return [f"You raise your guard. (Block skill: {block_skill})"]

    def action_dodge(self) -> list[str]:
        self.player_stance = "dodging"
        speed = self.player.attributes["speed"]
        return [f"You prepare to dodge. (Speed: {speed})"]

    def action_flee(self) -> tuple[bool, list[str]]:
        speed_ratio = self.player.attributes["speed"] / max(1, self.enemy.attributes["speed"])
        # flee chance: pure speed comparison, no dice
        success = speed_ratio >= 1.0 or (speed_ratio > 0.7 and random.random() < 0.5)
        if success:
            return True, ["You successfully flee from combat!"]
        return False, ["You can't escape — the enemy is too fast!"]

    def action_use_item(self, item: dict) -> list[str]:
        msgs = []
        if item.get("hp_restore"):
            self.player.heal(item["hp_restore"])
            msgs.append(f"You use {item['name']} and restore {item['hp_restore']} HP.")
        if item.get("stamina_restore"):
            self.player.stamina = min(
                self.player.stamina_max,
                self.player.stamina + item["stamina_restore"]
            )
            msgs.append(f"You use {item['name']} and restore {item['stamina_restore']} stamina.")
        return msgs or [f"You use {item['name']} — nothing happens."]

    # ---- enemy AI ----

    def _enemy_ai_action(self) -> str:
        """Simple enemy AI: power attack when player is blocking, else attack."""
        if self.player_stance == "blocking" and self.enemy.stamina > 25:
            return "power_attack"
        if self.player.hp < self.player.hp_max * 0.3:
            return "attack"
        return "attack"

    def _enemy_turn(self) -> list[str]:
        if "stunned" in self.enemy.statuses:
            self.enemy.statuses.remove("stunned")
            return [f"{self.enemy.name} is stunned and loses their turn."]

        action = self._enemy_ai_action()
        msgs = []
        open_penalty = getattr(self, "_player_open", False)
        p_stance = "neutral" if open_penalty else self.player_stance
        self._player_open = False

        if action == "power_attack" and self.enemy.stamina >= 20:
            self.enemy.stamina -= 20
            dmg, detail = self._deal_damage(self.enemy, self.player, p_stance, multiplier=2.0)
            msgs.append(f"{self.enemy.name} unleashes a POWER ATTACK for {dmg} damage! {detail}")
        else:
            dmg, detail = self._deal_damage(self.enemy, self.player, p_stance)
            msgs.append(f"{self.enemy.name} attacks you for {dmg} damage. {detail}")

        return msgs

    # ---- status effects ----

    def _process_statuses(self, character: "Character") -> list[str]:
        msgs = []
        for status in list(character.statuses):
            if status == "bleeding":
                character.take_damage(2)
                msgs.append(f"{character.name} bleeds for 2 damage.")
            elif status == "poisoned":
                character.take_damage(3)
                msgs.append(f"{character.name} takes 3 poison damage.")
        return msgs

    # ---- main round resolver ----

    def resolve_round(self, action: str, item: dict = None) -> CombatResult:
        result = CombatResult()
        self.round += 1
        msgs: list[str] = []

        # reset stance each round
        self.player_stance = "neutral"

        if action == "attack":
            msgs += self.action_attack()
        elif action == "power_attack":
            msgs += self.action_power_attack()
        elif action == "block":
            msgs += self.action_block()
        elif action == "dodge":
            msgs += self.action_dodge()
        elif action == "flee":
            success, flee_msgs = self.action_flee()
            msgs += flee_msgs
            if success:
                result.fled = True
                result.log = msgs
                return result
        elif action == "use_item" and item:
            msgs += self.action_use_item(item)

        # stamina regeneration each round
        self.player.stamina = min(self.player.stamina_max, self.player.stamina + 5)
        self.enemy.stamina = min(self.enemy.stamina_max, self.enemy.stamina + 5)

        msgs += self._process_statuses(self.player)

        if not self.enemy.is_alive:
            result.enemy_dead = True
            result.player_won = True
            msgs.append(f"{self.enemy.name} is defeated!")
            if hasattr(self.enemy, "drop_loot"):
                result.loot = self.enemy.drop_loot()
                result.gold_gained = random.randint(1, self.enemy.level * 10)
            result.xp_gained = max(1, self.enemy.level * 5)
            result.log = msgs
            return result

        msgs += self._enemy_turn()
        msgs += self._process_statuses(self.enemy)

        if not self.player.is_alive:
            result.player_dead = True
            msgs.append("You have fallen in combat...")

        result.log = msgs
        return result

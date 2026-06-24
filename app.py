"""Flask-приложение: RPG с диалогами NPC и миром."""
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import os, json, random, time

from npc.npc import NPC
from dialogue.rag_memory import RAGMemory
from core.config import NPC_DATA_DIR, MAX_HISTORY
from core.combat import CombatEngine, StatBlock, Attack, DamageType
from core.monsters import spawn_monster, roll_loot as monster_roll_loot, get_encounter
from core.traps import spawn_trap, check_trap_detection, check_trap_disarm
from core.trading import get_shop, ShopItem
from core.rest import short_rest, long_rest, can_rest
from core.loot import generate_chest_loot
from core.quests import QuestManager
from core.gametime import GameTime
from core.save_manager import SaveManager
from core.llm_generator import generate_npc, generate_location, generate_encounter, generate_trap
from core.storyteller import Storyteller
from core.director_ai import AIDirector, EventType
from player.player import Player, SKILL_NAMES, SKILL_ATTR
from world.world_map import WorldMap
from world.renderer import render_ascii, render_legend, render_minimap, render_global_svg, render_local_svg
import npc.director as director

app = Flask(__name__, static_folder="static")
CORS(app)

npcs: dict[str, NPC] = {}
rag = RAGMemory()
player = Player.load()
world = WorldMap()
combat: CombatEngine | None = None
active_trap = None
active_shop = None
current_subarea: str | None = None
quest_manager = QuestManager()
quest_manager.load_templates()
game_time = GameTime()
save_manager = SaveManager()
storyteller = Storyteller()
storyteller.load()
director_ai = AIDirector()


def _director_update_on_move(loc_id: str):
    """Обновляет метрики директора при перемещении."""
    visited = len(set(l.id for l in world.locations.values() if getattr(l, 'visited', False)))
    director_ai.update_metrics(
        locations_visited=visited,
        time_played_minutes=int((time.time() - director_ai.minute_start) / 60),
    )


def _director_update_on_combat(kills: int = 0, deaths: int = 0):
    """Обновляет метрики директора после боя."""
    director_ai.update_metrics(
        total_kills=director_ai.metrics.total_kills + kills,
        total_deaths=director_ai.metrics.total_deaths + deaths,
        recent_combats=director_ai.metrics.recent_combats + 1,
        recent_losses=director_ai.metrics.recent_losses + deaths,
        hp_percent=player.hp / max(1, player.max_hp),
    )


def _director_update_on_rest():
    """Обновляет метрики директора после отдыха."""
    director_ai.update_metrics(
        recent_combats=0,
        recent_losses=0,
        hp_percent=player.hp / max(1, player.max_hp),
    )


def _npc_or_404(nid):
    npc = npcs.get(nid)
    return (npc, None) if npc else (None, (jsonify({"error": "NPC not found"}), 404))


# ─── Статика ───────────────────────────────────────────────────────────────

@app.route("/")
def index(): return send_from_directory("static", "index.html")

@app.route("/static/<path:p>")
def static_files(p): return send_from_directory("static", p)


# ─── Мир ──────────────────────────────────────────────────────────────────

def _get_completed_encounters(loc_id: str) -> set:
    data = _load_encounters()
    return {k.split(":", 1)[1] for k, v in data.get("completed", {}).items()
            if k.startswith(loc_id + ":") and v}


@app.route("/api/world")
def get_world():
    loc = world.get_current()
    completed = _get_completed_encounters(loc.id) if loc else set()
    return jsonify({
        "current_location": loc.to_dict() if loc else None,
        "minimap": render_minimap(world),
        "ascii_map": render_ascii(world),
        "svg_global": render_global_svg(world),
        "svg_local": render_local_svg(loc, completed_encounters=completed, current_subarea=current_subarea) if loc else "",
    })

@app.route("/api/world/move", methods=["POST"])
def move_player():
    d = request.get_json(force=True)
    direction = d.get("direction", "").lower()
    
    loc = world.move(direction)
    if not loc:
        return jsonify({"error": "Нельзя"}), 400
    
    player.location_id = loc.id
    _director_update_on_move(loc.id)
    
    director_events = director_ai.evaluate()
    
    for de in director_events:
        if de.event_type == EventType.DIFFICULTY_UP:
            director_ai.config.difficulty_scale = de.data.get("new_scale", 1.0)
        elif de.event_type == EventType.DIFFICULTY_DOWN:
            director_ai.config.difficulty_scale = de.data.get("new_scale", 1.0)
    
    completed = _get_completed_encounters(loc.id)
    return jsonify({
        "location": loc.to_dict(),
        "minimap": render_minimap(world),
        "ascii_map": render_ascii(world),
        "svg_global": render_global_svg(world),
        "svg_local": render_local_svg(loc, completed_encounters=completed, current_subarea=current_subarea),
        "legend": render_legend(world),
        "director_events": [{"type": e.event_type.value, "title": e.title,
                              "description": e.description} for e in director_events if e.priority >= 3],
    })

@app.route("/api/world/svg")
def get_svg_map():
    mode = request.args.get("mode", "global")
    loc = world.get_current()
    if mode == "local" and loc:
        return render_local_svg(loc, current_subarea=current_subarea), 200, {"Content-Type": "image/svg+xml"}
    return render_global_svg(world), 200, {"Content-Type": "image/svg+xml"}


@app.route("/api/world/subarea", methods=["POST"])
def set_subarea():
    global current_subarea
    d = request.get_json(force=True)
    current_subarea = d.get("subarea_id")
    loc = world.get_current()
    completed = _get_completed_encounters(loc.id) if loc else set()
    return jsonify({
        "svg_local": render_local_svg(loc, completed_encounters=completed, current_subarea=current_subarea),
    })

@app.route("/api/world/locations")
def list_locations():
    return jsonify([l.to_dict() for l in world.locations.values()])


# ─── NPC CRUD ──────────────────────────────────────────────────────────────

@app.route("/api/npcs")
def list_npcs(): return jsonify([n.to_dict() for n in npcs.values()])

@app.route("/api/npc/new", methods=["POST"])
def create_npc():
    d = request.get_json(force=True)
    npc = NPC.from_config(d["config_path"]) if d.get("config_path") else NPC(
        name=d.get("name"), personality=d.get("personality", ""),
        background=d.get("background", ""), lore=d.get("lore", ""),
        quest_hooks=d.get("quest_hooks", []),
    )
    npcs[npc.id] = npc
    npc.save()
    return jsonify(npc.to_dict())


# ─── Диалог ────────────────────────────────────────────────────────────────

@app.route("/api/npc/<nid>/start", methods=["POST"])
def start_dialogue(nid):
    npc, err = _npc_or_404(nid)
    if err: return err
    npc.start_dialogue()
    summary = npc.current_summary if npc.current_summary else ""
    prompt = director.build_system_prompt(npc, rag.query(nid, "встреча с игроком"), summary, all_npcs=npcs)
    greeting = __import__("core.llm_client", fromlist=["chat"]).chat(prompt, [{"role": "user", "content": "(начало диалога)"}])
    npc.add_message("assistant", greeting)
    npc.save()
    return jsonify({"npc_response": greeting, "state": npc.to_dict()})

@app.route("/api/npc/<nid>/say", methods=["POST"])
def say(nid):
    npc, err = _npc_or_404(nid)
    if err: return err
    d = request.get_json(force=True)
    msg = d.get("message", "")
    item_id = d.get("item_id")

    npc.add_message("user", msg)
    npc.msg_count += 1

    director.update_name(npc, msg)
    director.update_relationships(npc, msg)
    director.update_emotion(npc, msg)
    director.update_memory(npc, msg)

    history = npc.dialogue_history[-MAX_HISTORY:]
    mems = rag.query(nid, msg)
    summary = npc.current_summary if npc.current_summary else ""

    prompt = director.build_system_prompt(npc, mems, summary, all_npcs=npcs)
    reply = None

    skill_check = None
    if not item_id:
        from core import llm_client
        reply = llm_client.chat(prompt, history)
        skill_check = director.try_skill_check(npc, msg, prompt, history)
        if skill_check: reply = skill_check["reply"]

    item_result = None
    if item_id:
        item_result = director.try_give_item(npc, msg, item_id, prompt, history, player.inventory)
        if item_result:
            player.save()
            reply = item_result["reply"]

    if not reply:
        from core import llm_client
        reply = llm_client.chat(prompt, history)

    npc.add_message("assistant", reply)
    npc.save()

    summaries = director.maybe_summarize(npc, nid, rag)

    return jsonify({
        "npc_response": reply, "state": npc.to_dict(),
        "block_summaries": summaries, "skill_check": skill_check and skill_check.get("check"),
        "item_result": item_result,
    })

@app.route("/api/npc/<nid>/end", methods=["POST"])
def end_dialogue(nid):
    npc, err = _npc_or_404(nid)
    if err: return err
    from npc.summarizer import summarize_final
    all_sums = [s["document"] for s in rag.get_all(nid)]
    final = summarize_final(npc.dialogue_history, all_sums)
    rag.store(nid, final["summary"], final.get("facts"), {"npc_id": nid, "type": "final"})
    npc.current_summary = final["summary"]
    npc.dialogue_history = []
    npc.end_dialogue()
    npc.save()
    return jsonify({"summary": final, "state": npc.to_dict()})


# ─── Бой ───────────────────────────────────────────────────────────────────

@app.route("/api/combat/start", methods=["POST"])
def start_combat():
    global combat, active_trap
    loc = world.get_current()
    if not loc:
        return jsonify({"error": "Нет локации"}), 400
    
    encounter_ids = get_encounter(loc.id)
    if not encounter_ids:
        return jsonify({"message": "Врагов нет. Можно спокойно исследовать."})
    
    combat = CombatEngine()
    
    player_sb = StatBlock(
        name=player.name,
        hp=player.hp,
        max_hp=player.max_hp,
        ac=player.get_ac(),
        level=player.level,
        strength=player.attributes.get("str", 10),
        dexterity=player.attributes.get("dex", 10),
        constitution=player.attributes.get("con", 10),
        intelligence=player.attributes.get("int", 10),
        wisdom=player.attributes.get("wis", 10),
        charisma=player.attributes.get("cha", 10),
    )
    
    weapon = None
    if hasattr(player, 'inventory') and player.inventory.equipment.get("weapon"):
        weapon = player.inventory.equipment["weapon"]
    if weapon:
        dmg = weapon.properties.get("damage", "1d6")
        player_sb.attacks.append(Attack(
            name=weapon.name, damage_dice=dmg,
            damage_type=DamageType.SLASHING,
        ))
    else:
        player_sb.attacks.append(Attack(
            name="Кулаки", damage_dice="1",
            damage_type=DamageType.BLUDGEONING,
        ))
    
    combat.add_combatant(player_sb, is_player=True, team=0)
    
    for eid in encounter_ids:
        msb = spawn_monster(eid)
        combat.add_combatant(msb, is_player=False, team=1)
    
    combat.start()
    
    active_trap = spawn_trap(loc.id)
    
    return jsonify({
        "message": f"Бой 시작ается! Враги: {', '.join(eid for eid in encounter_ids)}",
        "state": combat.get_state(),
    })


@app.route("/api/combat/attack", methods=["POST"])
def combat_attack():
    global combat
    if not combat or not combat.is_active:
        return jsonify({"error": "Бой не активен"}), 400
    
    d = request.get_json(force=True)
    target_idx = d.get("target", 0)
    attack_idx = d.get("attack", 0)
    
    current = combat.get_current()
    if not current or not current.is_player:
        return jsonify({"error": "Не ваш ход"}), 400
    
    alive_enemies = [c for c in combat.combatants if c.is_alive() and c.team == 1]
    if not alive_enemies:
        return jsonify({"error": "Нет врагов"}), 400
    
    target_idx = min(target_idx, len(alive_enemies) - 1)
    target = alive_enemies[target_idx]
    
    result = combat.attack(current, target, attack_idx)
    
    loot = []
    if not target.is_alive():
        template_id = target.name.lower().replace(" ", "_")
        loot = monster_roll_loot(template_id)
        for item in loot:
            if item.get("type") == "gold":
                player.gold = getattr(player, 'gold', 0) + item.get("amount", 0)
            elif item.get("type") == "item":
                from player.inventory import Item as InvItem
                new_item = InvItem(
                    name=item.get("name", "?"),
                    icon=item.get("icon", "?"),
                    item_type=item.get("item_type", "misc"),
                    properties=item.get("properties", {}),
                )
                player.inventory.add_item(new_item)
    
    combat.next_turn()
    
    enemy_results = combat.run_enemy_turns()
    
    player.hp = combat.combatants[0].stat_block.hp if combat.combatants else player.hp
    
    return jsonify({
        "result": result.__dict__,
        "enemy_results": [r.__dict__ for r in enemy_results],
        "loot": loot,
        "state": combat.get_state(),
    })


@app.route("/api/combat/defend", methods=["POST"])
def combat_defend():
    global combat
    if not combat or not combat.is_active:
        return jsonify({"error": "Бой не активен"}), 400
    
    current = combat.get_current()
    if not current or not current.is_player:
        return jsonify({"error": "Не ваш ход"}), 400
    
    current.stat_block.ac += 2
    combat._log("system", f"{current.name} принимает защитную стойку. AC +2 до следующего хода.")
    combat.next_turn()
    
    return jsonify({
        "message": "Защитная стойка. AC +2 до следующего хода.",
        "state": combat.get_state(),
    })


@app.route("/api/combat/flee", methods=["POST"])
def combat_flee():
    global combat
    if not combat or not combat.is_active:
        return jsonify({"error": "Бой не активен"}), 400
    
    import random
    roll = random.randint(1, 20)
    dex_mod = player.get_modifier("dex")
    success = roll + dex_mod >= 10
    
    if success:
        combat.is_active = False
        combat._log("system", f"Побег удался! ({roll}+{dex_mod} >= 10)")
        return jsonify({"message": "Вы сбежали!", "state": combat.get_state()})
    else:
        combat._log("system", f"Побег не удался! ({roll}+{dex_mod} < 10)")
        combat.next_turn()
        return jsonify({"message": "Побег не удался!", "state": combat.get_state()})


@app.route("/api/combat/use_potion", methods=["POST"])
def combat_use_potion():
    global combat
    if not combat or not combat.is_active:
        return jsonify({"error": "Бой не активен"}), 400
    
    current = combat.get_current()
    if not current or not current.is_player:
        return jsonify({"error": "Не ваш ход"}), 400
    
    healing = 0
    for i, item in enumerate(player.inventory.backpack):
        if item and item.item_type == "potion" and "healing" in item.properties:
            dice = item.properties["healing"]
            from core.combat import roll_dice
            healing = roll_dice(dice)
            player.inventory.backpack[i] = None
            break
    
    if healing > 0:
        current.stat_block.heal(healing)
        combat._log("system", f"{current.name} выпивает зелье. +{healing} HP.")
        combat.next_turn()
        return jsonify({"message": f"+{healing} HP", "state": combat.get_state()})
    else:
        return jsonify({"error": "Нет зелий лечения"}), 400


@app.route("/api/combat/state")
def combat_state():
    if not combat:
        return jsonify({"active": False})
    return jsonify({"active": combat.is_active, **combat.get_state()})


@app.route("/api/combat/end", methods=["POST"])
def end_combat():
    global combat
    
    kills = 0
    deaths = 0
    xp_total = 0
    if combat:
        for c in combat.combatants:
            if not c.is_player and not c.is_alive():
                kills += 1
                monster_xp = {
                    "goblin": 50, "skeleton": 50, "wolf": 50, "zombie": 50,
                    "spider": 10, "rat": 10, "bandit": 50, "orc": 100,
                    "troll": 700, "skeleton_mage": 100,
                }.get(c.name.lower(), 50)
                xp_total += monster_xp
            elif c.is_player and not c.is_alive():
                deaths += 1
        
        if xp_total > 0:
            result = player.gain_xp(xp_total)
            player.hp = combat.combatants[0].stat_block.hp if combat.combatants else player.hp
    
    _director_update_on_combat(kills=kills, deaths=deaths)
    director_events = director_ai.evaluate()
    
    combat = None
    return jsonify({
        "message": "Бой завершён.",
        "xp_gained": xp_total,
        "level": player.level,
        "leveled_up": xp_total > 0 and player.xp >= player.to_dict().get("xp_to_next", 999999),
        "director_events": [{"type": e.event_type.value, "title": e.title,
                              "description": e.description} for e in director_events if e.priority >= 3],
    })


# ─── Ловушки ───────────────────────────────────────────────────────────────

@app.route("/api/trap/detect", methods=["POST"])
def detect_trap():
    global active_trap
    if not active_trap:
        return jsonify({"detected": False, "message": "Нет ловушек рядом."})
    
    roll = player.get_modifier("wis") + player.get_skill_modifier("perception") if hasattr(player, 'get_skill_modifier') else 10
    import random
    roll += random.randint(1, 20)
    result = check_trap_detection(roll, active_trap)
    return jsonify(result)


@app.route("/api/trap/disarm", methods=["POST"])
def disarm_trap():
    global active_trap
    if not active_trap:
        return jsonify({"disarmed": False, "message": "Нет ловушки."})
    
    import random
    roll = random.randint(1, 20)
    dex_mod = player.get_modifier("dex")
    total = roll + dex_mod
    result = check_trap_disarm(total, active_trap)
    if result["disarmed"]:
        active_trap = None
    return jsonify(result)


@app.route("/api/trap/trigger", methods=["POST"])
def trigger_trap():
    global active_trap
    if not active_trap:
        return jsonify({"triggered": False})
    
    result = active_trap.trigger()
    if hasattr(player, 'hp'):
        player.hp = max(0, player.hp - result.get("damage", 0))
    active_trap = None
    return jsonify(result)


# ─── Торговля ──────────────────────────────────────────────────────────────

@app.route("/api/shop/<shop_type>")
def get_shop_inventory(shop_type):
    shop = get_shop(shop_type)
    if not shop:
        return jsonify({"error": "Магазин не найден"}), 404
    return jsonify(shop.to_dict())


@app.route("/api/shop/buy", methods=["POST"])
def shop_buy():
    global active_shop
    d = request.get_json(force=True)
    shop_type = d.get("shop_type", "general")
    item_id = d.get("item_id")
    
    shop = get_shop(shop_type)
    if not shop:
        return jsonify({"error": "Магазин не найден"}), 404
    
    item = next((i for i in shop.inventory if i.item_id == item_id), None)
    if not item:
        return jsonify({"error": "Предмет не найден"}), 404
    
    player_gold = getattr(player, 'gold', 0)
    success, new_gold, msg = shop.buy_item(player_gold, item)
    
    if success:
        player.gold = new_gold
        from player.inventory import Item as InvItem
        new_item = InvItem(
            name=item.name, icon=item.icon,
            item_type=item.item_type,
            properties=item.properties,
            description=item.description,
        )
        player.inventory.add_item(new_item)
        player.save()
    
    return jsonify({"success": success, "message": msg, "gold": player.gold})


@app.route("/api/shop/sell", methods=["POST"])
def shop_sell():
    d = request.get_json(force=True)
    shop_type = d.get("shop_type", "general")
    item_id = d.get("item_id")
    
    shop = get_shop(shop_type)
    if not shop:
        return jsonify({"error": "Магазин не найден"}), 404
    
    loc, idx, item = player.inventory.find_item(item_id)
    if not item:
        return jsonify({"error": "Предмет не найден"}), 404
    
    player_gold = getattr(player, 'gold', 0)
    shop_item = ShopItem(item_id=item.id, name=item.name, icon=item.icon,
                         item_type=item.item_type, sell_price=10)
    success, new_gold, msg = shop.sell_item(player_gold, shop_item)
    
    if success:
        player.gold = new_gold
        player.inventory.remove_item(item_id)
        player.save()
    
    return jsonify({"success": success, "message": msg, "gold": player.gold})


# ─── Отдых ─────────────────────────────────────────────────────────────────

@app.route("/api/rest", methods=["POST"])
def rest():
    d = request.get_json(force=True)
    rest_type = d.get("type", "short")
    loc = world.get_current()
    
    if not loc:
        return jsonify({"error": "Нет локации"}), 400
    
    can, msg = can_rest(loc.id, rest_type)
    if not can:
        return jsonify({"error": msg}), 400
    
    if rest_type == "long":
        result = long_rest(player)
    else:
        result = short_rest(player)
    
    _director_update_on_rest()
    player.save()
    return jsonify({
        "message": result.message,
        "hp_healed": result.hp_healed,
        "spells_restored": result.spells_restored,
        "random_event": result.random_event,
    })


# ─── Сундуки ───────────────────────────────────────────────────────────────

@app.route("/api/chest/open", methods=["POST"])
def open_chest():
    d = request.get_json(force=True)
    chest_type = d.get("type", "wooden")
    loot = generate_chest_loot(chest_type)
    
    for item in loot:
        if "gold" in item:
            player.gold = getattr(player, 'gold', 0) + item["gold"]
        elif item.get("item_id") != "gold":
            from player.inventory import Item as InvItem
            new_item = InvItem(
                name=item.get("name", "?"),
                icon=item.get("icon", "?"),
                item_type=item.get("item_type", "misc"),
                properties=item.get("properties", {}),
            )
            player.inventory.add_item(new_item)
    
    player.save()
    return jsonify({"loot": loot})


# ─── Энкаунтеры ────────────────────────────────────────────────────────────

ENCOUNTERS_FILE = os.path.join("db", "encounters.json")


def _load_encounters():
    if os.path.exists(ENCOUNTERS_FILE):
        with open(ENCOUNTERS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {"completed": {}}


def _save_encounters(data):
    os.makedirs(os.path.dirname(ENCOUNTERS_FILE), exist_ok=True)
    with open(ENCOUNTERS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


@app.route("/api/encounter/state")
def encounter_state():
    loc = world.get_current()
    if not loc or not loc.local_map:
        return jsonify({"completed": {}})
    data = _load_encounters()
    loc_id = loc.id
    completed = {k: v for k, v in data.get("completed", {}).items() if k.startswith(loc_id + ":")}
    return jsonify({"completed": completed})


@app.route("/api/encounter/start", methods=["POST"])
def encounter_start():
    global combat, active_trap
    d = request.get_json(force=True)
    subarea_id = d.get("subarea_id", "")
    loc = world.get_current()
    if not loc or not loc.local_map:
        return jsonify({"error": "Нет локации"}), 400

    data = _load_encounters()
    key = f"{loc.id}:{subarea_id}"
    if data.get("completed", {}).get(key):
        return jsonify({"error": "Энкаунтер уже пройдён"}), 400

    sa = None
    for s in loc.local_map.get("subareas", []):
        if s["id"] == subarea_id and "encounter" in s:
            sa = s
            break
    if not sa:
        return jsonify({"error": "Нет энкаунтера"}), 400

    enc = sa["encounter"]
    combat = CombatEngine()
    player_sb = StatBlock(
        name=player.name, hp=player.hp, max_hp=player.max_hp,
        ac=player.get_ac(), level=player.level,
        strength=player.attributes.get("str", 10),
        dexterity=player.attributes.get("dex", 10),
        constitution=player.attributes.get("con", 10),
        intelligence=player.attributes.get("int", 10),
        wisdom=player.attributes.get("wis", 10),
        charisma=player.attributes.get("cha", 10),
    )
    weapon = None
    if hasattr(player, "inventory") and player.inventory.equipment.get("weapon"):
        weapon = player.inventory.equipment["weapon"]
    if weapon:
        dmg = weapon.properties.get("damage", "1d6")
        player_sb.attacks.append(Attack(name=weapon.name, damage_dice=dmg, damage_type=DamageType.SLASHING))
    else:
        player_sb.attacks.append(Attack(name="Кулаки", damage_dice="1", damage_type=DamageType.BLUDGEONING))
    combat.add_combatant(player_sb, is_player=True, team=0)

    for eid in enc.get("monsters", []):
        msb = spawn_monster(eid)
        combat.add_combatant(msb, is_player=False, team=1)
    combat.start()

    return jsonify({
        "message": enc["name"],
        "state": combat.get_state(),
    })


@app.route("/api/encounter/complete", methods=["POST"])
def encounter_complete():
    d = request.get_json(force=True)
    subarea_id = d.get("subarea_id", "")
    loc = world.get_current()
    if not loc:
        return jsonify({"error": "Нет локации"}), 400

    data = _load_encounters()
    key = f"{loc.id}:{subarea_id}"
    data.setdefault("completed", {})[key] = True
    _save_encounters(data)
    return jsonify({"ok": True})


# ─── Золото ────────────────────────────────────────────────────────────────

@app.route("/api/gold")
def get_gold():
    return jsonify({"gold": getattr(player, 'gold', 0)})


@app.route("/api/gold", methods=["POST"])
def set_gold():
    global player
    d = request.get_json(force=True)
    player.gold = d.get("gold", 0)
    player.save()
    return jsonify({"gold": player.gold})


# ─── XP и уровни ──────────────────────────────────────────────────────────

@app.route("/api/xp")
def get_xp():
    return jsonify({
        "xp": player.xp,
        "level": player.level,
        "xp_to_next": player.to_dict().get("xp_to_next", 999999),
    })


@app.route("/api/xp/add", methods=["POST"])
def add_xp():
    d = request.get_json(force=True)
    amount = d.get("amount", 0)
    result = player.gain_xp(amount)
    player.save()
    return jsonify(result)


@app.route("/api/levelup", methods=["POST"])
def level_up():
    player.level_up()
    player.save()
    return jsonify({
        "level": player.level,
        "max_hp": player.max_hp,
        "hp": player.hp,
        "proficiency_bonus": player.proficiency_bonus,
    })


# ─── Время и погода ────────────────────────────────────────────────────────

@app.route("/api/time")
def get_time():
    return jsonify(game_time.to_dict())


@app.route("/api/time/advance", methods=["POST"])
def advance_time():
    d = request.get_json(force=True)
    minutes = d.get("minutes", 30)
    game_time.advance(minutes)
    return jsonify(game_time.to_dict())


# ─── Квесты ────────────────────────────────────────────────────────────────

@app.route("/api/quests")
def list_quests():
    loc = world.get_current()
    loc_id = loc.id if loc else ""
    available = quest_manager.get_available_quests(
        player_level=player.proficiency_bonus,
        location=loc_id,
    )
    return jsonify({
        "available": [q.to_dict() for q in available],
        "active": [q.to_dict() for q in quest_manager.get_active_quests()],
        "completed": [q.to_dict() for q in quest_manager.get_completed_quests()],
    })


@app.route("/api/quests/accept", methods=["POST"])
def accept_quest():
    d = request.get_json(force=True)
    quest_id = d.get("quest_id")
    success, msg = quest_manager.accept_quest(quest_id)
    return jsonify({"success": success, "message": msg})


@app.route("/api/quests/progress", methods=["POST"])
def quest_progress():
    d = request.get_json(force=True)
    event_type = d.get("type")
    target = d.get("target")
    amount = d.get("amount", 1)
    updates = quest_manager.update_quest_progress(event_type, target, amount)
    return jsonify({"updates": updates})


@app.route("/api/quests/<quest_id>")
def get_quest(quest_id):
    q = quest_manager.quests.get(quest_id)
    if not q:
        return jsonify({"error": "Квест не найден"}), 404
    return jsonify(q.to_dict())


# ─── LLM Генерация ────────────────────────────────────────────────────────

@app.route("/api/generate/npc", methods=["POST"])
def gen_npc():
    d = request.get_json(force=True)
    location_id = d.get("location_id", "village")
    context = d.get("context", "")
    result = generate_npc(location_id, context)
    if not result:
        return jsonify({"error": "LLM недоступен или генерация не удалась"}), 503
    return jsonify(result)


@app.route("/api/generate/location", methods=["POST"])
def gen_location():
    existing = [l.id for l in world.locations.values()]
    result = generate_location(existing)
    if not result:
        return jsonify({"error": "LLM недоступен или генерация не удалась"}), 503
    return jsonify(result)


@app.route("/api/generate/encounter", methods=["POST"])
def gen_encounter():
    d = request.get_json(force=True)
    location_id = d.get("location_id", "forest")
    result = generate_encounter(location_id)
    if not result:
        return jsonify({"error": "LLM недоступен или генерация не удалась"}), 503
    return jsonify(result)


@app.route("/api/generate/trap", methods=["POST"])
def gen_trap():
    d = request.get_json(force=True)
    location_id = d.get("location_id", "cave")
    severity = d.get("severity", "moderate")
    result = generate_trap(location_id, severity)
    if not result:
        return jsonify({"error": "LLM недоступен или генерация не удалась"}), 503
    return jsonify(result)


# ─── Storyteller ───────────────────────────────────────────────────────────

@app.route("/api/storyteller/generate", methods=["POST"])
def storyteller_generate():
    d = request.get_json(force=True)
    theme = d.get("theme", "")
    mode = d.get("mode", "full")

    if mode == "full":
        arc = storyteller.generate_full_story(theme)
    else:
        arc = storyteller.generate_step_by_step(theme)

    if not arc:
        return jsonify({"error": "LLM недоступен или генерация не удалась"}), 503

    storyteller.save()
    return jsonify({"ok": True, "story": storyteller.to_dict(), "summary": storyteller.get_summary()})


@app.route("/api/storyteller/state")
def storyteller_state():
    if not storyteller.current_arc:
        return jsonify({"has_story": False})
    return jsonify({"has_story": True, "story": storyteller.to_dict(), "summary": storyteller.get_summary()})


@app.route("/api/storyteller/apply", methods=["POST"])
def storyteller_apply():
    if not storyteller.current_arc:
        return jsonify({"error": "Нет истории"}), 400
    results = storyteller.apply_to_game(app)
    return jsonify({"ok": True, "applied": results})


@app.route("/api/storyteller/summary")
def storyteller_summary():
    return jsonify({"summary": storyteller.get_summary()})


# ─── AI Director ───────────────────────────────────────────────────────────

@app.route("/api/director/state")
def director_state():
    return jsonify(director_ai.get_state())


@app.route("/api/director/evaluate", methods=["POST"])
def director_evaluate():
    events = director_ai.evaluate()
    return jsonify({
        "events": [{"type": e.event_type.value, "title": e.title,
                     "description": e.description, "data": e.data, "priority": e.priority}
                    for e in events],
        "state": director_ai.get_state(),
    })


@app.route("/api/director/toggle", methods=["POST"])
def director_toggle():
    active = director_ai.toggle()
    return jsonify({"is_active": active})


@app.route("/api/director/metrics", methods=["POST"])
def director_update_metrics():
    d = request.get_json(force=True)
    director_ai.update_metrics(**d)
    return jsonify(director_ai.get_state())


@app.route("/api/npc/<nid>/state")
def npc_state(nid):
    npc, err = _npc_or_404(nid)
    if err: return err
    return jsonify(npc.to_dict())

@app.route("/api/npc/<nid>/history")
def npc_history(nid):
    npc, err = _npc_or_404(nid)
    if err: return err
    return jsonify(npc.dialogue_history)

@app.route("/api/npc/<nid>/memory")
def npc_memory(nid): return jsonify(rag.get_all(nid))

@app.route("/api/npc/<nid>/memory", methods=["POST"])
def npc_memory_add(nid):
    d = request.get_json(force=True)
    text = d.get("text", "")
    facts = d.get("facts", [])
    if not text:
        return jsonify({"error": "text required"}), 400
    rag.store(nid, text, facts=facts if facts else None, meta={"type": "manual"})
    return jsonify({"ok": True, "total": len(rag.get_all(nid))})


@app.route("/api/npc/<nid>/relations", methods=["GET"])
def npc_relations_get(nid):
    npc, err = _npc_or_404(nid)
    if err: return err
    resolved = {}
    for rid, rtype in (npc.relations or {}).items():
        other = npcs.get(rid)
        resolved[rid] = {"type": rtype, "name": other.name if other else rid}
    return jsonify(resolved)


@app.route("/api/npc/<nid>/relations", methods=["POST"])
def npc_relations_set(nid):
    npc, err = _npc_or_404(nid)
    if err: return err
    d = request.get_json(force=True)
    target_id = d.get("target_id", "")
    rel_type = d.get("type", "")
    if not target_id or not rel_type:
        return jsonify({"error": "target_id and type required"}), 400
    npc.relations = getattr(npc, "relations", {}) or {}
    npc.relations[target_id] = rel_type
    npc.save()
    return jsonify({"ok": True, "relations": npc.relations})

@app.route("/api/npc/<nid>/summary")
def npc_summary(nid):
    npc, err = _npc_or_404(nid)
    if err: return err
    return jsonify({"summary": npc.current_summary})


# ─── Игрок ─────────────────────────────────────────────────────────────────

@app.route("/api/player", methods=["GET"])
def get_player(): return jsonify(player.to_dict())

@app.route("/api/player", methods=["POST"])
def update_player():
    global player
    d = request.get_json(force=True)
    
    if "attributes" in d and "name" in d:
        attrs = d.get("attributes", {})
        for k in ["str", "dex", "con", "int", "wis", "cha"]:
            attrs[k] = max(8, min(15, int(attrs.get(k, 10))))
        player = Player.create(d["name"], attrs)
        player.save()
        return jsonify(player.to_dict())
    
    if "name" in d: player.name = d["name"]
    if "attributes" in d:
        for k, v in d["attributes"].items():
            if k in player.attributes: player.attributes[k] = int(v)
    if "proficiency_bonus" in d: player.proficiency_bonus = int(d["proficiency_bonus"])
    if "proficiencies" in d: player.proficiencies = d["proficiencies"]
    player.save()
    return jsonify(player.to_dict())

@app.route("/api/skills")
def list_skills():
    return jsonify([{"id": k, "name": v, "attribute": SKILL_ATTR[k]} for k, v in SKILL_NAMES.items()])


# ─── Инвентарь ─────────────────────────────────────────────────────────────

@app.route("/api/inventory")
def get_inventory(): return jsonify(player.inventory.to_dict())

@app.route("/api/inventory/add", methods=["POST"])
def inventory_add():
    from player.inventory import Item
    d = request.get_json(force=True)
    item = Item(name=d.get("name", "?"), description=d.get("description", ""),
                icon=d.get("icon", "?"), item_type=d.get("item_type", "misc"),
                stack_size=d.get("stack_size", 1), properties=d.get("properties", {}))
    ok = player.inventory.add_item(item)
    player.save()
    return jsonify({"ok": ok, "inventory": player.inventory.to_dict()})

@app.route("/api/inventory/equip", methods=["POST"])
def inventory_equip():
    d = request.get_json(force=True)
    item, err = player.inventory.equip(d["item_id"])
    if err: return jsonify({"ok": False, "error": err}), 400
    player.save()
    return jsonify({"ok": True, "inventory": player.inventory.to_dict()})

@app.route("/api/inventory/unequip", methods=["POST"])
def inventory_unequip():
    d = request.get_json(force=True)
    item, err = player.inventory.unequip(d["slot"])
    if err: return jsonify({"ok": False, "error": err}), 400
    player.save()
    return jsonify({"ok": True, "inventory": player.inventory.to_dict()})

@app.route("/api/inventory/remove", methods=["POST"])
def inventory_remove():
    d = request.get_json(force=True)
    item = player.inventory.remove_item(d["item_id"])
    player.save()
    return jsonify({"ok": item is not None, "inventory": player.inventory.to_dict()})

@app.route("/api/inventory/move", methods=["POST"])
def inventory_move():
    d = request.get_json(force=True)
    bp = player.inventory.backpack
    f, t = d["from"], d["to"]
    if 0 <= f < len(bp) and 0 <= t < len(bp):
        bp[f], bp[t] = bp[t], bp[f]
        player.save()
    return jsonify({"ok": True, "inventory": player.inventory.to_dict()})


# ─── Сохранения ────────────────────────────────────────────────────────────

def _get_game_state() -> dict:
    return {
        "player": player.to_dict(),
        "location_id": world.current_location_id,
        "time": game_time.save(),
        "quest_progress": quest_manager.to_dict(),
        "story": storyteller.to_dict() if storyteller.current_arc else {},
    }


@app.route("/api/save/list")
def list_saves():
    return jsonify(save_manager.list_saves())


@app.route("/api/save", methods=["POST"])
def save_game():
    d = request.get_json(force=True)
    name = d.get("name", "save")
    state = _get_game_state()
    path = save_manager.save_game(name, state)
    return jsonify({"ok": True, "path": path})


@app.route("/api/save/quick", methods=["POST"])
def quick_save():
    state = _get_game_state()
    path = save_manager.quick_save(state)
    return jsonify({"ok": True, "path": path})


@app.route("/api/load", methods=["POST"])
def load_game():
    global player, game_time, quest_manager
    d = request.get_json(force=True)
    name = d.get("name", "quicksave")
    state = save_manager.load_game(name)
    if not state:
        return jsonify({"error": "Сохранение не найдено"}), 404
    
    player_data = state.get("player", {})
    inv_data = player_data.pop("inventory", {})
    from player.inventory import Inventory
    inv = Inventory(equipment=inv_data.get("equipment"), backpack=inv_data.get("backpack"))
    player = Player(
        name=player_data.get("name", "Герой"),
        level=player_data.get("level", 1),
        xp=player_data.get("xp", 0),
        hp=player_data.get("hp", 20),
        max_hp=player_data.get("max_hp", 20),
        gold=player_data.get("gold", 50),
        attributes=player_data.get("attributes", {}),
        proficiency_bonus=player_data.get("proficiency_bonus", 2),
        proficiencies=player_data.get("proficiencies", []),
        inventory=inv,
        location_id=player_data.get("location_id", "village"),
    )
    
    world.set_position(state.get("location_id", "village"))
    
    time_data = state.get("time", {})
    game_time = GameTime.load(time_data)
    
    return jsonify({"ok": True, "player": player.to_dict()})


@app.route("/api/save/delete", methods=["POST"])
def delete_save():
    d = request.get_json(force=True)
    name = d.get("name")
    ok = save_manager.delete_save(name)
    return jsonify({"ok": ok})


# ─── Загрузка ──────────────────────────────────────────────────────────────

def _load_npcs():
    saved = NPC.load_all()
    npcs.update(saved)
    for p in (os.path.join(NPC_DATA_DIR, f) for f in ("kira.json", "unknown_npc.json")):
        if not os.path.exists(p): continue
        npc = NPC.from_config(p)
        if npc.id not in npcs:
            npcs[npc.id] = npc
            npc.save()
            print(f"Loaded: {npc.name or 'Unknown'} ({npc.id})")


def _init_world():
    world.load_all()
    if not world.current_location_id:
        world.set_position("village")
        print("Starting in: Деревня")


_load_npcs()
_init_world()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)

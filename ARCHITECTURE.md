# Project Dusk — Architecture

## Запуск
```
pip install pygame>=2.5.0
python main.py
```

---

## Экраны и переходы

```
main_menu
  ├─► char_creation  → new_game() → world_map
  └─► load game      → world_map (or game if saved inside location)

world_map
  ├─► [E] enter_location() → game (3D first-person)
  ├─► [I] inventory overlay
  ├─► [C] status overlay
  └─► [J] journal overlay

game  (first-person raycasting)
  ├─► [Esc] leave_location() → world_map
  ├─► [I/C/J] overlays (3D view stays in background)
  ├─► [F1] debug: spawn test enemy → combat
  └─► NPC collision (TODO) → dialogue overlay

combat  (overlay over frozen 3D view)
  └─► win/flee → game | die → load save → world_map
```

---

## Структура файлов

```
main.py               # pygame loop, input routing, calls render functions
engine/
  game.py             # GameState: new_game(), save(), load(), move_player()
  world.py            # World: 16x16 grid, proc-gen, Location objects
  dungeon_map.py      # DungeonMap: 2D grid used by raycaster; generators
  combat.py           # Combat: skill-based, no to-hit dice
  events.py           # EventBus: publish/subscribe (bus.emit / bus.subscribe)
  time.py             # GameTime: in-game clock, date string
entities/
  character.py        # Base: attributes, skills, HP/Stamina, XP leveling
  player.py           # Player(Character): world pos, loc_x/y, quests
  npc.py              # NPC(Character): type, dialogue topics, loot
  item.py             # Item dataclass + factory functions
ui/
  raycaster.py        # cast_rays() → z_buffer; render_sprites()
  hud.py              # render_hud() — bottom bar: HP, Stamina, log
  world_map_view.py   # render_world_map() — top-down pygame view
  overlay.py          # all overlay panels: menu, char creation,
                      # inventory, status, journal, dialogue, combat
data/
  races.json          # race definitions + attribute bonuses
  classes.json        # class definitions + skill bonuses
  npc_names.json      # name lists for proc-gen NPCs
saves/                # JSON save files (save_0.json … save_3.json)
```

---

## Ключевые потоки данных

### Отрисовка кадра (game screen)
```
main.py
  → cast_rays(view3d, current_map, player.loc_x, player.loc_y, angle)
       → DDA per column → draws to view3d Surface → returns z_buffer[]
  → render_sprites(view3d, sprites, ..., z_buffer)
       → billboard per sprite, clipped by z_buffer
  → screen.blit(view3d)
  → _draw_minimap(screen, current_map, ...)
  → render_hud(screen, player, game_time, message_log)
```

### Боёвка
```
F1 / NPC collision → start_combat(enemy_data) → Combat(player, enemy)
KEYDOWN [A/P/B/D/U/F] → combat.resolve_round(action) → CombatResult
  result.log      → combat_log[] (shown in overlay)
  result.player_won / fled → screen = "game"
  result.player_dead       → state.load(0) → screen = "world_map"
```

### Сохранение / загрузка
```
GameState.save(slot)  → saves/save_{slot}.json
  { player: Player.to_dict(), world_seed, time, message_log }

GameState.load(slot)  → reads JSON
  → Player.from_dict()
  → World(seed)         # regenerate deterministically from seed
  → GameTime.from_dict()
```

---

## Атрибуты персонажа

| Атрибут     | Влияет на                              |
|-------------|----------------------------------------|
| Strength    | урон оружием, carry weight             |
| Intelligence| цены (speechcraft), alchemy quality    |
| Willpower   | сопротивление статус-эффектам          |
| Agility     | stamina max, mitigation                |
| Speed       | скорость движения (loc_x/y per frame)  |
| Endurance   | HP max, HP per level                   |
| Personality | цены торговцев, репутация              |
| Luck        | мелкий бонус везде (±luck/100)         |

## Навыки (Skills)

Прокачиваются через использование (use-based).
`gain_skill_xp(skill)` → накапливает `skill_points_since_level` → level up.

| Навык       | Когда растёт               |
|-------------|----------------------------|
| blade       | удар клинком               |
| blunt       | удар дробящим              |
| archery     | выстрел из лука            |
| block       | успешный блок              |
| sneak       | движение в stealth         |
| lockpick    | попытка вскрыть замок      |
| alchemy     | создание зелья             |
| speechcraft | диалог с NPC               |
| mercantile  | сделка купли/продажи       |

---

## Боёвка (combat.py)

Нет броска на попадание. Каждый удар достигает цели.

```
damage = base_weapon_damage + strength_bonus + skill_bonus + variance(±20%)
mitigation = armor.defense + agility_bonus [+ block_bonus if blocking]
actual_damage = max(1, damage - mitigation)
```

Действия игрока и врага за раунд:
- **Attack** — стандартный удар
- **Power Attack** — x2 урон, -20 stamina, игрок открыт (враг игнорирует митигацию)
- **Block** — +block_skill/5 + 5 к митигации
- **Dodge** — +speed/10 + 3 к митигации
- **Use Item** — зелье/еда
- **Flee** — успех если speed_player >= speed_enemy, иначе 50% шанс

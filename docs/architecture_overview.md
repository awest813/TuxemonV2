# Architecture Overview

Concise walkthroughs of the three core subsystems for new contributors. For debugging guidance, see [debugging_workflow.md](debugging_workflow.md).

---

## 1. Battle System

### Key Files

| File | Purpose |
|------|---------|
| `tuxemon/states/combat_state.py` | UI state, animation coordination, input handling |
| `tuxemon/combat/machine.py` | Phase-based state machine for combat flow |
| `tuxemon/combat/session.py` | Core battle logic: players, monsters, turn order, action execution |
| `tuxemon/combat/action_queue.py` | Turn-based action queueing and priority resolution |
| `tuxemon/combat/combat_context.py` | Battle initialization parameters |
| `tuxemon/states/combat_menus.py` | Player action menus (Fight, Item, Swap, Run) |
| `tuxemon/states/combat_animations.py` | Visual effects and sprite animations |

### Combat Phase Flow

```
BEGIN → READY → HOUSEKEEPING → DECISION → PRE_ACTION → ACTION → POST_ACTION
                     ↑                                               │
                     └───────────────────────────────────────────────┘
                                                                     │
                                                              RESOLVE_MATCH
                                                                     │
                                              ┌──────────────────────┼──────────────┐
                                              ▼                      ▼              ▼
                                         HAS_WINNER            DRAW_MATCH      RAN_AWAY
                                              │                      │              │
                                              └──────────────────────┴──────────────┘
                                                                     │
                                                                END_COMBAT
```

1. **BEGIN/READY**: Combat state initializes, loads sprites, sets up the battlefield.
2. **HOUSEKEEPING**: Fills open positions with party monsters.
3. **DECISION**: Player selects an action (fight/item/swap/run) via combat menus. AI selects actions for NPC trainers.
4. **PRE_ACTION/ACTION**: Actions are dequeued in speed order and executed (damage, status effects, item use).
5. **POST_ACTION**: Status effects tick, end-of-turn effects apply.
6. **RESOLVE_MATCH**: Check win/loss/draw conditions. If neither side is out, loop back to HOUSEKEEPING.
7. **END_COMBAT**: Results applied (XP, captures), state popped.

### Key Classes

- **`CombatState`**: The pygame state that drives the battle UI. Manages sprites, animations, and user input.
- **`CombatSession`**: Holds the authoritative battle state — which monsters are active, health, status, turn order.
- **`CombatMachine`**: Drives phase transitions based on the current state.
- **`ActionQueue`**: Priority queue that resolves turn order by speed, priority, and submission time.

### Multiplayer Extension

Online battles route through `MultiplayerBattleManager` (in `tuxemon/multiplayer_battle_manager.py`). Turn actions are submitted via `submit_turn_action()`, resolved authoritatively on the server, and broadcast to both clients. Connection state, timeouts, and reconnect grace periods are tracked per session.

---

## 2. Save System

### Key Files

| File | Purpose |
|------|---------|
| `tuxemon/save.py` | File I/O: serialize, write, read, detect format |
| `tuxemon/save_state.py` | Pydantic models defining save data structure |
| `tuxemon/save_upgrader.py` | Version migration: upgrade old saves to current schema |
| `tuxemon/session.py` | Orchestrates `save_state()` and `load_state()` at session level |

### Save Flow

```
Session.save_state()
  │
  ├─ player.get_state()      → NPCState (monsters, items, variables, tuxepedia, ...)
  ├─ world.get_state()        → WorldSave (factions, menu flags)
  ├─ session.get_state()      → SessionSave (UUID, playtime)
  ├─ capture_screenshot()     → base64 screenshot
  ├─ shop_manager.dump()      → shop stock dict
  ├─ battle_manager.save_log() → multiplayer battles dict
  └─ persistent NPCs          → list[NPCState]
  │
  ▼
SaveData (Pydantic model)
  │
  ▼
save.save(save_data, slot)
  │
  ├─ Serialize to JSON/CBOR/YAML
  ├─ Optional compression
  └─ Atomic write (temp file → os.replace)
```

### Load Flow

```
save.load(slot)
  │
  ├─ open_save_file()          → raw bytes
  ├─ Detect format (JSON/CBOR)
  ├─ upgrade_save(raw_data)    → migrated dict (v0 → v1 → v2 → v3)
  └─ SaveData(**upgraded)      → validated Pydantic model
  │
  ▼
Session.load_state(save_data)
  │
  ├─ player.set_state(npc_state)
  ├─ world.set_state(world_state)
  ├─ shop_manager.load_from_dict()
  ├─ battle_manager.load_log()
  └─ npc_manager.load_persistent_npc_states()
```

### Save Version Migration

The `SAVE_VERSION` constant (currently 3) tracks the schema version. When loading a save with an older version, `upgrade_save()` applies each step sequentially:

- **v0→v1**: Placeholder.
- **v1→v2**: Tuxepedia format, plague format, money structure, contacts→relationships, teleport_faint.
- **v2→v3**: Appearance field introduction.

Universal fixes (monster/technique renames) are applied regardless of version.

### Adding a New Save Migration

1. Increment `SAVE_VERSION` in `save_upgrader.py`.
2. Add `upgrade_from_vN_to_vM(save_data)` function.
3. Register it in `VERSION_UPGRADES` dict.
4. Add regression test in `tests/tuxemon/test_save_compatibility.py`.

---

## 3. Content Loading

### Key Files

| File | Purpose |
|------|---------|
| `tuxemon/database/bootstrap.py` | Initializes the database from config |
| `tuxemon/database/loader.py` | Reads JSON/YAML files, validates against models |
| `tuxemon/database/data.py` | `ModData` — the runtime database container |
| `tuxemon/database/runtime.py` | Singleton `db` instance used globally |
| `tuxemon/db.py` | Pydantic model definitions (MonsterModel, ItemModel, etc.) |
| `tuxemon/monster/monster.py` | Runtime `Monster` class built from database models |
| `mods/tuxemon/db/` | JSON data files organized by table (monster/, technique/, item/, npc/) |
| `mods/tuxemon/l18n/` | PO translation files |

### Loading Pipeline

```
mods/tuxemon/db/monster/*.json
mods/tuxemon/db/technique/*.json
mods/tuxemon/db/item/*.json
mods/tuxemon/db/npc/*.json
        │
        ▼
  ModelLoader.load_files()        Read and parse JSON/YAML
        │
        ▼
  ModelLoader.validate()          Validate against Pydantic models
        │                         (MonsterModel, TechniqueModel, etc.)
        ▼
  ModData tables                  Indexed by slug for O(1) lookup
        │
        ▼
  MonsterModel.lookup(slug, db)   Query by slug at runtime
        │
        ▼
  Monster(slug, db_data)          Runtime game object with behavior
```

### Data vs Behavior Separation

- **Data layer** (`tuxemon/db.py`): Pydantic models define the schema. Field validators enforce constraints (valid types, translation keys exist, catch rate in range). These models are read-only records.
- **Behavior layer** (`tuxemon/monster/monster.py`): Runtime classes like `Monster` consume model data and add game logic (leveling, stat calculation, status effects, battle participation).

### Adding New Content

Use the scaffold scripts for a quick start:

```bash
python scripts/scaffold_monster.py --slug mymon --name "My Mon" \
    --species lizard --types fire --stage basic \
    --description "A fiery lizard."
```

This creates the JSON definition and locale stub. Then:

1. Add sprite sheets to `mods/tuxemon/gfx/sprites/battle/mymon-sheet.png`.
2. Add sound files.
3. Fill in the moveset with technique slugs.
4. Validate: `python -m tuxemon.database.content_validator`.

### Mod System

The game supports multiple mods via the `mods/` directory. Each mod has a `mod.yaml` config. Content from later mods overrides earlier mods, enabling patches and extensions without modifying the base game files.

---

## First Contribution Path

1. **Set up**: Clone, install dependencies (`pip install -e .`), run `pytest tests` to verify.
2. **Explore**: Use `python run_tuxemon.py --status` to see the content snapshot. Try `--test-map` to load a specific map.
3. **Pick a task**: Check open issues or roadmap items in `ROADMAP.md`.
4. **Make changes**: Follow code guidelines in `CONTRIBUTING.md`. Use `black` and `isort` for formatting.
5. **Test**: Run targeted tests, then full suite (`pytest tests`). Play test for 10 minutes.
6. **Submit**: Open a PR targeting the development branch. Include the diagnostics described in [debugging_workflow.md](debugging_workflow.md).

# OpenCapsuleMon Settings Taxonomy

## Document Status

- Status: Published (Phase 1)
- Scope: All configurable settings across the engine and gameplay systems

---

## Overview

Settings in OpenCapsuleMon are organized into four layers. Each layer may override values from the layer below it. A higher-priority layer may only override the keys it is authorized to touch.

```
Layer 4 (highest): Mod / Campaign Override
Layer 3:           Host / Server Config
Layer 2:           Player Config
Layer 1 (lowest):  Engine Defaults
```

This document defines:

1. Which settings exist and what they control.
2. Which layers own each setting.
3. How fallback and precedence behavior works.

---

## 1. Layer Definitions

### Layer 1 — Engine Defaults

Built-in values defined in source code (`tuxemon/rules/models.py` and `tuxemon/config.py`). Applied when no other layer provides a value. Never modified at runtime.

**Owner:** Engine / core developers.
**Mutability:** Code change only (not user-editable).

### Layer 2 — Player Config

Per-user preferences stored in the player's local config file (`tuxemon.cfg`). May be changed by the player through the in-game settings menu at any time.

**Owner:** Player.
**Mutability:** Player-editable; persisted across sessions.
**Scope:** Applies to all contexts unless a higher layer overrides it.

Authorized keys (player may set):

| Category | Key | Type | Description |
|---|---|---|---|
| `gameplay` | `encounter_rate_modifier` | float (0.0–2.0) | Scales wild encounter frequency. |
| `gameplay` | `dialog_speed` | enum | Text scroll speed: `slow`, `medium`, `fast`, `max`. |
| `gameplay` | `unit_measure` | enum | `metric` or `imperial`. |
| `gameplay` | `combat_click_to_continue` | bool | Require click/button between combat animations. |
| `display` | `resolution_x`, `resolution_y` | int | Window resolution. |
| `display` | `fullscreen` | bool | Fullscreen mode. |
| `display` | `fps` | float | Target frame rate. |
| `display` | `show_fps` | bool | Show FPS counter. |
| `display` | `large_gui` | bool | Enlarged UI elements for accessibility. |
| `audio` | `sound_volume` | float (0.0–1.0) | Sound effects volume. |
| `audio` | `music_volume` | float (0.0–1.0) | Music volume. |
| `player` | `animation_speed` | float | Player sprite movement animation speed. |
| `player` | `player_walkrate` | float | Walk speed (tiles/sec). |
| `player` | `player_runrate` | float | Run speed (tiles/sec). |
| `controls` | all key bindings | str | Keyboard mapping for each action. |
| `locale` | `locale` | str | Language code (e.g., `en_US`, `ja`). |
| `battle` | `difficulty` | enum | Campaign difficulty preset: `easy`, `normal`, `hard`, `challenge`. |

### Layer 3 — Host / Server Config

Settings established by the session host (for casual online) or tournament administrator (for tournaments). Communicated to joining players before match confirmation. Applied on top of player config; may restrict or override gameplay-facing settings.

**Owner:** Session host or tournament admin.
**Mutability:** Set at session/tournament creation. Immutable once the match or bracket is started.
**Scope:** Applies for the duration of the host session or tournament.

Authorized keys (host/server may set):

| Category | Key | Type | Description |
|---|---|---|---|
| `battle` | `team_size` | int (1–6) | Maximum monsters per team. |
| `battle` | `level_cap` | int or null | Level cap enforced at battle start. |
| `battle` | `turn_timer_seconds` | int (0 = disabled) | Per-turn time limit. |
| `battle` | `active_clauses` | list[str] | Enabled clause IDs from rulebook vocabulary. |
| `battle` | `allow_items_in_battle` | bool | Whether items may be used during battle. |
| `battle` | `allow_held_items` | bool | Whether held items are active during battle. |
| `tournament` | `bracket_size` | int (8 or 16) | Total bracket slot count. |
| `tournament` | `check_in_duration_minutes` | int | Check-in window length. |
| `tournament` | `reconnect_grace_seconds` | int | Reconnect grace period during battle. |
| `tournament` | `no_show_timeout_seconds` | int | Time before no-show loss is applied. |

### Layer 4 — Mod / Campaign Override

Hard overrides applied by the mod or campaign author for specific zones, events, or story beats. These values are embedded in map data or campaign manifest files and cannot be changed by the player or host. Intended for authored intent (e.g., "this gym forces level-cap 20 regardless of player difficulty").

**Owner:** Mod author / campaign designer.
**Mutability:** Authored in content files; immutable at runtime.
**Scope:** Applies only for the defined zone or event context.

Authorized keys (mod may override):

| Category | Key | Description |
|---|---|---|
| `battle` | `team_size` | Force a specific team size for a battle. |
| `battle` | `level_cap` | Pin a level cap for the encounter or dungeon zone. |
| `battle` | `active_clauses` | Enforce specific clauses for story battles. |
| `battle` | `allow_items_in_battle` | Disable item use for a scripted battle. |
| `battle` | `allow_held_items` | Disable held items for story-specific battles. |
| `encounter` | `encounter_rate_modifier` | Pin or disable encounters in a zone. |
| `encounter` | `time_restrictions` | Restrict available encounters to specific time windows. |
| `trainer` | `rematch_policy` | Override the trainer's rematch eligibility. |
| `campaign` | `permadeath` | Enable or disable permadeath for the campaign. |
| `campaign` | `nuzlocke_mode` | Enable first-encounter-only catch restriction. |

---

## 2. Precedence Algorithm

At resolution time, the engine evaluates each setting key using the following algorithm:

```
def resolve(key, context):
    for layer in [mod_override, host_config, player_config, engine_defaults]:
        if layer.provides(key) and layer.authorized_for(key, context):
            return layer.get(key)
    raise KeyError(f"No value found for {key}")
```

**Fallback behavior:** If a layer does not provide a value for a key, the next lower layer is tried. The engine defaults layer always provides a value for every key (no unbounded fallback).

**Authorization check:** A layer attempting to set a key it does not own is silently ignored (the key resolves from the next lower authorized layer). This prevents host configs from accidentally overriding mod-authored values and prevents mod authors from altering player-only preferences.

---

## 3. Setting Lifecycle

| Event | Behavior |
|---|---|
| Engine startup | Engine defaults loaded. |
| Player config load | Player config loaded and merged over defaults. |
| Session/tournament created | Host config applied over player config for session scope. |
| Map/zone entered | Mod overrides applied for the zone; overrides expire on zone exit. |
| Battle start | Final resolved ruleset snapshot is frozen for the duration of the battle. |
| Battle end | Zone-scoped overrides remain active; session-scoped overrides remain until session ends. |
| Session end | Host config removed; player config and engine defaults remain. |
| Save | Player config layer persisted. Host config and mod overrides are NOT persisted (they re-apply on load from content files). |

---

## 4. Settings Not Configurable by Players or Hosts

The following settings are engine-internal and locked to their defaults at runtime:

- `save_method` — JSON serialization format.
- `compress_save` — Save compression algorithm.
- `save_prefix`, `save_extension` — Save file naming.
- `data` — Active mod directory name.
- `recompile_translations` — Translation cache behavior.
- Internal timing constants (day/night hour boundaries, season boundaries).

---

## 5. Regression Testing Requirements

For each setting key:

1. **Default resolution:** Key resolves to engine default when no other layer provides it.
2. **Player override:** Player config value overrides the default for authorized keys.
3. **Host override:** Host config value overrides player config for authorized keys.
4. **Mod override:** Mod override takes precedence over host and player config for authorized keys.
5. **Unauthorized override ignored:** A layer attempting to set a key it does not own falls through to the next authorized layer.
6. **Battle snapshot:** The resolved ruleset frozen at battle start does not change if a lower-layer value changes mid-battle.

See `tests/tuxemon/rules/` for the full regression test suite covering these behaviors.

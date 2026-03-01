# Tile Editor Guide

This guide explains how to create and edit maps for OpenCapsuleMon using the
[Tiled map editor](https://www.mapeditor.org/).

---

## Quick start

1. Download and install **Tiled** (1.10 or later recommended).
2. Open the repository root in Tiled:
   **File → Open Project → `.tuxemon.tiled-project`**
3. Maps live in `mods/tuxemon/maps/`.  Open any `.tmx` file to explore an
   existing map or create a new one.

---

## File formats

| File | Purpose |
|------|---------|
| `.tmx` | Map file (tile layers, objects, map properties). |
| `.tsx` | External tileset definition (tile grid + per-tile properties). |
| `.yaml` | Companion event/collision file – merged with the TMX at load time. |

> **Rule:** Always use *external* tilesets (`.tsx`).  Never embed tileset
> data directly inside a `.tmx` file.

---

## Required map properties

Every `.tmx` file must declare the following property in its **Map Properties**
panel (accessible via **Map → Map Properties**):

| Property | Type   | Description |
|----------|--------|-------------|
| `slug`   | string | Unique identifier matching the filename without extension. Must be lowercase with underscores. |

### Optional map properties

| Property    | Allowed values | Description |
|-------------|----------------|-------------|
| `edges`     | `clamped`, `looped` | How the camera/player behaves at map edges. |
| `map_type`  | `notype`, `town`, `route`, `clinic`, `shop`, `dungeon` | Used for encounter tables and ambient music selection. |
| `scenario`  | string | Slug of a shared YAML event file to overlay on this map. |
| `inside`    | bool | Set to `true` for indoor maps (affects lighting and encounter logic). |

---

## Tile layers

Use standard Tiled tile layers for rendering.  Layer names are mostly
cosmetic but the special name `Above Player` causes tiles in that layer to
render on top of the player sprite.

Typical layer stack (bottom to top):

```
Tile Layer 1    ← ground / base terrain
Tile Layer 2    ← decoration (flowers, paths, etc.)
Above Player    ← tree tops, building overhangs, etc.
```

---

## Object layers and object types

Objects encode collisions and interactive events.  Use **Object Layer** and
place objects with the types listed below.

### `collision` – solid region

The player and NPCs cannot enter this rectangle.

Optional properties (all string type):

| Property        | Values | Description |
|-----------------|--------|-------------|
| `enter_from`    | comma-separated directions | Directions the player **can** enter from. Omit to block from all sides. |
| `exit_from`     | comma-separated directions | Directions the player **can** exit. If only `exit_from` is set, `enter_from` is inferred as the complement. |
| `endure`        | comma-separated directions | Directions where the player can remain stationary (e.g., staircase tiles). |
| `key`           | `default`, `slide`, `push_tile` | Special region behaviour. |
| `speed_modifier`| float | Movement speed multiplier (e.g., `0.5` for mud). |
| `push_direction`| single direction | Required when `key=push_tile`. |
| `push_strength` | integer ≥ 1 | Required when `key=push_tile`. |

Valid direction tokens: `up`, `down`, `left`, `right`

### `collision-line` – one-sided barrier

A **polyline** (not a polygon) that blocks movement across the line from one
direction only.  Useful for ledges where the player can jump down but not
climb up.

### `event` – trigger region

When the player steps into this rectangle, the engine evaluates conditions
and runs actions.

Properties use the naming convention `condN` / `actN` where `N` is a
multiple of 10 (10, 20, 30 …):

| Prefix | Meaning |
|--------|---------|
| `cond10`, `cond20`, … | Condition strings evaluated in order. |
| `act10`, `act20`, …  | Action strings executed when all conditions pass. |
| `behav10`, …         | Behaviour strings (advanced scripting). |

Example:

```
name:  Enter Town Hall
type:  event
cond10 player_facing_tile down
act10  teleport town_hall,5,8,down
```

At least one `act*` property is required.

### `init` – map-load trigger

Identical to `event` but fires once when the map loads, not when the player
enters the region.  Useful for one-time setup scripts.

---

## Tileset tile properties

Per-tile properties are declared in the `.tsx` file and control how the
engine interprets each tile for movement and physics.

| Property key    | Allowed values | Description |
|-----------------|----------------|-------------|
| `enter_from`    | comma-separated directions | Directions an entity may enter this tile from. |
| `exit_from`     | comma-separated directions | Directions an entity may leave this tile through. |
| `endure`        | comma-separated directions | Directions where movement is sustained. |
| `key`           | `default`, `slide`, `push_tile` | Region behaviour strategy. |
| `push_direction`| single direction | Push direction for `push_tile` key. |
| `push_strength` | integer | Push force for `push_tile` key. |
| `speed_modifier`| float | Movement speed multiplier. |
| `surfable`      | float | Surfing movement rate (0.0 disables). |
| `walkable`      | float | Walking movement rate override. |
| `climbable`     | float | Climbing movement rate override. |

---

## Authoring conventions

- **Grid alignment:** All collision and event objects must be aligned to the
  tile grid.  Use **View → Snap to Grid** in Tiled.
- **Lowercase filenames:** Map filenames must be all lowercase with
  underscores, e.g. `azure_town.tmx`.
- **External tilesets only:** Never embed tilesets; always reference `.tsx`
  files with a relative `source` path.
- **Slug matches filename:** The `slug` map property must equal the filename
  stem (`azure_town` for `azure_town.tmx`).

---

## Validating maps

A validation script is provided to catch common authoring errors before
committing:

```bash
# Validate all maps in the default mod:
python scripts/validate_maps.py

# Validate a single file:
python scripts/validate_maps.py mods/tuxemon/maps/azure_town.tmx

# Also validate tilesets:
python scripts/validate_maps.py --tilesets

# JSON output for editor integrations:
python scripts/validate_maps.py --json

# Treat warnings as errors (recommended for CI):
python scripts/validate_maps.py --strict
```

The validator checks:

- Required `slug` property is present and non-empty.
- `edges` value, when set, is `clamped` or `looped`.
- `map_type` value, when set, is one of the recognised types.
- Referenced `.tsx` tileset files exist on disk.
- Object names are not empty.
- Object types belong to the recognised set.
- `event` and `init` objects have at least one `act*` property.
- Objects are within the map bounds.
- Tileset images referenced by `.tsx` files exist on disk.
- Per-tile direction properties contain only valid tokens.

---

## CI integration

The validator is already wired into the project's test suite.  You can also
add it as a pre-commit step:

```yaml
# .pre-commit-config.yaml
- repo: local
  hooks:
    - id: validate-maps
      name: Validate TMX maps
      entry: python scripts/validate_maps.py --strict
      language: system
      types: [file]
      files: \.tmx$
```

---

## Tiled project setup

The `.tuxemon.tiled-project` file at the repository root configures Tiled
with:

- **Custom property types** – `MapEdges`, `MapType`, `Direction`, and
  `RegionKey` enums appear in Tiled's property editor dropdowns.
- **Object type templates** – `.tuxemon-object-types.xml` provides pre-filled
  property templates when you place `collision`, `event`, or `init` objects.

Open the project once with **File → Open Project** and Tiled will remember it.

---

## Further reading

- [Tiled documentation](https://doc.mapeditor.org/)
- `tuxemon/map/loader.py` – how TMX files are parsed at runtime.
- `tuxemon/map/region.py` – `RegionProperties` and direction logic.
- `tuxemon/map/validator.py` – validation logic (importable as a library).
- `scripts/snap_map.py` – snap misaligned objects to the tile grid.
- `scripts/yamlify_map_script.py` – extract events from TMX into YAML.

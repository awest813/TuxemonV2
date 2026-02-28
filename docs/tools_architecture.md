# Tools Architecture Note

This document provides a domain-based inventory of the current utility surface in `tuxemon/tools.py` and related modules. It serves as the reference for the phased modularization plan described in `tools_expansion_roadmap.md`.

## Current Module Layout

| Module | Responsibility |
|--------|---------------|
| `tuxemon/tools.py` | Mixed-responsibility utility layer (type coercion, comparisons, dialog helpers, formatting, coordinate helpers, misc) |
| `tuxemon/platform/tools.py` | Input-level helpers (`ButtonEdgeFilter`, `ScriptInputCache`, key/unicode maps) |
| `tuxemon/rumble/tools.py` | Rumble parameter model and dynamic library probing |
| `scripts/*.py` | One-off contributor data-maintenance scripts |

## Canonical Domain Modules (Extraction Targets)

When `tuxemon/tools.py` is modularized, functions should move to these domain modules. The `tuxemon/tools.py` file remains as a backward-compatible re-export facade during the transition.

### `tuxemon/tools/casting.py` — Type Coercion

Responsible for converting raw values between types, casting dataclass parameters, and type introspection utilities.

| Function | Current Location | Notes |
|----------|-----------------|-------|
| `cast_value()` | `tools.py:310` | High complexity; benefits from isolated testing |
| `cast_dataclass_parameters()` | `tools.py:538` | Depends on `cast_value`, `get_cached_type_info` |
| `get_types_tuple()` | `tools.py:495` | Pure typing utility |
| `get_cached_type_info()` | `tools.py:512` | LRU-cached; used by `cast_dataclass_parameters` |
| `safe_enum_value()` | `tools.py:140` | Enum conversion with fallback |
| `get_valid_uuid()` | `tools.py:163` | UUID retrieval from game variables |
| `parse_flag()` | `tools.py:692` | Boolean string parsing |

**Allowed dependencies:** Standard library only (no game-specific imports).

### `tuxemon/tools/conditions.py` — Comparison & Condition Checking

Responsible for numeric/tuple comparison and set-based condition evaluation.

| Function | Current Location | Notes |
|----------|-----------------|-------|
| `compare()` | `tools.py:631` | Operator-string based comparison |
| `compare_tuple()` | `tools.py:666` | Tuple variant of `compare` |
| `check_condition()` | `tools.py:702` | Set membership with negation support |

**Allowed dependencies:** `tuxemon.db.Comparison` enum, standard library operators.

### `tuxemon/tools/dialog.py` — Dialog & UI Helpers

Responsible for opening dialogs, choice menus, and result displays. These depend on the game client and UI subsystem.

| Function | Current Location | Notes |
|----------|-----------------|-------|
| `open_dialog()` | `tools.py:189` | Core dialog opening utility |
| `open_choice_dialog()` | `tools.py:244` | Choice menu dialog |
| `show_result_as_dialog()` | `tools.py:563` | Item/technique use result display |

**Allowed dependencies:** `tuxemon.base_client`, `tuxemon.ui.*`, `tuxemon.locale`.

### `tuxemon/tools/math.py` — Mathematical & Numeric Utilities

Responsible for numeric operations, scaling, rounding, and arithmetic helpers.

| Function / Constant | Current Location | Notes |
|---------------------|-----------------|-------|
| `safe_floordiv()` | `tools.py:74` | Division-by-zero safe |
| `ops_dict` | `tools.py:80` | Operator string → function mapping |
| `number_or_variable()` | `tools.py:275` | String-to-number with variable fallback |
| `fix_measure()` | `tools.py:184` | Percentage-based measure calculation |
| `round_to_divisible()` | `tools.py:583` | Grid-aligned rounding (collision helpers) |
| `scale()` | `tools.py:127` | Display scale factor application |
| `format_playtime()` | `tools.py:724` | Seconds → "Xh Ym" formatting |

**Allowed dependencies:** `tuxemon.scaling` (for `scale()`), standard library.

### `tuxemon/tools/geometry.py` — Coordinate & Geometry

Responsible for spatial coordinate conversions and rect calculations.

| Function | Current Location | Notes |
|----------|-----------------|-------|
| `get_cell_coordinates()` | `tools.py:88` | Point-to-cell within rect |
| `get_screen_rect()` | `tools.py:113` | HUD-local to screen coordinates |
| `vector2_to_tile_pos()` | `tools.py:271` | Vector2 → tile tuple |

**Allowed dependencies:** `tuxemon.math.Vector2`, `tuxemon.compat.rect`, pygame (TYPE_CHECKING only).

### Remaining in `tuxemon/tools.py` — Facade & Misc

These stay in the root module or are general-purpose utilities too small to warrant their own module.

| Function / Constant | Notes |
|---------------------|-------|
| `Never` / `TVar` / `TEnum` | Type aliases and type variables |
| `transform_resource_filename()` | Thin wrapper around `fetch_asset` |
| `copy_dict_with_keys()` | Generic dict utility |
| `assert_never()` | Exhaustive check assertion |

## API Contract Table

| Function | Input Types | Return Type | Raises | Side Effects |
|----------|-------------|-------------|--------|-------------|
| `cast_value` | `((types, name), value)` | `Any` | `ValueError` | None |
| `cast_dataclass_parameters` | `dataclass instance` | `None` | `ValueError` | Mutates instance in place |
| `compare` | `str, number, number` | `bool` | `ValueError` | None |
| `compare_tuple` | `str, tuple, tuple` | `bool` | `ValueError` | None |
| `check_condition` | `str, set[str]` | `bool` | None | Logs via `logging.debug` |
| `parse_flag` | `str \| None` | `bool` | None | None |
| `number_or_variable` | `dict, str` | `float` | `ValueError` | None |
| `safe_enum_value` | `type[Enum], str, Enum` | `Enum` | `ValueError` (if `raise_on_error`) | Logs warning on fallback |
| `open_dialog` | `BaseClient, [str], ...` | `State` | None | Pushes state onto client |
| `open_choice_dialog` | `BaseClient, MenuOptions, ...` | `State` | None | Pushes state onto client |
| `scale` | `int` | `int` | None | May import `DISPLAY_CONTEXT` lazily |
| `round_to_divisible` | `float, int` | `int` | None | None |
| `format_playtime` | `float` | `str` | None | None |

## Dependency Layer Rules

1. **Pure helpers** (`casting.py`, `conditions.py`, `math.py`): Must not import platform-specific code (pygame, display contexts). Standard library and `tuxemon.db` enums only.
2. **Geometry helpers** (`geometry.py`): May import `tuxemon.math.Vector2` and use pygame types via `TYPE_CHECKING`.
3. **Dialog helpers** (`dialog.py`): May import game client, UI subsystem, and locale modules.
4. **Facade** (`tools.py`): Re-exports everything; may import any internal module.

## Migration Strategy

1. Create domain modules under `tuxemon/tools/` as a package.
2. Move functions to their domain modules.
3. Add re-exports in `tuxemon/tools/__init__.py` matching the current `tuxemon.tools` public API.
4. Add deprecation warnings for direct imports from old paths (non-fatal, with documented sunset version).
5. Update internal call sites incrementally — no big-bang rename.

## Scripts Surface (Contributor Utilities)

Scripts in `scripts/` are one-off data maintenance tools. They should:
- Not be imported by runtime game code.
- Follow a consistent CLI pattern (see `tools_expansion_roadmap.md` Phase 5).
- Include a docstring describing purpose and usage.
- Exit non-zero on actionable failures.

# Runtime Tools Architecture Note

This document defines the planned module boundaries for runtime helpers currently exposed through `tuxemon.tools`.

## Scope and goals

- Keep `tuxemon.tools` as a **public compatibility facade** during migration.
- Move helpers into coherent domain modules with explicit contracts.
- Keep pure runtime helper modules free from platform-specific dependencies.

## Canonical module boundaries

| Module | Responsibilities | Must not import |
| --- | --- | --- |
| `tuxemon.tools.casting` | Type coercion and parsing helpers (`cast_value`, dataclass casting helpers, typed collections). | `pygame`, client/state classes, UI modules. |
| `tuxemon.tools.conditions` | Condition checking and comparison helpers (`check_compare`, key comparator utilities). | Platform/input modules. |
| `tuxemon.tools.dialog` | Dialog and menu helper wrappers (`open_dialog`, `open_choice_dialog`, text formatting integration). | Platform/input modules. |
| `tuxemon.tools.math_utils` | Scalar/tuple math and coordinate helpers (`safe_floordiv`, `fix_measure`, `get_cell_coordinates`, scaling-safe helpers). | UI/client modules unless required by type hints under `TYPE_CHECKING`. |
| `tuxemon.tools.resources` | Resource path and asset lookup helpers (`transform_resource_filename`). | Platform/input modules. |
| `tuxemon.tools.identifiers` | Identifier and enum guards (`safe_enum_value`, `get_valid_uuid`). | Platform/input modules. |

## Runtime utility vs contributor script boundary

Use runtime tools when the helper:

- is needed during gameplay execution,
- has deterministic behavior suitable for unit tests,
- and belongs to a stable API surface.

Use contributor scripts (`scripts/*.py`) when behavior is:

- one-off data migration or maintenance,
- repository content rewrite that should be manually reviewed,
- and not expected to execute in normal game runtime.

## Allowed dependency layers

1. **Pure helper layer** (`casting`, `conditions`, `math_utils`, `resources`, `identifiers`)
   - Standard library + internal pure modules.
   - No platform-specific libraries.
2. **UI helper layer** (`dialog`)
   - May depend on UI/localization components.
   - Must not depend on platform-specific input code.
3. **Compatibility facade** (`tuxemon.tools`)
   - Re-exports from focused modules.
   - Emits deprecation guidance for direct legacy imports once migration begins.

## API contract table (phase-1 baseline)

| Function | Expected inputs | Exception behavior | Side effects / logging |
| --- | --- | --- | --- |
| `cast_value` | `value: Any`, `target_type: type hint` | Raises `TypeError`/`ValueError` for unsupported coercion paths. | No side effects; pure conversion. |
| `safe_enum_value` | `enum_class`, `value`, `default`, `raise_on_error=False` | Raises `ValueError` only when `raise_on_error=True`; otherwise returns default. | Warn-level log on invalid input fallback. |
| `get_valid_uuid` | `game_variables`, `variable_name` | Never raises on malformed variable; returns `None`. | Info log on sentinel value; warn log on malformed UUID. |
| `check_compare` | `value0`, `operator`, `value1` | Raises `KeyError` or `ValueError` for invalid comparator/operator inputs. | No side effects. |
| `open_dialog` | `client`, dialog text, optional avatar/style/position args | Propagates state errors from `client.push_state` if called with invalid state config. | Pushes dialog state (runtime state side effect). |

## Migration sequence for modularization

1. Extract pure conversion helpers into `tuxemon/tools/casting.py`.
2. Extract comparison/condition helpers into `tuxemon/tools/conditions.py`.
3. Extract dialog wrappers into `tuxemon/tools/dialog.py`.
4. Leave compatibility imports in `tuxemon/tools.py` and add deprecation notes.
5. Migrate at least one call site per module before removing legacy internals.

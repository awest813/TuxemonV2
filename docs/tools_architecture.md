# Tools Architecture

This document serves as the architecture note for the OpenCapsuleMon tools and utilities ecosystem.
It defines the canonical module structure, outlines boundaries between code layers, and helps contributors
choose where to place their helpers.

## Canonical Modules by Domain

The `tuxemon/tools/` directory is logically grouped into domains. When adding a new utility function,
choose the domain that best fits its behavior:

- **`tuxemon.tools.casting`**: Functions for coercing raw inputs into strongly-typed objects (`cast_value`, `cast_dataclass_parameters`).
- **`tuxemon.tools.math`**: Pure math functions, geometry algorithms, and comparators (`round_to_divisible`, `compare`, `ops_dict`, `safe_floordiv`).
- **`tuxemon.tools.conditions`**: State or rule checking (`check_condition`, `parse_flag`).
- **`tuxemon.tools.dialog`**: Functions that bridge user interfaces or launch dialog interactions (`open_dialog`, `show_result_as_dialog`).
- **`tuxemon.tools.misc`**: Grab-bag helpers that don't fit into the above categories, such as screen formatting, uuid safety checks, and basic enum casting (`get_valid_uuid`, `safe_enum_value`, `scale`).

## Runtime Utilities vs. Contributor Scripts

**Runtime Utilities**
If a function is called directly by game code during normal play (events, states, networking, combat), it belongs in `tuxemon/tools/`. It must be performant, safe, well-tested, and comply with strict typing.

**Contributor Scripts**
If a function is used to migrate files, clean up missing map assets, reformat data batches, or fill in localization slugs, it belongs in the `scripts/` directory. These are meant to be run once (or periodically by maintainers) from the command line, and are not imported by the main game loop.

## Dependency Layer Rules

1. **Pure Tools Must Avoid Platform Imports**: `tuxemon.tools.math`, `tuxemon.tools.casting`, and `tuxemon.tools.conditions` must not import specific hardware platform libraries such as `pygame`. If a tool relies on platform rendering loops, it belongs in `tuxemon.platform`.
2. **One-Way Tool Imports**: Systems rely on tools, tools should generally not rely on complex game systems unless strictly required for typing. Prefer dependency injection or passing simple interfaces instead of importing massive game singletons into the tool package.

## Core API Contract Table

The following is a lightweight snapshot of major extraction boundaries. This contract ensures
predictable data coercion throughout the engine.

| Function | Expected Inputs | Exception Behavior | Side Effects / Logging |
|----------|-----------------|--------------------|------------------------|
| `cast_value` | `((type_list, param_name), raw_value)` | `ValueError` if parsing fails or invalid format | None |
| `cast_dataclass_parameters` | `dataclass_instance` | `ValueError` if a field cast fails | Mutates object fields in-place |
| `check_condition` | `condition_string`, `dataset_set` | None | Debug logs check outcomes |
| `compare` | `operator_str`, `val_a`, `val_b` | `ValueError` on bad operator | None |
| `safe_enum_value` | `enum_cls`, `raw_val`, `default` | Optional `ValueError` if `raise_on_error` is True | Warns when returning default |
| `parse_flag` | `string` or `None` | None | None |

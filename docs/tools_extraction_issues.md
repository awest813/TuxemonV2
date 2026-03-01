# Tools Extraction Issue Map (Phase 1)

Tracked IDs are local planning identifiers used to tag extraction candidates in `tuxemon/tools.py`.

## Open items

- **TOOLS-101**: Extract `cast_value` and helper routines into `tuxemon.tools.casting` with unchanged behavior.
- **TOOLS-102**: Extract comparator helpers (`check_compare`, tuple/scalar comparators) into `tuxemon.tools.conditions`.
- **TOOLS-103**: Extract dialog wrappers (`open_dialog`, `open_choice_dialog`) into `tuxemon.tools.dialog`.
- **TOOLS-104**: Extract identifier safety helpers (`safe_enum_value`, `get_valid_uuid`) into `tuxemon.tools.identifiers`.
- **TOOLS-105**: Extract pure math/resource helpers into `tuxemon.tools.math_utils` and `tuxemon.tools.resources`.
- **TOOLS-106**: Introduce compatibility-facade deprecation warnings and document sunset policy.

## Completion criteria for each issue

1. Function(s) moved to target module.
2. Imports from `tuxemon.tools` still work.
3. Existing tests pass and any affected tests are updated.
4. Migration note added to docs if caller behavior changes.

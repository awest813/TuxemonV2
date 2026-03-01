# Tools Phase 1 Issue Map

This issue map captures the Phase 1 extraction boundaries requested in `docs/tools_expansion_roadmap.md` and ties compatibility TODO tags to concrete migration work.

## Scope

- Canonical module boundaries are defined in `docs/tools_architecture.md`.
- Compatibility exports currently live in `tuxemon/tools/__init__.py`.
- TODO tags in that file are linked to the issue IDs below.

## Phase 1 Extraction / Cleanup Issues

| Issue ID | Category | Current Surface | Target State | Acceptance Criteria |
|---|---|---|---|---|
| `TOOLS-201` | Shim cleanup | `Never` re-export in `tuxemon.tools` facade | Call sites import from `tuxemon.tools.misc` directly | No imports of `Never` from `tuxemon.tools`; compatibility entry removed |
| `TOOLS-202` | Casting migration | Casting types + helpers re-exported from facade | Call sites import from `tuxemon.tools.casting` | No imports of `ValidParameterSingleType`, `ValidParameterTypes`, `cast_value`, `cast_dataclass_parameters` from facade |
| `TOOLS-203` | Conditions migration | `check_condition` and `parse_flag` facade re-exports | Call sites import from `tuxemon.tools.conditions` | All rule checks import from `conditions`; facade entries removed |
| `TOOLS-204` | Dialog migration | Dialog helpers re-exported from facade | Call sites import from `tuxemon.tools.dialog` | Event/action dialog code imports only from `dialog` module |
| `TOOLS-205` | Math migration | Math helpers re-exported from facade | Call sites import from `tuxemon.tools.math` | Scalar/tuple compare + measure helpers imported directly from `math` module |
| `TOOLS-206` | Misc migration | Misc helpers re-exported from facade | Call sites import from `tuxemon.tools.misc` | All misc helper imports bypass facade |

## Tracking Notes

- These IDs are intentionally lightweight and repo-local for roadmap execution.
- When each issue is completed, remove the associated TODO comment and compatibility re-export entry from `tuxemon/tools/__init__.py`.
- If a compatibility entry needs to remain for third-party scripts, document an explicit deprecation sunset in release notes.

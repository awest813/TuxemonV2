# Tools Expansion & Polish Roadmap

This roadmap focuses on the current in-repo tool surface and proposes a staged plan to make it easier to use, safer to extend, and better tested.

## Current tool surface (quick scan)

- `tuxemon/tools.py`: shared utility layer with mixed responsibilities (type coercion, comparisons, dialog helpers, formatting, misc helpers). It is broadly used across event/actions, item systems, and entity workflows.
- `tuxemon/platform/tools.py`: input-level helpers (`ButtonEdgeFilter`, `ScriptInputCache`) and key/unicode maps.
- `tuxemon/rumble/tools.py`: rumble parameter model and dynamic library probing utility.
- `scripts/*.py`: contributor scripts that perform one-off data maintenance (example: event renumbering, monster slug filling).
- Existing test coverage includes `tests/tuxemon/test_tools.py` and devtools middleware tests, but coverage is uneven between tool modules.

---

## Guiding goals

1. **Cohesion:** reduce “misc bucket” growth by grouping utilities by domain.
2. **Safety:** tighten typing and validation for conversion-heavy helpers.
3. **Discoverability:** make tooling entry points and expected usage obvious to contributors.
4. **Reliability:** align each tool module with stable tests and CI checks.
5. **Backward compatibility:** avoid sudden breakage by introducing migration aliases and deprecation windows.

---

## Phase 1 — Inventory, boundaries, and API contracts (1-2 weeks)

- Create a `tools` architecture note documenting:
  - canonical modules by domain (e.g., `tools/casting.py`, `tools/conditions.py`, `tools/dialog.py`, `tools/math.py`),
  - what belongs in runtime utilities vs. one-off contributor scripts,
  - and allowed dependency layers (e.g., pure helpers must not import platform-specific code).
- Add a lightweight API contract table:
  - function name,
  - expected input types,
  - exception behavior,
  - side effects/logging behavior.
- Tag candidate functions in `tuxemon/tools.py` for extraction with TODO labels tied to issue IDs.

**Deliverables:** architecture note + issue list + agreed extraction map.

---

## Phase 2 — Internal modularization with compatibility shims (2-4 weeks)

- Split `tuxemon/tools.py` into focused modules while preserving imports from `tuxemon.tools` as a public compatibility facade.
- Move high-risk conversion logic (`cast_value`, dataclass casting helpers) into an isolated module with clearer helper subroutines.
- Standardize naming consistency:
  - avoid abbreviations that obscure intent,
  - use consistent boolean helper prefixes (`is_`, `has_`, `can_`),
  - align function docstrings to one style.
- Add deprecation warnings (non-fatal) when old import paths are used directly, with a documented sunset version.

**Deliverables:** modularized internals, unchanged external behavior, migration notes.

---

## Phase 3 — Validation hardening and error quality (2-3 weeks)

- Add stricter parsing policy for `cast_value`:
  - clarify numeric coercion precedence,
  - centralize bool-string parsing rules,
  - and define behavior for empty collection tokens.
- Improve error messaging consistency:
  - include parameter name and expected type family,
  - avoid overly generic “cannot cast” text,
  - preserve root cause where practical.
- Add guardrails for utility functions with hidden assumptions:
  - explicit set normalization in condition checks,
  - stricter comparator key validation helper reused by scalar/tuple compare functions.

**Deliverables:** explicit conversion spec + cleaner exceptions + reduced ambiguity.

---

## Phase 4 — Test and CI expansion (2-3 weeks)

- Expand unit test coverage for:
  - `tuxemon/platform/tools.py` (edge transitions, frame clearing behavior, key map coverage),
  - `tuxemon/rumble/tools.py` (parameter validation and library lookup behavior via mocks),
  - and additional `cast_value` branch cases (nested typing, malformed unions, invalid literals).
- Add property-style tests for conversion invariants where feasible (idempotence and round-trip scenarios).
- Gate critical tool tests in CI as a fast, always-on suite.

**Deliverables:** broader and deeper tests, faster regression detection.

---

## Phase 5 — Contributor tooling UX polish (2 weeks)

- Introduce a consistent CLI pattern for data-maintenance scripts:
  - `--dry-run`,
  - `--apply`,
  - `--json` output mode,
  - and non-zero exit codes for actionable failures.
- Add a `docs/tools_contributor_guide.md` with:
  - when to create a script vs. runtime utility,
  - how to test scripts safely,
  - and examples of common maintenance workflows.
- Add script smoke tests for core scripts used during release/content updates.

**Deliverables:** safer script workflows and lower contributor onboarding cost.

---

## Phase 6 — Observability and maintenance policy (ongoing)

- Add structured debug logs for difficult conversion paths and input edge detection.
- Define ownership and review checklist for new utilities:
  - dependency-layer check,
  - test requirement,
  - docs requirement,
  - compatibility impact statement.
- Track tool-health metrics quarterly:
  - utility-related bug count,
  - test flake rate,
  - mean time to fix converter regressions.

**Deliverables:** sustained quality rather than one-time cleanup.

---

## Suggested milestone acceptance criteria

A phase is complete when:

1. Planned docs and code changes are merged.
2. Tool-related tests pass in local and CI runs.
3. Any compatibility impact is documented with migration steps.
4. At least one real call site has been migrated/validated for each new module boundary introduced.

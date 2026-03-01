# Debugging Workflow Standardization

This workflow defines the default triage and validation loop for bugfixes in OpenCapsuleMon/TuxemonV2. Use it for gameplay bugs, content-load failures, networking regressions, and save/load issues.

## 1) Capture a Status Snapshot

Run a baseline status capture before changing code:

```bash
python run_tuxemon.py --status
```

Record in your notes/PR description:
- Branch and commit.
- Content counts (monsters, techniques, items, NPCs, maps, localizations).
- Any obvious anomalies (missing content, count drop, unexpected warnings).

## 2) Create a Narrow Reproduction Command

Prefer the smallest command that reproduces the issue:

- Single test module for a subsystem:
  ```bash
  pytest tests/tuxemon/test_save_compatibility.py
  ```
- Single test case by node id:
  ```bash
  pytest tests/tuxemon/test_save_compatibility.py::test_legacy_trade_timestamp_roundtrip
  ```
- Focused validator:
  ```bash
  python -m tuxemon.database.content_validator
  ```

If the issue is interactive, write exact repro steps with expected vs actual behavior.

## 3) Run Targeted Verification First

After implementing a fix, run only the closest checks first:

- The minimal failing test(s).
- Adjacent subsystem tests.
- Any validator or script directly tied to the bug surface.

This keeps feedback fast while iterating.

## 4) Run a Regression Safety Pass

Before merge, perform a broader confidence check:

```bash
pytest
```

If full-suite runtime is constrained, run the largest practical subset and explicitly note the limitation.

## 5) Minimum Diagnostic Output for Bugfix PRs

Every bugfix PR description should include:

1. **Issue summary:** one sentence of user-visible impact.
2. **Reproduction:** exact command(s) and/or numbered in-game steps.
3. **Root cause:** brief technical explanation of what was wrong.
4. **Fix summary:** what changed and where.
5. **Validation:** targeted command(s) plus broader regression command(s).
6. **Save/load compatibility impact:** whether persistence format or migrations were affected.
7. **Risk notes:** what areas could still regress and what was done to reduce risk.

## 6) Optional Diagnostics for Difficult Cases

When the issue is intermittent or stateful, include:

- Relevant log excerpts.
- Input fixture snippets.
- Before/after payload examples.
- Why rejected alternatives were not chosen.

Keeping this workflow consistent makes triage faster, bugfixes more reproducible, and regressions easier to prevent.

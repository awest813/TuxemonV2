# Debugging Workflow

A shared triage flow for diagnosing and fixing issues in OpenCapsuleMon. Follow these steps when investigating bugs, performance problems, or unexpected behavior.

## Quick Reference

| Step | Command / Action |
|------|-----------------|
| Status snapshot | `python run_tuxemon.py --status` |
| Narrow repro | `python run_tuxemon.py --test-map <map_name>` |
| Targeted test | `pytest tests/tuxemon/test_<module>.py -v -k <test_name>` |
| Full regression | `pytest tests` |
| Content validation | `python -m tuxemon.database.content_validator` |
| Content validation (strict) | `python -m tuxemon.database.content_validator --strict` |

---

## Step 1 — Gather a Status Snapshot

Before investigating, capture the current project state:

```bash
python run_tuxemon.py --status
```

This prints a summary of the current fork: monster count, technique count, item count, NPC count, map count, and localization count. Include this output in any bug report or PR description so reviewers can confirm the baseline.

For save-related issues, also note:
- The save slot number and whether the save predates a known version bump.
- The `version` field in the save data (current: check `SAVE_VERSION` in `tuxemon/save_upgrader.py`).

---

## Step 2 — Narrow the Reproduction

Use the smallest possible reproduction path:

**For map or world issues:**
```bash
python run_tuxemon.py --test-map <map_name>
```
This loads the map directly, skipping the title screen. Use this to test NPC interactions, event triggers, and map transitions without playing through the full game.

**For headless / server issues:**
```bash
python run_tuxemon.py --headless
```

**For specific save data issues:**
```bash
python run_tuxemon.py --load <slot_number>
```

**For content data issues:**
```bash
python -m tuxemon.database.content_validator --mod-root mods/tuxemon
```

When filing a bug, describe the reproduction in terms of these commands so others can reach the problem state quickly.

---

## Step 3 — Run a Targeted Test

If the issue maps to a specific module, run only its tests first:

```bash
# Trade system
pytest tests/tuxemon/test_trade_manager.py -v

# Multiplayer battles
pytest tests/tuxemon/test_multiplayer_battle_manager.py -v

# Network client
pytest tests/tuxemon/test_network_client.py -v

# Save/load compatibility
pytest tests/tuxemon/test_save_compatibility.py -v

# Content validation
pytest tests/tuxemon/test_content_validator.py -v

# Tools and utilities
pytest tests/tuxemon/test_tools.py -v

# Run a single test by name
pytest tests/tuxemon/test_trade_manager.py -v -k "test_accept_trade_expired_offer"
```

If the issue spans modules, use markers or patterns:

```bash
# All multiplayer-related tests
pytest tests -v -k "multiplayer"

# All save-related tests
pytest tests -v -k "save"
```

---

## Step 4 — Full Regression Pass

Before submitting a fix, run the complete test suite:

```bash
pytest tests
```

Or via tox for multi-version coverage:

```bash
tox -epy3
```

All tests must pass. If a test fails that is unrelated to your change, note it in the PR description.

---

## Step 5 — Play Test

Per the [contributing guidelines](../CONTRIBUTING.md), spend roughly 10 minutes playing the game from a new save to confirm your changes don't break anything:

1. Start a new game (do not load a save).
2. Catch a monster, navigate menus, interact with NPCs.
3. Save and reload to confirm save/load integrity.
4. Verify your specific fix or feature works as expected.

---

## Logging

Use the `logging` module — never `print()` — for debug output:

```python
import logging

logger = logging.getLogger(__name__)

logger.debug("Detailed diagnostic info: %s", value)
logger.info("Notable state change: %s", event)
logger.warning("Unexpected but recoverable: %s", issue)
logger.error("Failed operation: %s", error)
```

To increase log verbosity at runtime, configure logging before the game starts or adjust `tuxemon/constants/` configuration.

---

## Minimum Diagnostic Output for Bugfix PRs

When submitting a bugfix PR, include these in the PR description:

1. **Status snapshot** — output of `python run_tuxemon.py --status`.
2. **Reproduction command** — the narrowest command to reach the bug (e.g., `--test-map`, `--load`, a specific pytest invocation).
3. **Failing test** (if applicable) — the test name and its output before the fix.
4. **Test results after fix** — output of the targeted test run showing the fix.
5. **Full regression result** — confirmation that `pytest tests` passes.

### Template

```markdown
## Bug Description
Brief description of the problem.

## Reproduction
```
python run_tuxemon.py --test-map cotton_town
```

## Status Snapshot
```
Monsters 411, Techniques 274, Items 221, NPCs 122, Maps 224
```

## Root Cause
What went wrong and why.

## Fix
What the fix does.

## Tests
```
pytest tests/tuxemon/test_<module>.py -v -k "<test>"
# All pass
pytest tests
# All pass
```
```

---

## Common Diagnostic Scenarios

### Save won't load / crashes on load

1. Check the `version` field in the save JSON file.
2. Compare against `SAVE_VERSION` in `tuxemon/save_upgrader.py`.
3. Run the save through the upgrade pipeline manually:
   ```python
   from tuxemon.save_upgrader import upgrade_save
   import json
   with open("saves/slot1.save") as f:
       data = json.load(f)
   upgraded = upgrade_save(data)
   ```
4. Check for malformed fields (missing keys, wrong types) — the upgrader should tolerate them but log warnings.

### Monster/technique/item not found

1. Run content validation: `python -m tuxemon.database.content_validator`
2. Check the slug exists in `mods/tuxemon/db/<table>/<slug>.json`
3. Check the locale entry exists in `mods/tuxemon/l18n/en_US/LC_MESSAGES/base.po`
4. If a rename happened, check `MONSTER_RENAMES` or `TECHNIQUE_RENAMES` in `tuxemon/save_upgrader.py`

### Multiplayer connection failure

1. Check network feedback messages by looking at `consume_feedback()` output in `NetworkManager.update()`
2. Verify the feedback translation keys exist in the locale PO file
3. Check `tuxemon/network/client.py` for connection state transitions (DISCONNECTED → REGISTERING → READY)
4. Look for timeout in `ConnectionManager._registration_deadline`

### Trade or challenge not persisting

1. Check `save_log()` and `load_log()` in the relevant manager
2. Run save compatibility tests: `pytest tests/tuxemon/test_save_compatibility.py -v`
3. Inspect the `multiplayer_battles` field in the save data
4. Check for expired entries being purged on load

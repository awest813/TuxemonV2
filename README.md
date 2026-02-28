# TuxemonV2 Fork

This repository is a **fork-focused development branch** of Tuxemon, the free and open-source monster-battling RPG.

The goal of this fork is to ship practical gameplay systems, preserve save compatibility, and keep contributor workflows simple and reproducible.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)

---

## Current Project Snapshot

Check local status at any time:

```bash
python run_tuxemon.py --status
```

Snapshot at the time of this README update:

- Branch: `work`
- Commit: `c1ec2529`
- Monsters: 411
- Techniques: 274
- Items: 221
- NPCs: 122
- Maps: 224
- Localization catalogs (`.po`): 14
- Roadmap checklist completion: **17/25**

For milestone details, see [`ROADMAP.md`](ROADMAP.md).

---

## What This Fork Adds

Compared with a baseline upstream-oriented workflow, this fork currently emphasizes:

- **Progress visibility:** built-in `--status` reporting with content and roadmap summary.
- **Gameplay systems:** breeding/egg hatching, weather, fishing, and day/night cycles.
- **Online interaction reliability:** hardened trade and multiplayer challenge lifecycles with persistence and expiration handling.
- **Backward compatibility:** save/load tolerance for legacy keys and malformed historical records in multiplayer/trade logs.

---

## Quick Start

### 1) Clone

```bash
git clone <your-fork-url>
cd TuxemonV2
```

### 2) Install (editable)

```bash
python -m pip install -e . --no-build-isolation
```

### 3) Run

```bash
python run_tuxemon.py
```

---

## Useful Commands

### Show fork progress summary

```bash
python run_tuxemon.py --status
```

### Run headless

```bash
python run_tuxemon.py --headless
```

### Load a specific save slot

```bash
python run_tuxemon.py --load 1
```

### Start directly on a map (debug workflow)

```bash
python run_tuxemon.py --test-map starting_town
```

### Use a custom mod directory

```bash
python run_tuxemon.py --mod /path/to/mod
```

---

## Development Notes

- Core game code: `tuxemon/`
- Bundled content and gameplay data: `mods/`
- Tests: `tests/`
- Sphinx docs: `docs/`

Run the test suite with:

```bash
pytest
```

### Debugging quickstart

When something behaves unexpectedly, use this lightweight sequence before deeper changes:

1. Confirm content/roadmap state and commit identity:

   ```bash
   python run_tuxemon.py --status
   ```

2. Reproduce with a narrow entrypoint (headless or map-focused):

   ```bash
   python run_tuxemon.py --headless
   python run_tuxemon.py --test-map starting_town
   ```

3. Run targeted tests first, then full tests if needed:

   ```bash
   pytest tests/tuxemon/test_network_controller.py -q
   pytest -q
   ```

4. If changing save, trade, or multiplayer behavior, verify backward compatibility paths with existing fixtures in `tests/` before merging.

---

## Next Steps (Recommended Focus)

With the completed baseline now expanded into a broader 25-item plan, the next wave should focus on quality and scale:

1. **Multiplayer battle execution loop**
   - Move from challenge lifecycle completion to full synchronous battle state exchange.
2. **Online trading UX + security hardening**
   - Add clearer user-facing states and robust conflict handling for reconnect/retry scenarios.
3. **Content pipeline automation**
   - Expand validation scripts for monsters, maps, and localization consistency in CI.
4. **Balance and progression tuning**
   - Audit encounter pacing, move power curves, and economy progression in mid/late game.
5. **Contributor onboarding polish**
   - Add compact architecture notes and “first issue” pathways for new contributors.

Detailed sequencing and ownership notes are tracked in [`ROADMAP.md`](ROADMAP.md).

---

## Contributing to This Fork

Contributions are welcome. When opening a change, include:

- A concise gameplay/tooling impact summary
- Test results (or clear rationale when a test cannot run)
- Migration notes for saves/content when relevant

---

## Upstream Project

Tuxemon originated at:

- Website: <https://www.tuxemon.org>
- Upstream source: <https://github.com/Tuxemon/Tuxemon>

This fork maintains attribution and licensing alignment with upstream GPLv3.

# TuxemonV2 Fork

This repository is a **fork-focused development branch** of Tuxemon, the free and open-source monster-battling RPG.

The goal of this fork is to make iterative gameplay and tooling improvements while keeping the project easy to run from source and easy to contribute to.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)

---

## Fork Status (Current Snapshot)

You can check local progress at any time with:

```bash
python run_tuxemon.py --status
```

Current snapshot from this branch:

- Monsters: 411
- Techniques: 274
- Items: 221
- NPCs: 122
- Maps: 224
- Localization catalogs: 14
- Roadmap checklist completion: 5/8

For roadmap details, see [`ROADMAP.md`](ROADMAP.md).

---

## What’s Different in This Fork

- Added a **local fork progress report** command: `--status`.
- Updated project documentation to reflect the fork’s current state and workflow.
- Maintained compatibility with source-based development on Linux, macOS, and Windows.

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

### Show fork progress summary

```bash
python run_tuxemon.py --status
```

---

## Development Notes

- Core game code lives in `tuxemon/`
- Main bundled content is under `mods/tuxemon/`
- Tests are in `tests/`
- Sphinx docs are in `docs/`

Run tests with:

```bash
pytest
```

---

## Contributing to This Fork

Contributions are welcome. Suggested areas:

- Content balancing and encounter pacing
- Battle and status-effect mechanics
- Tooling and developer UX
- Documentation quality and onboarding

When opening changes, include:

- A short summary of the gameplay or tooling impact
- Test results (or clear rationale when tests are skipped)
- Any migration notes for saves/content if relevant

---

## Upstream Project

Tuxemon originated at:

- Website: <https://www.tuxemon.org>
- Upstream source: <https://github.com/Tuxemon/Tuxemon>

This fork keeps attribution and licensing aligned with the upstream GPLv3 project.

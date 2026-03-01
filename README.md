# OpenCapsuleMon (TuxemonV2 Fork)

OpenCapsuleMon is a free and open-source monster-battling RPG project evolving from the TuxemonV2 lineage.

This branch is focused on a clear product direction:

- **Gold/Silver-inspired adventure design**
- **Online tournaments**
- **Online casino + battle center**
- **Easy campaign maker for creators**
- **Polished rules and settings for fair, transparent play**

> Transition note: runtime command names and many internal package paths still use `tuxemon` for compatibility.

![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)

---

## Vision

OpenCapsuleMon aims to combine:

1. **Classic adventure feel** inspired by the depth, rhythm, and replayability associated with Gold/Silver-era monster RPG design.
2. **Modern online infrastructure** for competitive and social play.
3. **Creator-first tooling** so players can build and share complete campaigns without deep engine knowledge.
4. **Reliable rules and settings** that make gameplay expectations explicit in both solo and online modes.

If you want the execution details, read [`ROADMAP.md`](ROADMAP.md).

---

## Core Focus Areas

### 1) Gold/Silver-Inspired Features
- Time-aware gameplay loops (day/night/weekday impacts).
- Rematch and world-evolution progression loops.
- Strong post-game identity connecting campaign and online systems.

### 2) Online Tournaments
- Structured brackets, seasonal organization, and adjudication.
- Reconnect/no-show handling designed for real online operations.
- Clear player notifications for check-ins, pairings, and outcomes.

### 3) Online Casino + Battle Center
- Social online hubs for repeatable activities outside standard campaign routes.
- Casino systems with fairness and anti-abuse safeguards.
- Battle center support for quick matches, room play, and spectator-ready listing.

### 4) Easy Campaign Maker
- Guided workflows for maps, events, encounters, and progression.
- Validation-first UX to prevent broken campaigns before export.
- Template-driven onboarding for first-time creators.

### 5) Polished Rules and Settings
- Transparent rulesets and settings precedence.
- Presets for campaign, casual online, and tournament contexts.
- Deterministic behavior backed by regression testing.

---

## Quick Start

### Clone

```bash
git clone <your-fork-url>
cd TuxemonV2
```

### Install (editable)

```bash
python -m pip install -e . --no-build-isolation
```

### Run

```bash
python run_tuxemon.py
```

---

## Useful Commands

### Status Snapshot

```bash
python run_tuxemon.py --status
```

### Headless Run

```bash
python run_tuxemon.py --headless
```

### Load Save Slot

```bash
python run_tuxemon.py --load 1
```

### Map-Focused Debug Entrypoint

```bash
python run_tuxemon.py --test-map starting_town
```

### Custom Mod Directory

```bash
python run_tuxemon.py --mod /path/to/mod
```

---

## Development Layout

- Engine and game logic: `tuxemon/`
- Built-in content and gameplay data: `mods/`
- Tests: `tests/`
- Documentation: `docs/`

Run tests:

```bash
pytest -q
```

---

## Contributor Priorities (Current)

When contributing, prioritize changes that move one or more of these outcomes forward:

1. Gold/Silver-inspired campaign depth and replay loops.
2. Tournament operations stability and communication UX.
3. Battle center / casino systems with healthy economy controls.
4. Campaign maker ergonomics for non-programmer creators.
5. Rules/settings clarity, predictability, and documentation quality.

Include in your PR:

- Player-facing behavior summary
- Test or validation evidence
- Save/migration notes when behavior or schema changes
- Rule/settings impact notes when applicable

---

## Transition + Attribution

OpenCapsuleMon currently builds from TuxemonV2 and preserves upstream attribution and GPLv3 licensing obligations.

Tuxemon origins:

- Website: <https://www.tuxemon.org>
- Upstream source: <https://github.com/Tuxemon/Tuxemon>

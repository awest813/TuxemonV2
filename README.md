# OpenCapsuleMon

**OpenCapsuleMon** is a free and open-source monster-battling RPG built on the TuxemonV2 engine, combining Gold/Silver-era adventure depth with modern online tournaments, a battle center, an in-game-currency casino, and a creator-friendly campaign maker.

> **Transition note:** Runtime command names and internal package paths still use `tuxemon` for compatibility.

[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/downloads/)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](LICENSE)
[![Status: Beta](https://img.shields.io/badge/status-beta-green.svg)](ROADMAP.md)
[![Tests](https://github.com/awest813/TuxemonV2/actions/workflows/test.yml/badge.svg)](https://github.com/awest813/TuxemonV2/actions/workflows/test.yml)
[![Lint](https://github.com/awest813/TuxemonV2/actions/workflows/lint.yml/badge.svg)](https://github.com/awest813/TuxemonV2/actions/workflows/lint.yml)

---

## Overview

OpenCapsuleMon is an open-source monster RPG aiming to recreate the depth and replayability of classic monster-battling games while adding modern online infrastructure and creator-first tooling.

**What it solves:**
- Provides a fully open, moddable monster RPG platform with no paywalls or microtransactions.
- Gives competitive players structured online tournaments with real season management.
- Lets creators build complete campaigns using guided templates — no programming knowledge required.

**Who it is for:**
- **Players** who want a rich single-player monster RPG with online components.
- **Competitive players** who want organized brackets and seasonal ladders.
- **Creators** who want to build and share their own campaigns and mods.
- **Developers** who want to contribute to an open-source Python game engine.

---

## Features

- 🎮 **Gold/Silver-inspired adventure** — day/night cycles, weekday-aware events, rematch loops, and post-game progression
- 🏆 **Online tournaments** — structured brackets, seasonal ladders, reconnect handling, and adjudication tools
- 🎰 **Online casino + battle center** — social hubs powered by **in-game currency only** (no real money, no microtransactions)
- 🛠️ **Campaign maker** — guided creation flows, validation-first UX, and template-driven onboarding for creators
- 📜 **Polished rules & settings** — transparent clause sets, configurable presets, and regression-tested deterministic behavior
- 🌍 **Multi-language support** — localization via Babel with Weblate integration
- 🧩 **Mod system** — loadable content mods with YAML-driven data definitions
- 💾 **Save migration** — safe, tested upgrade paths between save file versions
- 🖥️ **Headless mode** — run the game as a server without a display

---

## Screenshots / Demo

> TODO: Add gameplay screenshots and/or demo GIF here.

---

## Project Architecture

OpenCapsuleMon is a Python game application built on `pygame-ce`. The main loop drives input, game logic, and rendering each frame. Networking and the CLI run alongside the main loop in supporting threads.

```
Player Input (keyboard / gamepad / mouse)
           |
     InputManager
           |
     EventManager  ──→  StateManager (push/pop/replace states)
           |                    |
     BaseClient           Active States (WorldState, CombatState, MenuState …)
      ├── MapManager
      ├── NPCManager
      ├── CombatEngine  ──→  Rules / Techniques / Items / Status Effects
      ├── NetworkManager ──→  Multiplayer / Tournaments / Battle Center / Casino
      ├── EconomyEngine
      └── CampaignManager ──→  Campaign Templates / Validation / Packaging
           |
     Renderer
      ├── StateDrawer (bottom-to-top state stack)
      └── MapRenderer (pyscroll + pytmx tile maps)
           |
     pygame-ce display surface
```

**Key subsystems:**

| Subsystem | Location | Purpose |
|---|---|---|
| Game Engine Core | `tuxemon/client.py`, `tuxemon/base_client.py` | Main loop, state orchestration |
| State Machine | `tuxemon/state.py`, `tuxemon/states/` | Game screen management |
| Combat System | `tuxemon/combat/` | Turn-based battle logic |
| Event Engine | `tuxemon/event/` | Scripted map/world events |
| Network Layer | `tuxemon/network/` | WebSocket multiplayer and tournament management |
| Map System | `tuxemon/map/` | Tiled map loading and rendering |
| Save System | `tuxemon/save.py`, `tuxemon/save_upgrader.py` | Persistence and migration |
| Campaign Tools | `tuxemon/campaign/` | Creator templates and validation |
| Economy | `tuxemon/economy/`, `tuxemon/money/` | In-game currency and anti-abuse controls |
| UI | `tuxemon/ui/`, `tuxemon/menu/` | Menus, HUD, and screen helpers |
| AI | `tuxemon/ai/`, `tuxemon/computer.py` | CPU trainer logic |

---

## Repository Structure

```
TuxemonV2/
├── run_tuxemon.py          # Main entry point — run the game from here
├── requirements.txt        # Python runtime dependencies
├── pyproject.toml          # Project metadata, build config, tool settings
├── tox.ini                 # Test / lint / format automation
├── Makefile                # Common developer commands
│
├── tuxemon/                # Engine and all game logic
│   ├── main.py             # pygame client initialization and main loop
│   ├── client.py           # LocalPygameClient — the playable game client
│   ├── headless_client.py  # HeadlessClient — server/CI mode
│   ├── combat/             # Turn-based battle engine
│   ├── event/              # Map scripting engine (actions, conditions, behaviors)
│   ├── network/            # WebSocket networking, tournaments, battle center
│   ├── campaign/           # Campaign creation framework and templates
│   ├── casino/             # Online casino (in-game currency only)
│   ├── economy/            # Currency policy and progression analysis
│   ├── rules/              # Battle clause sets and rule management
│   ├── states/             # All game screen states (world, combat, menus…)
│   ├── map/                # Tiled map loading, rendering, LRU cache
│   ├── monster/            # Monster data, stats, leveling, experience
│   ├── technique/          # Moves and abilities
│   ├── item/               # Inventory and items
│   ├── status/             # Status effects
│   ├── save.py             # Save/load logic
│   ├── save_upgrader.py    # Save migration between versions
│   ├── ai/                 # AI opponent logic
│   ├── ui/                 # UI helpers and widgets
│   └── ...                 # Additional modules (weather, time, factions, etc.)
│
├── mods/                   # Game content (maps, sprites, sounds, music, data)
│   └── tuxemon/            # Default built-in mod
│
├── tests/                  # Automated test suite (pytest)
│   └── tuxemon/            # Test modules mirroring tuxemon/ structure
│
├── docs/                   # Design specs, rulebooks, sprint notes
├── scripts/                # Developer utility scripts
├── buildconfig/            # Build configuration files
├── ARCHITECTURE_MAP.md     # Engine architecture reference
├── ROADMAP.md              # Phase-by-phase development roadmap
└── CONTRIBUTING.md         # Contributor guidelines
```

---

## Installation

### Requirements

- **Python 3.10, 3.11, 3.12, or 3.13**
- **pip** (included with Python)
- A system capable of running `pygame-ce` (Linux, macOS, or Windows)

On Linux you may need SDL2 system libraries:

```bash
# Debian / Ubuntu
sudo apt install libsdl2-dev libsdl2-image-dev libsdl2-mixer-dev libsdl2-ttf-dev
```

### Clone

```bash
git clone https://github.com/awest813/TuxemonV2.git
cd TuxemonV2
```

### Install Dependencies

Install in editable mode so that `tuxemon/` package changes take effect immediately:

```bash
python -m pip install -e . --no-build-isolation
```

Or install dependencies from `requirements.txt` directly:

```bash
pip install -r requirements.txt
```

Alternatively, use the Makefile shortcut:

```bash
make setup
```

---

## Running the Project

### Start the Game

```bash
python run_tuxemon.py
```

Or, after an editable install, use the registered command:

```bash
tuxemon
```

### Common Launch Options

| Command | Description |
|---|---|
| `python run_tuxemon.py` | Start the game normally |
| `python run_tuxemon.py --status` | Print a fork/pillar progress snapshot and exit |
| `python run_tuxemon.py --headless` | Run without a display (server or CI mode) |
| `python run_tuxemon.py --load 1` | Load save slot 1 on startup |
| `python run_tuxemon.py --test-map starting_town` | Jump directly to a named map for testing |
| `python run_tuxemon.py --mod /path/to/mod` | Load a custom mod directory instead of the default |
| `make run` | Launch via Makefile shortcut |

---

## Testing

The test suite uses **pytest**. All tests live under `tests/`.

### Run All Tests

```bash
pytest -q
```

### Run via Tox (recommended — matches CI)

```bash
tox -e py3        # Run tests
tox -e fmt        # Auto-format code (black + isort + autoflake + pyupgrade)
tox -e style      # Check code style without modifying files
tox -e lint       # Run flake8 linting
```

### Run via Makefile

```bash
make test         # Run tests via tox
make fmt          # Auto-format code
```

CI runs tests on Python 3.10, 3.11, 3.12, and 3.13 via GitHub Actions.

---

## Roadmap

OpenCapsuleMon is in **Beta (v0.5.0)**. Alpha exit was declared in March 2026 with all five pillars at baseline.

| Pillar | Status | Next Focus |
|---|---|---|
| **Adventure** (Gold/Silver depth) | ✅ Baseline complete | Post-credits progression polish |
| **Tournaments** (Competitive online) | ✅ Lobby/bracket/confirm live | Season operations UX + moderation tools |
| **Casino + Battle Center** | ✅ Core systems live | Anti-abuse telemetry, economy health monitoring |
| **Campaign Maker** | ✅ Validation + packaging live | Creator onboarding UX improvements |
| **Rules & Settings** | ✅ Context-aware clause sets live | Settings UI clarity + documentation |

Upcoming areas of focus:

- Tournament season operations and moderation tooling
- Campaign creator onboarding quality improvements
- Battle center spectator mode and matchmaking
- Performance and memory profiling
- Mobile UI readiness

See [`ROADMAP.md`](ROADMAP.md) for the full phase-by-phase plan.

---

## Contributing

Contributions are welcome! OpenCapsuleMon uses the **Fork & Pull** model.

### Quick Steps

1. **Fork** the repository on GitHub
2. **Clone** your fork locally
3. **Create a feature branch** from `development`:
   ```bash
   git checkout -b feature/your-feature-name development
   ```
4. **Make your changes** following the code guidelines below
5. **Run tests** and confirm nothing is broken:
   ```bash
   pytest -q
   ```
6. **Format your code:**
   ```bash
   tox -e fmt
   ```
7. **Open a Pull Request** targeting the `development` branch

### PR Checklist

- [ ] Targets the `development` branch
- [ ] Player-facing behavior is described in the PR body
- [ ] Tests pass (`pytest -q`)
- [ ] Code is formatted (`tox -e fmt`)
- [ ] Save/migration notes included if save schema changed
- [ ] Rules/settings impact noted if battle behavior changed

### Code Style

- Python files follow **PEP 8** with a 79-character line limit
- Use `black` and `isort` to format changed files
- New functions require docstrings
- Use `logging` for debug output — no bare `print()` statements

### Contributor Priorities

When choosing what to work on, prioritize:

1. Gold/Silver-inspired campaign depth and replay loops
2. Tournament operations stability and UX
3. Battle center / casino economy health (in-game currency only — no real money)
4. Campaign maker ergonomics for non-programmer creators
5. Rules/settings clarity, predictability, and documentation quality

For more details see [`CONTRIBUTING.md`](CONTRIBUTING.md).

---

## In-Game Economy Policy

> **The casino and all wager-based systems use in-game currency only.**

Coins and tokens are earned through gameplay (battles, exploration, quests, daily bonuses). There is no way to purchase, sell, or convert in-game currency using real money. No payment processor or external currency system is integrated at any layer.

This is a **hard design constraint**, not a configuration option. Any contribution that introduces a real-money pathway will be rejected.

---

## Frequently Asked Questions

**Q: Is this the same as Tuxemon?**
A: OpenCapsuleMon is a fork of TuxemonV2, which itself descends from the original [Tuxemon](https://github.com/Tuxemon/Tuxemon) project. It preserves all upstream attribution and the GPLv3 license while evolving toward a distinct product with online and creator features.

**Q: Why do commands and modules still say `tuxemon`?**
A: Runtime command names (`run_tuxemon.py`, `tuxemon` CLI) and Python package paths are kept for backward compatibility during the rebrand transition. See [`docs/rebrand_transition.md`](docs/rebrand_transition.md) for the staged migration plan.

**Q: Can I use real money in the casino?**
A: No. The casino is exclusively powered by in-game currency earned through gameplay. There are no microtransactions, no real-money purchases, and no external payment integrations — by design.

**Q: How do I create my own campaign?**
A: Use the campaign maker tools in `tuxemon/campaign/`. Template-based creation flows and validation tools guide you through maps, events, encounters, and progression. See `docs/campaign_maker_mvp.md` for details.

**Q: What Python versions are supported?**
A: Python 3.10, 3.11, 3.12, and 3.13.

---

## Troubleshooting

**Game does not start / pygame import error**
- Ensure `pygame-ce` is installed: `pip install pygame-ce==2.5.6`
- On Linux, install SDL2 system libraries (see [Installation](#installation))

**Map or asset loading errors**
- Confirm the `mods/` directory is present at the project root
- Try running with the default mod: `python run_tuxemon.py`

**Save file errors after updating**
- Save migration is automatic; if you encounter issues, check `tuxemon/save_upgrader.py`
- Open an issue with your save file version and the error message

**Tests fail on import**
- Run `python -m pip install -e . --no-build-isolation` to ensure the package is installed in editable mode

---

## License

OpenCapsuleMon is licensed under the **GNU General Public License v3.0 or later**.

See the [`LICENSE`](LICENSE) file for the full text.

---

## Credits

**OpenCapsuleMon** is built on the work of many contributors:

- **Original Tuxemon project** — [https://www.tuxemon.org](https://www.tuxemon.org) | [GitHub](https://github.com/Tuxemon/Tuxemon)
  - Founded by William Edwards (`shadowapex@gmail.com`) and the Tuxemon community
- **TuxemonV2 fork** — the intermediary branch this project evolves from
- **All contributors** — see [`CONTRIBUTORS.md`](CONTRIBUTORS.md)
- **Asset attributions** — see [`ATTRIBUTIONS.md`](ATTRIBUTIONS.md)

**Key open-source libraries:**

| Library | Purpose |
|---|---|
| [pygame-ce](https://pypi.org/project/pygame-ce/) | Graphics, input, and sound |
| [pyscroll](https://github.com/bitcraft/pyscroll) | Scrolling map rendering |
| [pytmx](https://github.com/bitcraft/pytmx) | Tiled map format loader |
| [pygame-menu-ce](https://pypi.org/project/pygame-menu-ce/) | UI menu system |
| [pydantic](https://docs.pydantic.dev/) | Data validation and schemas |
| [PyYAML](https://pyyaml.org/) | YAML configuration parsing |
| [websockets](https://websockets.readthedocs.io/) | WebSocket multiplayer networking |
| [Babel](https://babel.pocoo.org/) | Internationalization and localization |

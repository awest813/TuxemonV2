# Tuxemon Project Roadmap: Gold/Silver Feature Parity

This roadmap outlines the steps to achieve feature parity with Pokémon Gold/Silver, establishing a strong codebase foundation for future development.

## 1. Codebase Foundation & Quality

*   **Type Hinting (Mypy):**
    *   Achieve 100% type coverage for core modules (`tuxemon/core`, `tuxemon/monster`, `tuxemon/event`).
    *   Enforce strict type checking in CI.
*   **Code Style & Linting:**
    *   Resolve all `flake8` warnings.
    *   Maintain strict adherence to `black` and `isort`.
*   **Test Coverage:**
    *   Increase unit test coverage for complex logic (Battles, AI, Event System).
    *   Add integration tests for key gameplay loops (Catching, evolving, trading).
*   **Documentation:**
    *   Document public APIs using docstrings.
    *   Update Sphinx documentation to reflect current architecture.

## 2. Core Gameplay Features (Gold/Silver Parity)

### 2.1. Time System
*   **Visuals:** Implement dynamic map tinting for Day/Night/Morning/Dusk.
*   **Encounters:** Differentiate wild encounters based on time of day.
*   **Events:** Implement daily and weekly events (e.g., Bug Catching Contest, Gym Leader rematches).

### 2.2. Held Items
*   **Battle Usage:** Implement logic for items to trigger in battle (e.g., Berries healing HP when low).
*   **Pickup:** Implement ability/mechanic to find items after battle.

### 2.3. Breeding
*   **Egg Groups:** Define and implement egg groups for all Tuxemon.
*   **Daycare:** Implement Daycare logic for leaving two Tuxemon.
*   **Inheritance:** Implement logic for passing down Moves (Egg Moves) and IVs (Stats).
*   **Hatching:** Implement step-based egg hatching mechanic.

### 2.4. Friendship/Happiness
*   **Mechanics:** Fully integrate happiness value tracking.
*   **Modifiers:** Implement events that affect happiness (Walking, Fainting, Vitamins, Grooming, Trading).
*   **Evolution:** Ensure happiness-based evolution is fully functional (e.g., specific time + high happiness).

### 2.5. Special Stat Split
*   **Evaluation:** Evaluate if splitting `Ranged` (Sp. Atk) into Sp. Atk and Sp. Def is necessary for balance, or if `Armour` and `Dodge` suffice.
*   **Implementation:** If splitting, update database schema and battle formulas.

### 2.6. Shiny Tuxemon
*   **Mechanics:** Implement shiny calculation logic (1/8192 chance or similar).
*   **Visuals:** Support alternate color palettes/sprites for shiny forms.

### 2.7. Pokerus
*   **Mechanics:** Implement viral infection spreading in party.
*   **Effect:** Double EV/Stat Experience gain.

### 2.8. Berries & Apricorns
*   **Growth:** Implement a time-based soil/growth system for Berries.
*   **Crafting:** Implement a crafting system for Apricorn Balls (Kurt).

### 2.9. Phone/Pokegear
*   **Registration:** Ability to register Trainer numbers.
*   **Rematches:** System for trainers to call for rematches or report swarms.

### 2.10. Two Regions (Post-Game)
*   **Map Linking:** Ensure seamless travel between two distinct regions (e.g., train/boat events).
*   **Scaling:** Implement level scaling for post-game trainers and wild encounters.

## 3. Content & Data

*   **Database:** Update monster database with new stats, types (Steel/Dark equivalents), and move sets.
*   **Maps:** Design and implement maps for the second region.
*   **Scripting:** Write scripts for new events and story arcs.

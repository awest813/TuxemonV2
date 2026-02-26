# Tuxemon Game Design Document

## 1. Game Overview

**Title:** Tuxemon
**Genre:** Monster-Taming RPG
**Perspective:** Top-down 2D (Pixel Art)
**Target Audience:** All ages, fans of classic monster-catching games.
**Engine/Tech:** Python, Pygame-ce, PyTMX.

### 1.1. High Concept
Tuxemon is an open-source, community-driven monster-fighting RPG. Players explore a vibrant world, capture "Tuxemon," train them, and battle other trainers to become the ultimate champion. The game aims to capture the spirit of the 2nd Generation of similar games (Gold/Silver/Crystal) while providing a modern, moddable open-source foundation.

### 1.2. Core Loop
1.  **Explore:** Traverse maps, interact with NPCs, solve puzzles, and find items.
2.  **Encounter:** Find wild Tuxemon in tall grass, caves, or water.
3.  **Combat:** Battle wild Tuxemon or other trainers using a turn-based system.
4.  **Growth:** Gain experience, level up, learn new moves, and evolve.
5.  **Collect:** Catch new species to complete the Tuxepedia.

---

## 2. Gameplay Mechanics

### 2.1. The Player
*   **Movement:** Grid-based movement (Up, Down, Left, Right). Sprinting is available.
*   **Interaction:** 'Action' button to talk to NPCs, pick up items, or inspect objects.
*   **Inventory:** A bag system separated into categories (Items, Medicine, Key Items, Tuxeballs, TMs).

### 2.2. Tuxemon
Each monster is defined by:
*   **Stats:**
    *   **HP (Hit Points):** Health. Faints at 0.
    *   **Melee:** Physical attack power.
    *   **Ranged:** Special/Ranged attack power.
    *   **Armour:** Physical defense.
    *   **Dodge:** Special/Ranged defense and evasion.
    *   **Speed:** Determines turn order.
*   **Types:** Elemental affinities (e.g., Fire, Water, Earth) that determine weaknesses and resistances.
*   **Moveset:** Can learn up to 4 techniques. New moves are learned via level-up, TMs, or breeding.
*   **Evolution:** Most Tuxemon can evolve into stronger forms based on Level, Items, Stones, or Happiness.

### 2.3. Combat System
*   **Format:** 1v1 Turn-Based Battles.
*   **Flow:**
    1.  **Selection:** Player chooses Fight, Bag, Tuxemon (Swap), or Run.
    2.  **Move Selection:** If Fight is chosen, select one of 4 moves.
    3.  **Execution:** The monster with the higher Speed acts first (usually). Priority moves can override this.
    4.  **Damage Calculation:** Based on Power, Attack Stat (Melee/Ranged), Defense Stat (Armour/Dodge), Type Effectiveness, and Random Variance.
    5.  **Status Effects:**
        *   *Poison:* Damage over time.
        *   *Burn:* Damage over time + lowers Attack.
        *   *Sleep:* Cannot move for 1-3 turns.
        *   *Paralysis:* Chance to not move + lowers Speed.
        *   *Freeze:* Cannot move until thawed.
*   **Winning:** Reduce enemy HP to 0. Awards XP and Money.
*   **Losing:** All party members faint. Player blacks out and returns to last healing center.

### 2.4. Catching System
*   **Tuxeballs:** Items used to capture wild monsters.
*   **Mechanic:** Probability based on:
    *   Target's Max HP vs Current HP (Lower is better).
    *   Target's Status Conditions (Sleep/Freeze > Paralyze/Poison/Burn).
    *   Catch Rate of the species.
    *   Quality of the Ball used.

### 2.5. Time & Day/Night Cycle
*   **Real-time Clock:** The game tracks real-world time or a simulated cycle.
*   **Visuals:** Map tints change (Morning, Day, Dusk, Night).
*   **Gameplay Impact:**
    *   Specific wild encounters only appear at Night or Morning.
    *   Some events (shops, NPCs) may only be active at certain times.
    *   Evolutions may depend on time of day (e.g., Eevee-like branches).

---

## 3. World & Setting

### 3.1. The Region
A varied region featuring:
*   **Towns/Cities:** Safe hubs with Centers (Healing), Marts (Shops), and Gyms.
*   **Routes:** Paths connecting towns, filled with wild encounters and trainers.
*   **Dungeons:** Caves, Forests, Power Plants, or Abandoned Buildings.

### 3.2. Organizations
*   **The League:** The governing body of trainers. Requires collecting Badges to challenge the Elite.
*   **The Antagonists:** A team or group creating conflict (stealing monsters, disrupting nature, etc.).

---

## 4. Systems Design

### 4.1. Technical Architecture
*   **Language:** Python 3.10+
*   **Framework:** Pygame Community Edition (pygame-ce).
*   **Data Storage:** JSON/YAML for static data (Monsters, Moves, Items). Save files use JSON.
*   **Map Format:** Tiled Map Editor (.tmx).

### 4.2. Event System
A scripting engine handles game logic:
*   **Conditions:** Checks if a variable is set, if player has an item, etc.
*   **Actions:** Dialogues, movement, giving items, starting battles, playing sounds.
*   **Triggers:** On Interact, On Step (Touch), Autorun (On Map Load).

---

## 5. UI/UX

*   **Dialogue Box:** Text appears at the bottom of the screen. Supports avatars/faces.
*   **Menus:** Nested list-based menus (Start Menu -> Bag -> Item).
*   **Battle Interface:**
    *   HUD showing HP/XP bars, Names, and Levels.
    *   Command window for actions.
    *   Attack animations overlaid on sprites.

---

## 6. Future Roadmap (Gold/Silver Parity)

*   **Breeding:** Daycare center mechanics for passing down moves/stats.
*   **Held Items:** Items that trigger effects in battle (Berries).
*   **Shiny Variants:** Rare alternate color palettes.
*   **Two Regions:** Post-game content allowing travel to a new map.
*   **Phone/Gear:** Rematch system and NPC calls.

# Tuxemon vs Pokémon Gold/Silver: Feature Gap Snapshot

This document compares the current Tuxemon feature surface (based on project roadmap and visible game systems in the codebase) with the feature expectations players usually associate with Pokémon Gold/Silver.

## 1) Current baseline (high-confidence from repository)

From the public roadmap, these systems are already marked implemented:

- Breeding / egg hatching
- Day / night cycle
- Fishing
- Weather

The roadmap also marks these as planned:

- Advanced breeding mechanics
- Online trading
- Multiplayer battles

In-game state modules and tests also show active support for:

- PC/box-like management (`pc`, `pc_kennel`, `pc_locker`)
- Phone features (`phone`, `phone_contacts`, `phone_radio`, `phone_map`, `phone_banking`)
- Monster journal / dex-like tracking (`journal_state`, `journal_info`, `tuxepedia` tests)
- Save/load + world + combat + mission + economy systems

## 2) Gold/Silver feature parity matrix

Legend:

- **Likely Present**: clearly represented in roadmap/system layout.
- **Partial / Needs Depth**: feature scaffolding appears present but likely needs GS-like depth/polish.
- **Likely Missing / Unclear**: not obvious from roadmap + surface scan.

### Core progression

- Gym challenge + badge progression: **Partial / Needs Depth**
- Elite Four + Champion loop: **Partial / Needs Depth**
- Postgame region-scale expansion (GS had Kanto): **Likely Missing / Unclear**
- Story event cadence comparable to Team Rocket arcs: **Partial / Needs Depth**

### Time-and-world identity (major GS strength)

- Day/night encounters and schedule logic: **Likely Present, needs tuning depth**
- Weekday/time events (e.g., timed NPCs, shops): **Partial / Needs Depth**
- Dynamic radio + map identity by region: **Partial / Needs Depth**
- Distinct "world clock" gameplay loops: **Partial / Needs Depth**

### Monster systems

- Breeding + eggs: **Present**
- Advanced breeding (inheritance rules, optimization loops): **Planned / Partial**
- Friendship/happiness evolutions and behavior: **Likely Missing / Unclear**
- Held item identity and battle utility depth: **Partial / Needs Depth**
- Evolution variety parity (stones, trade, friendship, time): **Partial / Needs Depth**

### Combat and metagame depth

- Battle flow + capture + progression: **Present**
- Battle facility equivalent (Battle Tower-like repeatable challenge): **Likely Missing / Unclear**
- Broad encounter archetypes (trainers, optional duels, rematches): **Partial / Needs Depth**
- AI and roster sophistication to GS-level replayability: **Partial / Needs Depth**

### Social systems

- Phone-contact ecosystem (calls, rematches, events): **Partial / Needs Depth**
- Trading: **Planned**
- Multiplayer battling: **Planned**

### Side activities and collectability

- Fishing: **Present**
- Contest/minigame equivalents (Bug-Catching Contest style loops): **Partial / Needs Depth**
- Collectibles and encyclopedic completion loop: **Present, likely needs milestone rewards**
- Crafting/economy systems (Tuxemon-specific): **Present (can be differentiator)**

## 3) What "matching Gold/Silver" means in practice

To feel GS-complete to players, Tuxemon should prioritize:

1. **Time-based world reactivity** (day/night + weekday NPC schedules + event windows).
2. **Phone ecosystem depth** (calls that matter: rematches, item tips, rare encounter alerts).
3. **Post-credits longevity** (second-region equivalent OR substantial postgame arc).
4. **Repeatable challenge pillar** (tower/facility with scaling rewards).
5. **Breeding/evolution depth** (inheritance, friendship, held-item + time evolutions).

## 4) Recommended delivery roadmap (GS parity-oriented)

### Milestone A — "GS Identity"

- Expand time/day-week event scripting hooks and map-level schedules.
- Finish radio/phone loops so they materially change route choice and rematches.
- Add at least one recurring weekly event activity.

### Milestone B — "GS Replayability"

- Deliver advanced breeding mechanics (already on roadmap).
- Implement friendship/happiness and tie to evolutions + move interactions.
- Add a Battle Tower-style ruleset/facility with rank progression.

### Milestone C — "GS Longevity"

- Ship online trading + multiplayer battles (already on roadmap).
- Add postgame expansion arc (region-scale content or equivalent chapter).
- Add durable completion incentives (journal milestones, rare unlocks, economy sinks).

## 5) Suggested success metrics

Track parity progress with measurable targets:

- % of routes with time-dependent encounter/availability changes.
- # of meaningful phone call triggers per in-game week.
- Postgame playtime median after credits.
- # of viable repeatable challenge formats (tower/contest/rematch ladders).
- % of monster evolutions using non-level methods (item/time/friendship/trade).

## 6) Bottom line

Tuxemon already has several **GS-adjacent foundation systems** (time, breeding/eggs, fishing, weather, phone/radio scaffolding). The biggest gap to "feels like Gold/Silver" is less about raw mechanics count and more about **depth, interconnectedness, and postgame longevity**.

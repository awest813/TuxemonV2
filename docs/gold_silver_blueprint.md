# Gold/Silver-Inspired Design Blueprint

## Document Status

- Status: Published (Phase 1)
- Scope: Day/night and weekday event cadence, rematch loops, mandatory engine hooks, and post-game identity milestones

---

## 1. Purpose and Design Intent

Pokémon Gold/Silver is the canonical reference for a monster-RPG that feels *alive* after its credits roll. The three properties that made it distinctive:

1. **World-clock identity** — The world reacted to the real-time clock. Day, night, and specific weekdays changed what was available, who appeared, and what happened.
2. **Rematch loop depth** — Trainers called back, rematches scaled, and the phone ecosystem kept the overworld meaningful after the main story ended.
3. **Post-game longevity** — An entire second region with its own gym sequence, rival escalation, and final boss gave players 40+ hours of directed post-game content.

OpenCapsuleMon's goal is not to copy Gold/Silver but to capture the *design intention* behind those properties using our open content pipeline. This blueprint defines what that means concretely.

---

## 2. Day/Night and Weekday Event Cadence

### 2.1 Time Segments

The engine already exposes `TimeHandler` with real-world time. The content system must be able to schedule events and encounters against the following segments:

| Segment | Hours (local) | Token |
|---|---|---|
| Dawn | 04:00–07:59 | `dawn` |
| Morning | 08:00–11:59 | `morning` |
| Afternoon | 12:00–15:59 | `afternoon` |
| Dusk | 16:00–19:59 | `dusk` |
| Night | 20:00–03:59 | `night` |

Day/night binary:
- **Day:** `dawn`, `morning`, `afternoon`, `dusk` (06:00–17:59)
- **Night:** `night` (18:00–05:59)

Seasons: `spring`, `summer`, `autumn`, `winter` (hemisphere-aware, already implemented).

Weekdays: `monday` through `sunday`.

### 2.2 Encounter Time Gates

Any encounter table entry must support optional time restrictions:

```yaml
# Example encounter table entry
- monster: "porcupinito"
  weight: 10
  time_restrictions:
    - "night"         # only spawns at night
  season_restrictions:
    - "winter"        # only in winter
  weekday_restrictions:
    - "friday"        # only on Fridays
    - "saturday"
```

Encounter resolution priority:
1. Check active zone-level time restrictions (mod override).
2. Check individual encounter entry restrictions.
3. Entries with no restrictions are always eligible.

### 2.3 NPC Scheduling

NPCs must support a schedule block that controls:

- **Presence:** Whether the NPC appears on the map.
- **Position:** Where the NPC stands or walks.
- **Dialogue:** Which script runs when the player talks to them.
- **Shop inventory:** Which items are stocked (for time-specific merchants).

```yaml
# Example NPC schedule definition
npc: "pepper_trader"
schedules:
  - days: ["monday", "wednesday", "friday"]
    time: ["morning", "afternoon"]
    position: [15, 22]
    dialogue: pepper_trader_market_open
    shop_inventory: pepper_market_stock
  - days: ["saturday", "sunday"]
    time: ["dawn", "morning", "afternoon", "dusk"]
    position: [8, 14]
    dialogue: pepper_trader_weekend
    shop_inventory: pepper_weekend_stock
  - time: ["night"]
    present: false    # NPC disappears at night
```

### 2.4 Weekly Event Calendar

Each mod/campaign may define a weekly event calendar. Events fire once per matching time window and reset weekly:

```yaml
weekly_events:
  - id: "bug_catching_contest"
    name_key: "event_bug_catching_contest"
    days: ["tuesday", "thursday", "saturday"]
    time: ["morning", "afternoon"]
    map: "national_park"
    trigger_script: "start_bug_contest"
    reward_script: "award_bug_contest"

  - id: "farmers_market"
    name_key: "event_farmers_market"
    days: ["sunday"]
    time: ["morning", "afternoon", "dusk"]
    map: "goldenrod_market_square"
    trigger_script: "open_farmers_market"
```

Fired events are tracked by their `id` in the player's world state. A fired event within its active window does not fire again until the next eligible window.

### 2.5 Day/Night Visual Layer

Map layers prefixed with `day_` are hidden during night; layers prefixed with `night_` are hidden during day. The lighting system should blend between them over a configurable transition duration centered at dawn/dusk boundaries.

---

## 3. Rematch Loop Architecture

### 3.1 Trainer State Model

Each trainer in the world has a persistent state that the engine tracks:

| Field | Type | Description |
|---|---|---|
| `trainer_id` | str | Stable identifier matching the NPC definition. |
| `defeated` | bool | True after the player wins the first encounter. |
| `last_rematch_at` | datetime or None | Timestamp of the most recent rematch. |
| `rematch_count` | int | Number of rematches completed. |
| `rematch_eligible` | bool | Whether the trainer's rematch policy is active. |

### 3.2 Rematch Eligibility Rules

A trainer becomes rematch-eligible when:

1. `defeated` is `True`.
2. The player has achieved a configured badge/milestone threshold (set per trainer).
3. The trainer's `rematch_policy` is `enabled` (see `docs/rulebook_spec.md §2.2`).

A rematch is available (ready to initiate) when:

1. Trainer is rematch-eligible.
2. The trainer is currently present on the map (schedule check passes).
3. A minimum cooldown period since `last_rematch_at` has elapsed (default: 24 real hours, configurable per trainer).

### 3.3 Phone-Initiated Rematches

When rematch conditions are met, trainers with a phone contact entry may call the player:

- Call frequency: at most once per in-game day per trainer.
- Call content: contextual (can offer rematch, share item tip, or trigger rare encounter hint).
- Rare encounter hint calls unlock a timed window (current in-game day) where a normally-hidden monster appears on a specific route.

Phone contact call script template:

```
[trainer_name] calls... 
"Hey [player]! I've been training hard. Want a rematch?"
> Accept → schedule rematch at trainer's location.
> Decline → trainer calls again after 3 in-game days.
```

### 3.4 Rematch Team Scaling

Trainer roster at each rematch is determined by `rematch_level_policy`:

- `static` — No change from the original encounter roster.
- `scaled` — Each monster's level set to `max(original_level, player_top_level * scale_factor)`. Default `scale_factor`: 0.9.
- `authored` — Mod author provides explicit `rematch_roster_N` entries for N = 1, 2, 3…

Maximum authored rematch slots per trainer: 5. Beyond 5, the most recent authored slot is repeated with `scaled` policy.

---

## 4. Mandatory Engine Hooks

The following hooks must be added to the engine to support the above cadence and loop design. Each hook is a defined interface that game-logic systems call; content scripts register handlers against them.

### Hook 4.1 — `on_time_segment_change`

**Trigger:** When the active time segment transitions (e.g., `morning` → `afternoon`).
**Payload:** `{ previous_segment, new_segment, current_time }`
**Use cases:** Switch NPC schedules, toggle encounter table sets, update map layers.

### Hook 4.2 — `on_day_change`

**Trigger:** At midnight (00:00) each day.
**Payload:** `{ previous_date, new_date, weekday }`
**Use cases:** Reset daily events, increment trainer cooldowns, trigger weekly event eligibility refresh.

### Hook 4.3 — `on_map_zone_enter`

**Trigger:** When the player transitions into a new map zone.
**Payload:** `{ zone_id, player_id, current_time_snapshot }`
**Use cases:** Apply zone-level encounter rate/time overrides, trigger NPC scheduling evaluation for the zone.

### Hook 4.4 — `on_encounter_table_query`

**Trigger:** Before each wild encounter roll.
**Payload:** `{ zone_id, current_time_snapshot, player_party }`
**Returns:** Filtered encounter table (after time/season/weekday gates applied).
**Use cases:** Gate encounter eligibility, inject time-limited rare encounters triggered by phone calls.

### Hook 4.5 — `on_trainer_defeated`

**Trigger:** Immediately after the player wins a trainer battle.
**Payload:** `{ trainer_id, player_id, timestamp }`
**Use cases:** Set `defeated = True` on trainer state, check milestone conditions, trigger first-defeat rewards.

### Hook 4.6 — `on_rematch_eligible`

**Trigger:** When a trainer transitions to rematch-eligible status (milestone threshold crossed after defeat).
**Payload:** `{ trainer_id, player_id }`
**Use cases:** Add trainer to the phone contact call pool, enable rematch dialogue in NPC script.

### Hook 4.7 — `on_weekly_event_window_open`

**Trigger:** When a weekly event's active window begins.
**Payload:** `{ event_id, zone_id, current_time_snapshot }`
**Use cases:** Activate event-specific map layers, spawn event NPCs, open timed encounter tables.

### Hook 4.8 — `on_weekly_event_window_close`

**Trigger:** When a weekly event's active window ends.
**Payload:** `{ event_id, zone_id }`
**Use cases:** Deactivate event map layers, despawn event NPCs, close timed encounter tables.

### Hook 4.9 — `on_postgame_milestone_reached`

**Trigger:** When the player achieves a post-game milestone (see §5).
**Payload:** `{ milestone_id, player_id, timestamp }`
**Use cases:** Unlock new regions or content blocks, update the journal/dex with postgame categories.

---

## 5. Post-Game Identity Milestones

Post-game identity is the answer to "what is there to do after the credits roll?" Each milestone is a discrete, trackable achievement that unlocks content or deepens existing systems.

### 5.1 Milestone Tier Structure

| Tier | Name | Unlocked By |
|---|---|---|
| 0 | Story Complete | Credits roll after final boss. |
| 1 | Returner | Complete first rematch against any gym-equivalent trainer. |
| 2 | Battler | Win 10 rematches across any trainers. |
| 3 | Champion Challenger | Win a tournament bracket OR reach top-10 in casual ladder (if applicable). |
| 4 | Completionist | Reach 80%+ monster journal/dex completion. |
| 5 | Grand Champion | Complete Battle Tower-equivalent facility at maximum difficulty. |

### 5.2 Milestone Acceptance Criteria

For each milestone to be marked complete in ROADMAP.md, ALL of the following must be true:

**Tier 0 — Story Complete**
- [ ] Engine fires `on_postgame_milestone_reached` with `milestone_id="story_complete"` when the final boss battle ends and the ending sequence begins.
- [ ] Journal/dex UI marks the story arc as complete.
- [ ] Save file records `story_complete = true` in world state.

**Tier 1 — Returner**
- [ ] At least 5 trainers in the base campaign have authored rematch rosters or `scaled` rematch policy.
- [ ] Phone contact system is live and at least 3 trainers participate in it.
- [ ] The milestone fires after the first rematch win is recorded in trainer state.

**Tier 2 — Battler**
- [ ] Cumulative rematch counter is persisted in save.
- [ ] Milestone fires when counter reaches 10.
- [ ] A player-visible milestone tracker UI element exists (journal or achievement page).

**Tier 3 — Champion Challenger**
- [ ] Online tournament system reaches Phase 3 (UX complete) — tracked in `docs/online_tournaments_roadmap.md`.
- [ ] Milestone fires when tournament champion event is received OR casual ladder threshold recorded.

**Tier 4 — Completionist**
- [ ] Monster journal/dex has a percentage-completion field in save state.
- [ ] Milestone fires when field reaches 80%.
- [ ] Reaching 100% unlocks an authored in-game reward item or title.

**Tier 5 — Grand Champion**
- [ ] Battle Tower equivalent facility exists with at least 5 difficulty tiers.
- [ ] Milestone fires when the player's facility rank record equals tier 5.
- [ ] Facility integrates with tournament ruleset (same clauses enforced).

### 5.3 Post-Game Content Gates

Milestones gate access to post-game content using the world state system:

| Content | Required Milestone |
|---|---|
| Second region / expanded postgame map | Tier 0 (story complete) |
| Elite trainer rematches (highest tier rosters) | Tier 2 (battler) |
| Legendary / ultra-rare encounter windows | Tier 4 (completionist) |
| Special cosmetic rewards | Tier 5 (grand champion) |

---

## 6. Implementation Priority

For Phase 1 delivery, the following items are the minimum required to move Phase 2 forward:

1. **Hook interfaces defined** in `tuxemon/time_hooks.py` — all 9 hooks as Python protocols/callables.
2. **Encounter table time/season/weekday filtering** wired into the encounter resolution path.
3. **Trainer state model** extended with `last_rematch_at`, `rematch_count`, `rematch_eligible`.
4. **Weekly event calendar schema** defined and documented (YAML format above).
5. **Milestone acceptance criteria** authored for Tiers 0–5 (this document, §5.2).

Phase 2 implements these hooks against live content; Phase 4 delivers the content itself.

# OpenCapsuleMon Rulebook Specification

## Document Status

- Status: Published (Phase 1)
- Scope: Battle rules and gameplay settings for all three play contexts
- Supported contexts: Campaign, Casual Online, Tournament

---

## Overview

This document defines the canonical ruleset for each play context in OpenCapsuleMon. All contexts share a common rule vocabulary; differences are expressed as overrides applied on top of the default base rules.

Play contexts:

| Context | Description | Audience |
|---|---|---|
| **Campaign** | Single-player story progression through the mod's authored content | Solo players |
| **Casual Online** | Unranked player-vs-player battles without stakes or records | Friends, drop-in play |
| **Tournament** | Structured seasonal competitive play with brackets and adjudication | Competitive community |

---

## 1. Base Battle Rules (All Contexts)

These rules apply in every context unless explicitly overridden.

### 1.1 Team Composition

- Maximum team size: **6 monsters**.
- Minimum team size to enter battle: **1 monster**.
- Fainted monsters count toward team size but cannot participate.

### 1.2 Monster Levels

- Monsters participate at their current level unless a **level cap** is active (see context overrides).
- Level cap is enforced by scaling stats at battle start; underlying level and XP are not modified.

### 1.3 Turn Timer

- By default, no turn timer is enforced in campaign and casual contexts.
- Timer is context-specific; see overrides below.

### 1.4 Clauses (Default: None Active)

Clauses are opt-in restrictions that limit team composition or strategy. The following clause vocabulary is supported:

| Clause ID | Description |
|---|---|
| `duplicate_species` | No two monsters on a team may share the same species. |
| `duplicate_item` | No two monsters may hold the same item. |
| `sleep_limit` | Only one opposing monster may be asleep at a time. |
| `ohko_ban` | One-hit-KO techniques are disallowed. |
| `evasion_limit` | Evasion-raising moves can only be used once per battle. |
| `self_ko_draw` | When the last surviving monsters on both sides faint simultaneously, the result is a draw (requires admin adjudication in tournaments). |

Default active clauses by context:

| Context | Active Clauses |
|---|---|
| Campaign | *(none — unrestricted)* |
| Casual Online | *(none — host-configurable)* |
| Tournament | `duplicate_species`, `self_ko_draw` |

Optional clauses by context (legal but not active by default):

| Context | Optional Clauses |
|---|---|
| Campaign | `duplicate_species` |
| Casual Online | `duplicate_species`, `duplicate_item`, `sleep_limit`, `ohko_ban`, `evasion_limit`, `self_ko_draw` |
| Tournament | `duplicate_item`, `sleep_limit`, `ohko_ban`, `evasion_limit` |

### 1.5 Battle Result Finality

- A battle result is final when the authoritative battle session records a winner or draw.
- Results must be persisted immediately and are immutable after settlement.
- Idempotent re-submission of the same result token is a no-op (not an error).

---

## 2. Campaign Context Rules

Campaign battles follow the narrative intent of the mod author. The rulebook defines constraints that override player config where needed.

### 2.1 Difficulty Presets

| Preset | Level Cap | Clauses | Trainer AI Depth |
|---|---|---|---|
| `easy` | None | None | 1 (random) |
| `normal` | None | None | 2 (basic) |
| `hard` | None | None | 3 (strategic) |
| `challenge` | None | `duplicate_species` | 4 (optimal) |

Default preset: `normal`. The active preset is set by the player at campaign start and may be changed at save points (mod author may restrict this).

### 2.2 Trainer Rematches

- Trainers whose `rematch_policy` is `enabled` may be re-challenged after the player has reached a configurable badge/milestone threshold.
- Rematch teams scale according to the trainer's `rematch_level_policy`:
  - `static` — team does not change.
  - `scaled` — team scales to a fixed percentage above the player's strongest monster level.
  - `authored` — mod author supplies a second explicit roster.

### 2.3 Wild Encounter Rates

- Base rate is `1.0` (full rate as authored by the mod).
- Player config `encounter_rate_modifier` multiplies this value (range `0.0–2.0`).
- Mod/campaign overrides may clamp or pin the modifier per map zone.

### 2.4 Campaign-Only Rules

- **Permadeath** (optional): If the `permadeath` campaign flag is enabled, fainted monsters cannot be revived; they are permanently lost.
- **Nuzlocke mode** (optional): Only the first monster encountered on each map zone may be caught.

---

## 3. Casual Online Context Rules

Casual online battles are player-initiated, unranked, and have minimal enforcement. The connecting host player controls most settings.

### 3.1 Host-Configurable Parameters

| Parameter | Allowed Range | Default |
|---|---|---|
| `team_size` | 1–6 | 6 |
| `level_cap` | None or 10–100 | None |
| `turn_timer_seconds` | 0 (disabled) or 15–300 | 0 |
| `active_clauses` | Any subset of clause vocabulary | `[]` |
| `allow_items_in_battle` | bool | `true` |
| `allow_held_items` | bool | `true` |

### 3.2 Joining Player Rights

- Joining players may decline and leave the session without penalty.
- Joining players see a pre-match rules snapshot containing: baseline defaults for the selected context, resolved final values, and a field-level difference list before confirming the match.
- Disconnecting during battle: no forced result; battle is abandoned.

### 3.3 Result Recording

- Results are recorded locally for personal stats only.
- No global ladder or rating is affected by casual results.

---

## 4. Tournament Context Rules

Tournament rules are the most restrictive and are admin-governed. They extend the base rules with enforcement and adjudication.

### 4.1 Format (v1)

- **Bracket type:** Single elimination.
- **Bracket sizes:** 8 or 16 players.
- **Byes:** Assigned deterministically from seeding order when bracket cannot be filled.

### 4.2 Eligibility

- Player must have a valid team of at least the configured `team_size`.
- Player must have an active online session at registration close.
- A single player account may not register more than once per tournament.

### 4.3 Check-in Policy

- Check-in opens when registration closes.
- Players who do not check in before the deadline are removed before bracket generation.
- If checked-in players fall below minimum viable size (8 for v1), the tournament is cancelled.

### 4.4 Seeding

- Deterministic PRNG using a captured `tournament_seed` value.
- Tie-break order: registration timestamp ascending, then stable player ID sort.
- Seed and tie-break metadata are persisted for replay/debug.

### 4.5 Match Rules (Default v1)

| Parameter | Value |
|---|---|
| Team size | 6 |
| Level cap | 50 |
| Turn decision timer | 60 seconds |
| Reconnect grace period | 90 seconds |
| Active clauses | `duplicate_species`, `self_ko_draw` |
| Items in battle | Allowed (host may restrict in custom tournaments) |

### 4.6 Result and Advancement

- Winner determined by authoritative battle session result.
- Match result ingestion is idempotent (tied to unique match resolution token).
- Winner auto-advances to next bracket node.
- Final winner declared champion when the championship match resolves.

### 4.7 No-show and Disconnect Policy

| Scenario | Resolution |
|---|---|
| Player fails readiness check before timeout | No-show loss; opponent advances. |
| Both players fail readiness check | Match paused for admin adjudication. |
| Disconnect during active match (within grace period) | Battle paused; reconnect allowed. |
| Disconnect exceeds reconnect grace | Disconnecting player forfeits (unless admin override). |

### 4.8 Admin/Moderation Actions

- **Force-report result** — Admin may set the winner of any match.
- **Disqualify participant** — Remove a player; their remaining scheduled opponents advance.
- **Pause/resume tournament** — Halt all match scheduling without cancelling the event.
- **Cancel tournament** — Cancel with reason broadcast to all registered players.

---

## 5. Rule Precedence Summary

When a rule value is resolved, the following precedence order applies (highest to lowest):

1. **Mod/campaign override** — Hardcoded by the mod author for a specific zone or story event.
2. **Tournament/host config** — Set by the tournament admin or the session host.
3. **Player config** — Set by the player in their personal settings.
4. **Base rulebook default** — Defined in this document.

A layer may only override keys it is authorized to touch (see `docs/settings_taxonomy.md`).

---

## 6. Open Questions

1. Should `level_cap` enforcement in casual online clip stats or prevent participation?
2. Should the `self_ko_draw` clause require immediate admin action or allow a post-match dispute window?
3. Should casual online results feed an optional opt-in public board (separate from ranked ladder)?

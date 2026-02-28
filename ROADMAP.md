# OpenCapsuleMon Roadmap (TuxemonV2 Transition)

This roadmap reflects the current state of the branch and outlines practical follow-up work as TuxemonV2 begins rebranding to **OpenCapsuleMon**.

## Status Overview

- Overall checklist completion: **29/29** (all alpha-gate milestones complete)
- Snapshot command: `python run_tuxemon.py --status`
- Rebrand phase: **Phase A complete** (documentation and messaging aligned; compatibility-first migration policy published)
- Latest recorded status during this update:
  - Branch `work`, commit `faff3a3c`
  - Monsters 411, Techniques 274, Items 221, NPCs 122, Maps 224, Localizations 14

---

## Completed Milestones

### Core Gameplay Systems
- [x] Breeding / Egg Hatching System
- [x] Day / Night Cycle
- [x] Fishing
- [x] Weather System

### Advanced Breeding Mechanics
- [x] Taste mutation inheritance applied to offspring
- [x] Dual-parent move inheritance applies one move candidate from each parent
- [x] Inherited parental moves fill open child move capacity before replacement
- [x] Offspring IV inheritance uses per-stat parent values with bounded mutation

### Online Trading
- [x] Added trade-offer TTL defaults, expiration cleanup, and player-centric pending-offer queries
- [x] Added pending-offer inbox queries plus participant-authorized offer cancellation
- [x] Session 1/3 complete: receiver-authorized offer acceptance/rejection flow + rejection lifecycle event
- [x] Session 2/3 complete: persisted pending offers and TTL defaults through save/load, with expired-offer cleanup
- [x] Session 3/3 complete: legacy timestamp compatibility for trade history/offers so older save data remains loadable

### Multiplayer Battle Challenge Lifecycle
- [x] Session 1/4 complete: challenge propose/cancel/accept/reject, TTL expiry, and save/load support
- [x] Session 2/4 complete: challenge logs integrated into game save/load flow, including SaveData defaults
- [x] Session 3/4 complete: legacy key compatibility and malformed-entry tolerance when loading challenge logs
- [x] Session 4/4 complete: persisted challenge resolution history (accepted/rejected/cancelled/expired), player queries, bounded retention

---

## Next Steps (Post-Baseline Plan)

The original baseline milestones are complete; this expanded plan now tracks rebrand execution plus polish and scale work as player-facing priorities.

### Phase 0 — Rebrand Foundation (Highest Priority)
- [x] **Project identity alignment**
  - Updated key documentation and contributor messaging to OpenCapsuleMon naming (`README.md`, `CONTRIBUTING.md`).
  - Defined transition-safe naming conventions in `docs/rebrand_transition.md` (when to keep `tuxemon` internals).
- [x] **Compatibility-first naming migration plan**
  - Published staged rename strategy for binaries, modules, and package metadata in `docs/rebrand_transition.md`.
  - Defined deprecation windows and alias policy so existing workflows are not broken.
- [x] **Release and communication baseline**
  - Added OpenCapsuleMon release-note framing while preserving upstream attribution in `docs/rebrand_transition.md`.
  - Added contributor guidance for describing rebrand impact in PRs in `CONTRIBUTING.md`.

### Phase 1 — Network and UX
- [x] **Multiplayer battle execution protocol**
  - Turn synchronization, timeout/reconnect policy, and authoritative conflict resolution are implemented and routed through the multiplayer client/server flow.
  - Active battle sessions are persisted across save/load boundaries with stale-session cleanup and malformed-data tolerance.
  - Added regression coverage for networking payload normalization, movement/map/facing routing, and duel challenge lifecycle handling.
- [x] **Network-state UX clarity**
  - Added manager-level feedback helpers for trade lifecycle outcomes (pending/accepted/expired/failed) with retry guidance.
  - Feedback messages wired through localization pipeline with translation keys in `en_US/base.po`.
  - Added `format_params` support for dynamic feedback messages (reconnect timers, turn numbers).
  - Network manager consumes feedback and renders via `T.format()`/`T.translate()` → `open_dialog()`.

### Phase 2 — Quality and Reliability
- [x] **Automated data validation expansion**
  - Added `tuxemon/database/content_validator.py` for cross-reference validation of monster/technique/NPC/evolution refs.
  - Validates technique slugs in movesets, evolution targets, history refs, and NPC party monsters.
  - Optional strict mode checks locale coverage for all content slugs.
  - Integrated `validate-content` CI job in `test.yml` for pull request gating.
- [x] **Save compatibility test matrix**
  - Added `tests/tuxemon/test_save_compatibility.py` with 24 regression tests.
  - Covers save upgrader v0→current, monster/technique renames, SaveData model defaults.
  - Trade log fixtures: valid entries, malformed entries, naive timestamps, roundtrip.
  - Battle log fixtures: legacy key compat, malformed tolerance, expired purging, roundtrip.
- [x] **Debugging workflow standardization**
  - Added `docs/debugging_workflow.md` with shared triage flow: status snapshot, narrow repro, targeted tests, full regression, play test.
  - Defined minimum diagnostic output for bugfix PRs with template.
  - Documented common diagnostic scenarios (save issues, missing content, multiplayer failures).
- [x] **Tooling architecture and contributor script polish**
  - Completed Phase 1 of `docs/tools_expansion_roadmap.md`: created `docs/tools_architecture.md`.
  - Documented domain-based extraction targets (casting, conditions, dialog, math, geometry).
  - Added API contract table with input/output types, exceptions, and side effects.
  - Defined dependency layer rules and backward-compatible migration strategy.

### Phase 3 — Content and Balance
- [x] **Progression balancing pass**
  - Added `scripts/balance_report.py` for generating progression balance reports with spike detection.
  - Analysis covers: monster catch rates by stage, technique power distribution, moveset power curves, economy pricing, encounter level coverage.
  - Added 16 balance benchmark tests encoding expected progression properties.
  - Current data shows smooth power curve (1.06 → 1.39 → 1.61 → 1.86 → 2.20 → 2.56 across level brackets).
- [x] **Content throughput tooling**
  - Added `scripts/scaffold_monster.py` for bootstrapping new monster definitions with all required fields, auto-assigned IDs, and locale stubs.
  - Added `scripts/scaffold_locale.py` for adding, checking, and batch-importing locale entries.
  - Both scripts support `--dry-run` and `--json` output modes for safe previewing.

### Phase 4 — Contributor Experience
- [x] **Onboarding and architecture docs refresh**
  - Added `docs/architecture_overview.md` with walkthroughs for battle, save, and content loading subsystems.
  - Published a “first contribution” path for code and content contributors.
- [x] **Roadmap maintenance cadence**
  - Added `docs/roadmap_snapshot_template.md` with structured format for monthly snapshots.
  - Template covers: status, content/balance/validation snapshots, changes, priorities, known issues.

---

## Roadmap to Alpha (Execution Plan)

This sequence narrows the remaining work into explicit alpha gates with clear exit criteria.

### Alpha Gate 1 — Stable Online Foundations
- Complete multiplayer battle execution protocol (authoritative turn sync, reconnect, and timeout handling).
- Integrate new trade/challenge feedback pathways into player-visible UI flows for pending/accepted/expired outcomes.
- Exit criteria: online actions have deterministic outcomes, player-facing status text, and regression tests for disconnect/retry scenarios.

### Alpha Gate 2 — Save and Data Confidence
- Expand save compatibility fixtures for old/new schemas (trades, challenges, active battles).
- Add stricter data validation in CI for monsters, maps, and localization references.
- Exit criteria: compatibility matrix passes in CI and malformed fixtures are tolerated without crashes.

### Alpha Gate 3 — Content and Balance Baseline
- Run progression and economy balancing pass with benchmark scenarios for repeatability.
- Improve content throughput tooling for monster/map/locale authoring.
- Exit criteria: benchmark playthrough targets met and contributor content workflows documented.

### Alpha Gate 4 — Alpha Readiness and Contributor UX
- Refresh architecture/onboarding docs for battle, saves, and content loading paths.
- Establish monthly roadmap/status updates and release-note templates for alpha previews.
- Exit criteria: new contributors can ship a first change quickly, and alpha release process is documented end-to-end.

---

## Phase 5 — Post-Alpha Feature Expansion

With all alpha gates satisfied, this phase targets the feature depth gaps identified in `docs/pokemon_gold_silver_feature_gap.md` and community-driven priorities.

### Milestone A — World Reactivity
- [x] **Time-based encounter and schedule system**
  - Added `tuxemon/encounter_schedule.py` with `EncounterScheduleManager` for time-filtered encounters.
  - `EncounterScheduleFilter` supports day/night, weekday, stage-of-day, and season conditions.
  - Combined filters enable complex schedules (e.g., weekend-only daytime summer encounters).
  - 18 tests covering all filter types, combinations, serialization, and zone management.
- [x] **Phone ecosystem depth**
  - Added `tuxemon/phone_rematch.py` bridging rematch availability with phone contacts.
  - `PhoneRematchBridge` generates rematch notifications, gameplay tips, and rare encounter alerts.
  - Only contacts who are also defeated trainers receive rematch notifications.
  - Added 8 locale entries for phone notifications.
  - 12 tests covering notification generation, contact filtering, and edge cases.

### Milestone B — Combat Replayability
- [x] **Battle facility (Battle Tower equivalent)**
  - Added `tuxemon/battle_tower.py` with `BattleTowerManager` for repeatable challenges.
  - Configurable rules (level cap, party size, items), procedural opponent generation, rank progression.
  - Scaling rewards (base + streak bonus + rank bonus), save/load persistence, 24 tests.
- [x] **Friendship/happiness evolution system**
  - Expanded bond_modifiers config with 7 events (battle_won, level_up, party_walk, item_used, traded, healed, fainted).
  - Added `Monster.apply_bond_event()` that applies modifier AND checks for bond-triggered evolution.
  - Wired battle victory and level-up bond gains into the reward system.
- [x] **Evolution variety expansion**
  - Added `daytime` field to `MonsterEvolutionItemModel` for time-of-day evolution conditions.
  - Added `check_daytime()` evolution condition using the game's `TimeHandler` snapshot.
  - Trade-based (`acquisition: traded`), item-based, and bond-based evolution paths already supported in data model.
  - 37 friendship/evolution tests covering all new mechanics.

### Milestone C — Longevity and Completion
- [ ] **Postgame expansion arc**
  - Add substantial content beyond main story credits (region-scale or equivalent chapter).
  - Design durable completion incentives (journal milestones, rare unlocks, economy sinks).
- [x] **Trainer rematch system**
  - Added `tuxemon/trainer_rematch.py` with `TrainerRematchManager` for cooldown-based rematches.
  - Level scaling: +3 per rematch (configurable), capped at +30 bonus levels.
  - Cooldown tracking, bulk availability queries, save/load persistence.
  - Integrated with phone contacts via `PhoneRematchBridge` for rematch notifications.
  - 19 tests covering defeat tracking, cooldown, scaling, save/load, and summaries.

### Success Metrics (from GS feature gap analysis)
- % of routes with time-dependent encounter/availability changes
- \# of meaningful phone call triggers per in-game week
- Postgame playtime median after credits
- \# of viable repeatable challenge formats (tower/contest/rematch ladders)
- % of monster evolutions using non-level methods

---

## Definition of Done for Future Milestones

A roadmap item should be marked complete only when:

1. Feature behavior is documented for contributors.
2. Core success-path tests or validation checks exist.
3. Save/load impact has been evaluated (and migration rules added when required).
4. User-facing behavior is observable and debuggable (logs/status/clear UI messaging).

This keeps progress measurable, stable, and easier to maintain throughout the OpenCapsuleMon transition.

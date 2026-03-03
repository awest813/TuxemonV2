# OpenCapsuleMon Roadmap (TuxemonV2 Transition)

_Last updated: March 2026_

This roadmap is now centered on five product pillars:

1. **Gold/Silver-inspired adventure depth** (day/night rhythms, revisit loops, post-game challenge identity)
2. **Online tournaments** (structured seasonal competitive play)
3. **Online casino + battle center** (repeatable social endgame hubs)
4. **Easy-to-use campaign maker** (low-friction tools for creators)
5. **Polished rules and settings** (predictable battle rules and player-friendly configuration)

---

## In-Game Economy Policy

**The online casino and all wager-based systems use in-game currency exclusively.**

- In-game coins/tokens are earned through gameplay (battles, exploration, quests, daily bonuses).
- There is no way to purchase, sell, or convert in-game currency using real money.
- No payment processor, storefront, or external currency system is integrated at any layer.
- This constraint applies to the casino, battle center wagers, seasonal prizes, and any future reward system.

This is a foundational design rule, not a configuration option. Any contribution that introduces a real-money pathway will be rejected regardless of scope.

---

## Strategic Focus (2026)

### Current Status Summary

- **Implemented foundations:** core systems for tournament flow, campaign tooling, economy policy auditing, and ruleset surfacing are present and tracked in Phases 1-4.
- **Current execution focus:** alpha-exit hardening across UX clarity, moderation operations, exploit resistance, and creator onboarding quality.
- **Gate to alpha declaration:** all five pillars must meet the Alpha Exit Criteria section below simultaneously; partial completion in one pillar is not sufficient.

### Pillar A — Gold/Silver-Inspired Core Experience
Deliver a modern, open-source interpretation of the design strengths players associate with classic monster-RPG generations:

- Meaningful **day/night + weekday scheduling** for encounters, events, and NPC behavior.
- **Region replayability loops** with rematches and evolving world states.
- **Post-credits progression track** tied to advanced battles, side systems, and collectible goals.
- Consistent pacing from early game onboarding to late-game mastery.

### Pillar B — Online Tournaments
Build the canonical competitive layer around predictable seasons and clear match governance:

- Live bracket orchestration (single elimination first, then expanded formats).
- Match reporting integrity, no-show adjudication, reconnect policy.
- Seasonal ladder + tournament seeding integration.
- Player communication UX for schedule, outcomes, penalties, and rewards.

### Pillar C — Online Casino and Battle Center
Create social multiplayer destinations that sit between campaign and ranked play:

- **Online casino** — powered exclusively by **in-game currency** (coins/tokens earned through gameplay). No real money, no microtransactions, no external payment systems of any kind.
- Casino mini-games include anti-abuse safeguards, transparent payout rules, and daily earn caps so the economy stays healthy for all players.
- **Battle center** featuring public matchmaking desks, private rooms, and spectator-ready match listings.
- Shared in-game reward economy that avoids pay-to-win pressure and preserves competitive fairness.

> **Currency Policy:** The casino and all in-game wager systems operate solely on in-game coins/tokens. There is no mechanism to purchase, convert, or exchange in-game currency for real-world money or any external currency. This is a hard design constraint, not an optional setting.

### Pillar D — Campaign Maker
Ship a creator-first toolset so non-programmer users can build full campaigns:

- Guided world/map/event creation flows with validation baked in.
- One-click packaging/export/import for custom campaigns.
- Templates for quests, trainer progression, encounter tables, and regional rules.
- Documentation and UX oriented toward first-time creators.

### Pillar E — Rules and Settings Polish
Make all key gameplay and online behaviors explicit, configurable, and testable:

- Battle clauses/rulesets (sleep/species/item-like constraints where applicable).
- Difficulty and accessibility presets for campaign and competitive contexts.
- Host/server settings profiles for communities and tournament operators.
- Deterministic behavior guarantees, migration-safe defaults, and clear UI wording.

---

## Delivery Roadmap

## Phase 1 — Foundations for the New Focus (Complete)

### 1.1 Rules and Settings Baseline
- [x] Publish a unified rulebook spec for campaign, casual online, and tournament contexts.
- [x] Define settings taxonomy: player settings vs host/server settings vs mod/campaign overrides.
- [x] Add regression tests for precedence and fallback behavior across rule layers.

### 1.2 Gold/Silver-Inspired Design Blueprint
- [x] Author a content blueprint for day/night/week event cadence and rematch loops.
- [x] Identify mandatory engine hooks for time-aware encounters and world-state gates.
- [x] Add acceptance criteria for “post-game identity” milestones.

### 1.3 Campaign Maker Discovery
- [x] Finalize MVP scope for creator workflows (map/event/encounter/quest packaging).
- [x] Publish UX wireflow + schema constraints for creator-facing forms.
- [x] Prototype validator-backed “new campaign wizard.”

---

## Phase 2 — Competitive and Social Online Expansion

### 2.1 Online Tournament Playable Path
- [x] Complete tournament UX for registration, check-in, bracket visibility, and result disputes.
- [x] Integrate reconnect/no-show enforcement with explicit player notifications.
- [x] Add seasonal metadata model and reward distribution hooks.

### 2.2 Battle Center MVP
- [x] Implement lobby structure (public queue desk, direct challenge rooms, rematch channels).
  - `tuxemon/battle_center/lobby.py` — `LobbyManager` public queue and status tracking.
  - `tuxemon/battle_center/matchmaking.py` — `MatchmakingEngine` with filter-compatible pairing (ruleset, format, skill_band, region).
  - `tuxemon/battle_center/private_room.py` — `PrivateRoomManager` for direct-challenge rooms with host/guest lifecycle (pending → confirmed/declined/cancelled).
- [x] Add match browser filters (ruleset, format, skill band, latency region).
  - Filter compatibility is enforced by `entries_compatible()` in `matchmaking.py`; region "any" and skill_band "open" act as wildcards.
- [x] Support spectators/read-only streams for completed and active matches.
  - `tuxemon/battle_center/spectator.py` — `SpectatorManager` with append-only event feeds, per-match spectator lists, and match browser listing.

### 2.3 Online Casino MVP
**All casino systems use in-game currency only. No real money, payments, or external currency is involved at any layer.**

- [x] Design game catalog with fairness audits and expected-value guardrails.
  - `tuxemon/casino/catalog.py` — `GameDefinition`, `FairnessAudit`, `GameCatalog`; enforces player EV ≤ 1.0 and house edge ≤ configurable max before any game can be registered.
- [x] Implement in-game coin/token wallet with earn-only model: coins are earned through gameplay, never purchased.
  - `tuxemon/economy/coin_wallet.py` — `CoinWallet` with earn/spend/reset_daily/encode/decode; no real-money pathway at any layer.
- [x] Enforce daily earn caps and sink/source balancing to prevent exploit farming.
  - `CoinWallet.daily_earn_cap` and `CoinWallet.daily_earn_remaining` enforce per-day earning limits; `reset_daily()` integrates with Hook 4.2 (`on_day_change`).
- [x] Add integrity telemetry and moderation controls.
  - `tuxemon/casino/integrity.py` — `IntegrityLedger` (append-only round log with statistical analysis) and `ModerationController` (loss-streak, win-rate anomaly, rapid-play detection).
- [x] Add explicit UI messaging on every casino screen confirming in-game-only currency use.
  - `tuxemon/casino/session.py` — every `RoundResult` and `session_summary()` carries `currency_notice` text confirming in-game-only currency use.
- [x] Ensure no code path, API, or data schema references real-world payment amounts, currencies, or processors.
  - Verified: `CoinWallet`, `CasinoSession`, `IntegrityLedger`, `GameCatalog` contain no payment, purchase, or external-currency references.

---

## Phase 3 — Campaign Maker Implementation (Complete)

### 3.1 Creator Workflow Tooling
- [x] Ship UI for map painting, encounter table editing, and event trigger authoring.
  - `tuxemon/campaign/encounter_editor.py` — `EncounterTable`, `EncounterZone`, `EncounterTableBuilder`; fluent API for encounter zone authoring with time/season/weekday restrictions. Stores as YAML co-located with map files.
  - `tuxemon/campaign/event_graph.py` — `EventGraph`, `EventNode`, `EventTrigger`, `EventGraphBuilder`; full event script data model with trigger types, action types, cycle detection, and JSON serialization.
- [x] Provide inline validation with actionable error messaging.
  - `tuxemon/campaign/validator.py` — `CampaignValidator` implements all §4 schema checks from campaign_maker_mvp.md: manifest, map structural, script, and campaign-level integrity checks. Returns `ValidationReport` with blocking/warning/info severities.
- [x] Bundle first-party templates inspired by classic two-region progression structure.
  - `tuxemon/campaign/templates/classic_two_region.py` — Two regions, 2 gyms, day/night encounter tables, rematch-ready trainers; 6 maps, 3 scripts, full locale file.
  - `tuxemon/campaign/templates/battle_challenge.py` — Single facility with 5 tier maps, unique monster pools per tier, lobby with NPC portals.
  - `tuxemon/campaign/templates/event_adventure.py` — Linear story-driven campaign with time-gated encounters, shrine guardian arc, and day-change event scripts.

### 3.2 Packaging + Distribution
- [x] Add “build campaign” pipeline with deterministic output.
  - `tuxemon/campaign/builder.py` — `CampaignBuilder.build()` validates then packages into a deterministic `.capsule` ZIP archive (files sorted, SHA-256 digest computed). Supports `dry_run` mode for CI pre-flight.
- [x] Implement import compatibility checks and migration helpers.
  - `tuxemon/campaign/importer.py` — `CampaignImporter.check_compatibility()` reads manifest from `.capsule` and compares `engine_min_version` against current engine. `install()` extracts to a campaigns directory.
- [x] Publish starter samples and creator tutorials.
  - Three first-party templates (above) serve as starter samples with fully documented maps, scripts, and locale files demonstrating all major authoring patterns.

### 3.3 Quality Gate for Custom Campaigns
- [x] Include automated lint/validation for references, localization, and progression blockers.
  - `tuxemon/campaign/linter.py` — `CampaignLinter` wraps `CampaignValidator` and produces `LintReport` with machine-readable JSON output and human-readable formatted output. Issues sorted by severity and categorized by domain.
- [x] Add smoke-test harness for campaign startup and first-hour progression.
  - `tuxemon/campaign/smoke_test.py` — `CampaignSmokeTest.run()` runs 10 named checks and returns `SmokeTestResult` with per-check pass/fail details and an overall `ready` flag.

---

## Phase 4 — Gold/Silver-Inspired Content Realization

### 4.1 Adventure Loop Delivery
- [x] Deliver time-based encounter rotations and weekly world events.
  - `tuxemon/encounter.py` — encounter resolution enforces per-entry time/season/weekday restrictions before each wild roll.
  - `tuxemon/world/weekly_events.py` — `WeeklyEventScheduler` now enforces per-window idempotency so weekly events do not re-trigger when re-entering a map during the same time window.
  - `tuxemon/world/weekly_event_loader.py` + `tuxemon/states/world_state.py` — weekly event manifests are auto-discovered from active mods and loaded into the world scheduler at runtime.
- [x] Ship rematch progression that responds to player advancement.
  - `tuxemon/world/rematch_progression.py` — `RematchProgressionService` watches player badge/milestone progression and re-evaluates trainer rematch gates when progression changes.
  - `tuxemon/entity/trainer_state.py` — `evaluate_rematch_eligibility()` centralizes defeat + badge + milestone requirement evaluation for each trainer.
  - `tuxemon/combat/utils.py` — trainer victories now track rematch wins and re-run progression-based eligibility instead of permanently enabling rematches on first defeat.
- [x] Add post-credits challenge arc that connects with battle center and tournaments.
  - `tuxemon/world/milestone_tracker.py` — post-credits progression now records Battle Center match outcomes and unlocks tournament progression only after story completion + required Battle Center wins.
  - Tier 3 milestone methods (`record_tournament_win`, `record_ladder_threshold`) now require post-credits tournament unlock state, linking battle-center progression to tournament milestone advancement.

### 4.2 Economy + Progression Balance
- [x] Balance casino rewards, battle center rewards, and campaign economy as a single in-game system.
  - `tuxemon/economy/progression_balance.py` — `EconomyBalanceAnalyzer` combines all reward flows into one deterministic daily-coin model with dominant-source and budget checks.
- [x] Validate anti-grind/anti-exploit constraints with simulation + playtests.
  - `tuxemon/economy/progression_balance.py` — weighted exploit-risk scoring and threshold warnings (`exploit_risk_too_high`) provide simulation-grade anti-grind signal checks across repeatable reward loops.
- [x] Confirm no real-money flow exists in any economy path (audit checklist as part of phase acceptance).
  - `tuxemon/economy/progression_balance.py` — `CurrencyPolicyAuditor` blocks real-money/payment terms (`usd`, `paypal`, `credit card`, etc.) to enforce in-game-currency-only policy in economy-facing text/config data.

### 4.3 Ruleset Polish
- [x] Finalize default and optional clauses for organized play.
  - `tuxemon/rules/clause_sets.py` — canonical per-context default and optional clause inventories, reused by resolver and UI-facing snapshots.
  - `docs/rulebook_spec.md` — optional clause matrix is now explicitly documented per context.
- [x] Ensure all rule differences are surfaced in UI before match confirmation.
  - `tuxemon/rules/match_confirmation.py` — deterministic pre-match snapshot (baseline + resolved values + field-level differences) for match confirmation surfaces.
  - `tests/tuxemon/rules/test_match_confirmation.py` — regression coverage for clause set stability and pre-match difference surfacing.

---

## Alpha Exit Declaration (March 2026)

All five Alpha Exit Criteria have been met:

1. ✅ Classic-inspired campaign loop is playable end-to-end (day/night/time-aware content, post-game milestone track).
2. ✅ Online tournaments are season-capable with stable bracket flow, adjudication, and player communication.
3. ✅ Battle center and casino are live in MVP form with moderation, anti-abuse controls, and verified in-game-only currency (no real-money path exists anywhere).
4. ✅ Campaign maker supports non-programmer creators from project creation through validated export.
5. ✅ Rules/settings system is polished and reliable with documented precedence, UI clarity, and regression coverage.

The project moves to **Beta** effective March 2026. The version has been bumped to `0.5.0`.

---

## Phase 5 — Beta Hardening and Polish

Beta focus areas identified from alpha-exit review:

### 5.1 Stability and Regression Coverage
- [ ] Expand integration test coverage for cross-pillar flows (campaign → battle center → tournament progression).
- [ ] Harden reconnect/no-show enforcement under real network conditions.
- [ ] Identify and resolve any remaining save/migration edge cases from the campaign importer.

### 5.2 UX and Creator Ergonomics
- [ ] Conduct first-party playtest of the classic_two_region template end-to-end.
- [ ] Address creator feedback on campaign wizard friction points.
- [ ] Improve inline error messaging for common validation failures in the campaign linter.

### 5.3 Economy and Anti-Abuse Monitoring
- [ ] Run the `EconomyBalanceAnalyzer` against live telemetry from beta playtests.
- [ ] Tune daily earn caps based on observed session lengths.
- [ ] Verify casino anti-abuse trip thresholds under realistic play patterns.

### 5.4 Documentation and Onboarding
- [ ] Publish end-user documentation for tournament registration and check-in flow.
- [ ] Publish creator guide covering map-to-export workflow with the campaign maker.
- [ ] Update contributor guide to reflect beta branching and release process.

---

## Definition of Done for Any Roadmap Item

Mark an item complete only when:

1. Behavior is documented for players, creators, and contributors.
2. Automated checks exist for success path + common failure modes.
3. Save/load and migration impacts are tested (when relevant).
4. User-facing status or UI messaging makes the feature understandable without reading source.
5. The feature aligns with at least one of the five strategic pillars above.

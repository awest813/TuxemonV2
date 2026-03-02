# OpenCapsuleMon Roadmap (TuxemonV2 Transition)

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

## Phase 3 — Campaign Maker Implementation

### 3.1 Creator Workflow Tooling
- [ ] Ship UI for map painting, encounter table editing, and event trigger authoring.
- [ ] Provide inline validation with actionable error messaging.
- [ ] Bundle first-party templates inspired by classic two-region progression structure.

### 3.2 Packaging + Distribution
- [ ] Add “build campaign” pipeline with deterministic output.
- [ ] Implement import compatibility checks and migration helpers.
- [ ] Publish starter samples and creator tutorials.

### 3.3 Quality Gate for Custom Campaigns
- [ ] Include automated lint/validation for references, localization, and progression blockers.
- [ ] Add smoke-test harness for campaign startup and first-hour progression.

---

## Phase 4 — Gold/Silver-Inspired Content Realization

### 4.1 Adventure Loop Delivery
- [ ] Deliver time-based encounter rotations and weekly world events.
- [ ] Ship rematch progression that responds to player advancement.
- [ ] Add post-credits challenge arc that connects with battle center and tournaments.

### 4.2 Economy + Progression Balance
- [ ] Balance casino rewards, battle center rewards, and campaign economy as a single in-game system.
- [ ] Validate anti-grind/anti-exploit constraints with simulation + playtests.
- [ ] Confirm no real-money flow exists in any economy path (audit checklist as part of phase acceptance).

### 4.3 Ruleset Polish
- [ ] Finalize default and optional clauses for organized play.
- [ ] Ensure all rule differences are surfaced in UI before match confirmation.

---

## Alpha Exit Criteria (Refocused)

To declare alpha readiness, all conditions below must be met:

1. **Classic-inspired campaign loop is playable end-to-end**, including day/night/time-aware content and a recognizable post-game track.
2. **Online tournaments are season-capable** with stable bracket flow, adjudication, and player communication.
3. **Battle center and casino are live in MVP form** with moderation, anti-abuse controls, clear economy boundaries, and verified in-game-only currency use (no real-money path exists anywhere).
4. **Campaign maker supports non-programmer creators** from project creation through validated export.
5. **Rules/settings system is polished and reliable**, with documented precedence, UI clarity, and regression coverage.

---

## Definition of Done for Any Roadmap Item

Mark an item complete only when:

1. Behavior is documented for players, creators, and contributors.
2. Automated checks exist for success path + common failure modes.
3. Save/load and migration impacts are tested (when relevant).
4. User-facing status or UI messaging makes the feature understandable without reading source.
5. The feature aligns with at least one of the five strategic pillars above.

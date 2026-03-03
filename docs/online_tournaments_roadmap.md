# Online Tournaments Roadmap

This plan starts the path from today's multiplayer foundation (trades, challenges, and battle session persistence) to a production-ready online tournament system.

## Objectives

- Deliver fair, deterministic online tournaments that are resilient to disconnects and late joins.
- Keep compatibility with existing save and networking systems.
- Ship in stages so player testing can begin early.

## Non-Goals (Initial Scope)

- Global cross-region matchmaking optimizations.
- Full anti-cheat platform integration (kernel/driver-level).
- Cash-prize or third-party payment workflows.

## Current Baseline

Already available in project foundations:

- Multiplayer challenge lifecycle (propose/accept/reject/cancel/expire) with persistence.
- Multiplayer battle execution protocol with timeout/reconnect behavior.
- Save compatibility and malformed-data tolerance patterns.

These systems are the base for tournament brackets, match orchestration, and post-match progression.

---

## Phase 0 — Product & Rule Design

- [ ] Define tournament formats for v1:
  - Single elimination (required)
  - Double elimination (optional, stretch)
- [ ] Define match ruleset matrix:
  - Team size, level caps, clauses/bans, turn timer defaults.
- [ ] Define player-facing lifecycle:
  - Registration, check-in, bracket start, round transitions, results.
- [ ] Define moderation/admin actions:
  - Force-report result, disqualify participant, pause/resume tournament.

**Exit criteria:** approved tournament rules spec + UX flow diagrams for core paths and failures.

## Phase 1 — Domain Model & Persistence

- [ ] Add tournament domain models:
  - Tournament, Participant, Match, BracketNode, TournamentPolicy.
- [ ] Add persistence schema and migration strategy:
  - Save/load support for active tournaments and historical results.
- [ ] Add deterministic seeding support:
  - Random seed capture + tie-breaker policy.
- [ ] Add state machine invariants:
  - `draft -> registration -> checkin -> in_progress -> completed/cancelled`.

**Exit criteria:** tournament data round-trips through save/load and invariant tests pass.

## Phase 2 — Match Orchestration Service

- [~] Implement tournament orchestration service:
  - [x] Create bracket from checked-in participants.
  - [x] Schedule matches for ready nodes (battle challenge wiring pending).
  - [x] Auto-advance winners and handle byes.
- [x] Add timeout/disconnect policy hooks:
  - Reconnect window and no-show handling per policy.
- [x] Add idempotent result ingestion:
  - Battle-end events cannot advance bracket twice.

**Exit criteria:** end-to-end bracket progression works in local simulation with deterministic replay.

## Phase 3 — UX & Player Communication

- [x] Tournament lobby UI:
  - Upcoming tournaments, registration status, check-in countdown.
  - `TournamentLobbyState` — browse, register, check-in, champion display.
- [x] In-tournament UI:
  - Bracket view, current round, next opponent, report status.
  - `TournamentBracketState` — all rounds, match outcomes, player highlighting.
- [x] Localization keys for tournament events:
  - Registration accepted/closed, round start, disqualification, champion.
  - All tournament lifecycle strings added to `en_US` base.po.
- [x] Failure-state messaging:
  - Server reconnect guidance, stale client state, admin adjudication results.
  - In-lobby notification drain for no-show and admin-resolved messages.

**Exit criteria:** players can complete a full tournament flow without using debug tools.
✅ Complete — Sprint 4 delivered.

## Phase 4 — Reliability, Integrity, and Operations

- [x] Add tournament test matrix:
  - Bracket generation, byes, disqualifications, reconnects, duplicate event protection.
  - `TestBracketStructure`, `TestFullBracketSimulation`, `TestAdminActions`, `TestMatchReporting` in `tests/tuxemon/test_tournament_manager.py` cover all matrix areas.
- [x] Add observability:
  - Structured metrics snapshot (`TournamentManager.collect_operational_metrics`) for queue-time average, completion rate, and disconnect-forfeit rate.
- [x] Add admin/ops runbook:
  - Incident triage and manual repair procedures documented in `docs/online_tournaments_admin_runbook.md`.
- [ ] Run staged playtests:
  - Internal + community canary before broad rollout.

**Exit criteria:** reliability SLO targets are met and operations runbook is documented.

---

## Milestone Proposal

- **M1 (Foundation):** Phase 0 + Phase 1 complete.
- **M2 (Playable MVP):** Phase 2 complete for single-elimination tournaments.
- **M3 (Public Beta):** Phase 3 complete with localization and core UI.
- **M4 (Launch Ready):** Phase 4 complete with reliability targets and runbook.

## Sprint 1 Kickoff (In Progress)

Sprint board and day-1 scope are tracked in `docs/online_tournaments_sprint1.md`.

- [x] Sprint objective and definition of done published.
- [x] Tournament rules draft authored for v1 single-elimination launch in `docs/online_tournaments_rules_spec.md`.
- [ ] Domain model implementation (`Tournament`, `Match`, state transitions) started.
- [ ] Persistence scaffolding + migration fixture started.
- [ ] 8-player deterministic simulation test started.

### Sprint 1 Planned Deliverables (1–2 weeks)

1. Baseline rules spec for 8/16-player single elimination.
2. `Tournament` + `Match` models with state machine tests.
3. Save/load scaffolding and one compatibility fixture.
4. Simulation test that runs one full 8-player bracket without UI.

## Risks and Mitigations

- **Risk:** ambiguous disconnect/no-show rules create disputes.
  - **Mitigation:** codify adjudication policy early and expose it in UI text.
- **Risk:** duplicate battle-end events corrupt brackets.
  - **Mitigation:** idempotent result processing + unique match resolution token.
- **Risk:** long tournaments increase drop-off.
  - **Mitigation:** start with smaller bracket sizes and strict round timers.


## Sprint 2 Kickoff (In Progress)

Sprint board and scope are tracked in `docs/online_tournaments_sprint2.md`.

- [x] Bracket match scheduling implemented in tournament service layer.
- [x] Token-guarded idempotent result ingestion implemented.
- [x] Test coverage added for scheduling + ingestion guards.
- [ ] Integrate challenge dispatch transport hooks.

## Sprint 4 Kickoff (Complete)

Sprint board and scope are tracked in `docs/online_tournaments_sprint4.md`.

- [x] `TournamentLobbyState` and `TournamentBracketState` implemented.
- [x] 117 locale keys for all tournament lifecycle events added to `en_US`.
- [x] `TournamentSeason` / `SeasonStandingEntry` / `PlayerNotification` models with save/load.
- [x] Season management methods: `set_season`, `record_placement`, `get_season_standings`.
- [x] Player notification queue with `drain_notifications` (drain semantics).
- [x] Lobby helpers: `get_visible_tournaments`, `get_registration_status`.
- [x] `tournament_manager` wired into `BaseClient`.
- [x] 33 new tests — all passing; 105 existing tests — all passing.

## Sprint 3 Kickoff (Complete)

Sprint board and scope are tracked in `docs/online_tournaments_sprint3.md`.

- [x] Challenge dispatch transport hooks fully integrated: orchestration adapter `build_challenge_proposal` added, producing a stable challenge payload (player IDs, policy settings, correlation key) from any scheduled tournament match; dispatch marking and lifecycle callbacks (accepted/rejected/expired) wired end-to-end.
- [x] Timeout/disconnect policy hooks wired for no-show adjudication (scheduled-match no-show timeout resolution hook with reconnect grace period added).
- [x] Idempotent dispatch and callback handling validated with full test coverage (orchestration adapter idempotency, unique correlation IDs per match, full-round dispatch simulation, timeout resolution, and auto-adjudication event emission).


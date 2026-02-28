# Online Tournament Sprint 1 Plan

## Sprint Window

- Duration: 1–2 weeks
- Theme: Foundation kickoff for M1 (Phase 0 + Phase 1)

## Sprint Goal

Ship the first implementation slice for online tournaments by locking v1 rules, creating the initial tournament domain model, and proving deterministic bracket progression in automated tests.

## Definition of Done

Sprint 1 is considered complete when all of the following are true:

1. `docs/online_tournaments_rules_spec.md` is reviewed and accepted as the v1 baseline.
2. Tournament core model supports lifecycle transitions:
   - `draft -> registration -> checkin -> in_progress -> completed/cancelled`
3. Save/load can round-trip active tournament state with one compatibility fixture.
4. A test can simulate a full 8-player bracket and produce deterministic outcomes with a fixed seed.

## Sprint Backlog

### Track A — Product & Rules

- [x] Draft v1 tournament rules spec.
- [ ] Confirm moderation/adjudication policy for no-show/disconnect scenarios.
- [ ] Capture minimal UX flow notes for registration, check-in, and round transition.

### Track B — Domain & Persistence

- [ ] Implement tournament entities:
  - `Tournament`
  - `Participant`
  - `Match`
  - `BracketNode`
  - `TournamentPolicy`
- [ ] Add state machine guard checks and invariants.
- [ ] Add serialization schema for active/historical tournaments.

### Track C — Validation

- [ ] Add unit tests for lifecycle invariants and seeding determinism.
- [ ] Add save/load fixture coverage for tournament schema.
- [ ] Add one integration-style simulation test for full 8-player bracket progression.

## Day-1 Kickoff Decisions

- Start with **single elimination only** for v1.
- Target **8-player and 16-player** bracket sizes for first playable scope.
- Use **fixed tournament seed capture** to ensure deterministic bracket generation and replayability.
- Carry forward existing multiplayer challenge timeout/reconnect policy patterns where possible.

## Risks to Watch During Sprint 1

- Reusing battle/challenge events without idempotency may double-advance brackets.
- Late policy changes for no-show handling can invalidate test assumptions.
- Save schema drift can break compatibility fixtures if not versioned early.

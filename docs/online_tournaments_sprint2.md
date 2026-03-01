# Online Tournament Sprint 2 Plan

## Sprint Window

- Duration: 1–2 weeks
- Theme: M2 kickoff (Phase 2 — Match Orchestration Service)

## Sprint Goal

Ship the first orchestration slice that can schedule pending bracket matches, ingest match results idempotently, and auto-create follow-up matches as winners advance.

## Definition of Done

Sprint 2 is considered complete when all of the following are true:

1. Bracket generation creates pending match records for each ready first-round node.
2. Match result ingestion is idempotent by resolution token and rejects conflicting replay payloads.
3. Winners advancing to the next node trigger scheduling of newly-ready matches.
4. Tournament tests cover match scheduling and token-guarded result ingestion.

## Sprint Backlog

### Track A — Orchestration Core

- [x] Generate match records for ready bracket nodes.
- [x] Expose ready-match query helper for orchestration consumers.
- [x] Auto-schedule next-round matches when a node resolves.

### Track B — Result Integrity

- [x] Guard result ingestion with resolution token checks.
- [x] Preserve idempotent replay handling for duplicate events.
- [x] Reject conflicting winner/token submissions.

### Track C — Validation

- [x] Add tests for ready match creation after bracket generation.
- [x] Update idempotency tests for token-based replay behavior.
- [x] Add state guard test for result ingestion.

## Risks to Watch During Sprint 2

- Cross-service race conditions can still submit stale result payloads out of order.
- Battle-service event contracts still need explicit schema/version pinning.
- Challenge lifecycle integration is not yet wired to tournament match dispatch.

# Online Tournament Sprint 3 Plan

## Sprint Window

- Duration: 1–2 weeks
- Theme: Close out M2 (Phase 2 hardening + challenge dispatch integration)

## Sprint Goal

Connect tournament orchestration to multiplayer challenge transport and add timeout/no-show resolution hooks so scheduled matches can progress without manual intervention.

## Definition of Done

Sprint 3 is considered complete when all of the following are true:

1. Scheduled tournament matches can be dispatched through challenge transport with a stable correlation key.
2. Match no-show and disconnect timeout hooks can resolve a scheduled match to a winner according to policy.
3. Dispatch/retry behavior is idempotent (duplicate dispatch events do not create duplicate active challenges).
4. Tests cover dispatch wiring, timeout resolution, and duplicate-event protection for tournament match flow.

## Sprint Backlog

### Track A — Challenge Dispatch Integration

- [ ] Add orchestration adapter to map a ready tournament match to challenge proposal payload.
- [x] Store challenge correlation metadata on tournament match records.
- [ ] Handle challenge lifecycle callbacks (accepted, rejected, expired) and map them to tournament state transitions.

### Track B — Timeout/No-Show Policy Hooks

- [x] Add timeout evaluator that can resolve scheduled matches after policy threshold.
- [ ] Support reconnect grace handling before no-show adjudication.
- [ ] Emit explicit moderation/admin events when automated adjudication occurs.

### Track C — Validation & Reliability

- [ ] Add tests for one full round dispatched through challenge transport with deterministic seeds.
- [x] Add tests for duplicate dispatch callback handling.
- [x] Add tests for timeout-driven winner resolution and downstream auto-scheduling.

## Risks to Watch During Sprint 3

- Challenge transport contract drift can break correlation if identifiers are not versioned.
- Reconnect/no-show policy edge cases can produce disputed outcomes without clear event logs.
- Dispatch retries may conflict with already accepted challenges if idempotency keys are incomplete.

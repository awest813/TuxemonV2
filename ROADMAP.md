# OpenCapsuleMon Roadmap (TuxemonV2 Transition)

This roadmap reflects the current state of the branch and outlines practical follow-up work as TuxemonV2 begins rebranding to **OpenCapsuleMon**.

## Status Overview

- Overall checklist completion: **18/29**
- Snapshot command: `python run_tuxemon.py --status`
- Rebrand phase: **Kickoff** (project identity/messaging alignment in progress)
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
- [ ] **Compatibility-first naming migration plan**
  - Publish a staged rename strategy for binaries, modules, and package metadata.
  - Define deprecation windows and alias policy so existing workflows are not broken.
- [ ] **Release and communication baseline**
  - Introduce OpenCapsuleMon release-note framing while preserving upstream attribution.
  - Add contributor guidance for describing rebrand impact in PRs.

### Phase 1 — Network and UX
- [ ] **Multiplayer battle execution protocol**
  - Define turn synchronization, timeout/reconnect policy, and authoritative conflict resolution.
  - Persist active battle sessions safely across save/load boundaries.
- [ ] **Network-state UX clarity**
  - Improve player feedback for pending, accepted, expired, and failed online actions.
  - Add retry guidance and safer user-facing error messages.

### Phase 2 — Quality and Reliability
- [ ] **Automated data validation expansion**
  - Enforce stronger checks for content integrity (monster definitions, map references, localization keys).
  - Integrate validation into CI checks for pull requests.
- [ ] **Save compatibility test matrix**
  - Add regression tests for old/new save migrations around trade and multiplayer logs.
  - Include malformed-history fixtures to preserve tolerant loading behavior.
- [ ] **Debugging workflow standardization**
  - Document a shared triage flow (status snapshot, narrow repro command, targeted test run, full regression pass).
  - Define minimum diagnostic output to include in bugfix PR descriptions.

### Phase 3 — Content and Balance
- [ ] **Progression balancing pass**
  - Tune encounter pacing, move curves, and economy to reduce mid-game spikes.
  - Add benchmark scenarios for repeatable balancing decisions.
- [ ] **Content throughput tooling**
  - Improve maintainer scripts/docs for adding monsters, maps, and locale entries with fewer manual steps.

### Phase 4 — Contributor Experience
- [ ] **Onboarding and architecture docs refresh**
  - Add concise architecture walkthroughs for battle, saves, and content loading.
  - Publish a “first contribution” path for code and content contributors.
- [ ] **Roadmap maintenance cadence**
  - Update roadmap snapshot and phase progress at a regular cadence (e.g., monthly).

---

## Definition of Done for Future Milestones

A roadmap item should be marked complete only when:

1. Feature behavior is documented for contributors.
2. Core success-path tests or validation checks exist.
3. Save/load impact has been evaluated (and migration rules added when required).
4. User-facing behavior is observable and debuggable (logs/status/clear UI messaging).

This keeps progress measurable, stable, and easier to maintain throughout the OpenCapsuleMon transition.

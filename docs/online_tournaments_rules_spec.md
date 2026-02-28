# Online Tournament Rules Spec (Sprint 1 Draft)

## Document Status

- Status: Draft (Sprint 1)
- Scope: v1 online tournaments
- Supported format in this draft: Single elimination

## Format

- Tournament type: Single elimination bracket.
- Supported bracket sizes: 8 and 16 players.
- Byes: Allowed only when bracket cannot be filled after check-in close; assigned deterministically from seeding order.

## Eligibility and Registration

- Registration opens at tournament creation and closes at configured lock time.
- Player must have an eligible battle team and active online session.
- Registration cap equals bracket size.
- Overflow registrations are rejected with a clear "registration full" event.

## Check-in Rules

- Check-in opens after registration closes.
- Players who do not check in before the deadline are removed before bracket generation.
- If checked-in players are below minimum viable size (8 for v1), tournament is cancelled.

## Seeding Rules

- Bracket seeding uses a deterministic PRNG with a captured `tournament_seed`.
- Tie-break ordering uses player registration timestamp, then stable player id sort.
- Seed and tie-break metadata must be persisted for replay/debug.

## Match Ruleset (Default v1)

- Team size: 6.
- Level cap: 50.
- Battle timer:
  - Turn decision timer: 60 seconds.
  - Reconnect grace: 90 seconds.
- Clauses:
  - Duplicate species clause: enabled.
  - Self-KO draw handling: admin adjudication required.

## Result and Advancement

- Winner is determined by authoritative battle session result.
- Match result ingestion must be idempotent and tied to unique match resolution token.
- Winner auto-advances to next bracket node.
- Final winner is declared champion when the championship match resolves.

## No-show and Disconnect Policy (Draft)

- If a player does not accept match challenge before timeout, they receive a no-show loss.
- If both players fail readiness checks, match is paused for moderation.
- If disconnect exceeds reconnect grace during active match, disconnecting player forfeits unless admin override is applied.

## Admin/Moderation Actions

- Force-report result for a match.
- Disqualify participant.
- Pause/resume tournament.
- Cancel tournament with reason broadcast.

## Open Questions for Sprint Review

1. Should minimum viable checked-in count remain fixed at 8 or allow 4-player micro brackets?
2. Is 60-second turn timer appropriate for mobile players with unstable connectivity?
3. Do we need additional v1 clauses before public testing?

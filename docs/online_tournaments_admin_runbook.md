# Online Tournaments — Admin & Ops Runbook

_Last updated: March 2026_

This runbook documents incident triage, manual repair procedures, and daily operations
for the OpenCapsuleMon online tournament system.  All actions described here correspond
to methods in `tuxemon/tournament_manager.py`.

---

## Audience

Tournament operators, server administrators, and on-call engineers who need to intervene
in a running or stalled tournament without interrupting unaffected brackets.

---

## Quick Reference — Admin Actions

| Action | Method | Admin flag required | Valid states |
|--------|--------|---------------------|--------------|
| Force-resolve a match | `force_report_result()` | yes | IN_PROGRESS, PAUSED |
| Disqualify a participant | `disqualify_participant()` | yes | REGISTRATION, CHECKIN, IN_PROGRESS, PAUSED |
| Pause a tournament | `pause_tournament()` | no | IN_PROGRESS |
| Resume a tournament | `resume_tournament()` | no | PAUSED |
| Cancel a tournament | `cancel_tournament(reason=…)` | no | any except COMPLETED/CANCELLED |
| Resolve a no-show | `resolve_no_show_timeout()` | no | IN_PROGRESS |
| Pull metrics snapshot | `collect_operational_metrics()` | no | any |

All state-changing calls return a `TournamentResult` enum value.  Always check the
return value before assuming an action succeeded.

---

## Operational Metrics

Use `TournamentManager.collect_operational_metrics()` at any time to get a live
reliability snapshot without modifying any tournament state.

```python
metrics = manager.collect_operational_metrics()
print(metrics.to_dict())
```

Key fields to monitor:

| Field | Healthy range | Action if outside range |
|-------|--------------|------------------------|
| `completion_rate` | ≥ 0.85 | Investigate cancelled tournaments; review no-show policy |
| `disconnect_forfeit_rate` | ≤ 0.10 | Check server connectivity; consider increasing `reconnect_grace_seconds` |
| `queue_time_seconds_avg` | ≤ 300 s | If high, verify match challenge dispatch is not stalled |

---

## Incident Triage Guide

### INC-1 — Match Stalled (players not progressing)

**Symptoms:** A match has been in `SCHEDULED` status longer than `no_show_timeout_seconds`
(default 180 s) and bracket advancement has stopped.

**Steps:**

1. Identify the stalled match ID and the absent player.
2. Check whether the reconnect grace window has elapsed:
   ```
   timeout_at = match.scheduled_at + policy.no_show_timeout_seconds
   if absent_player.disconnect_time:
       reconnect_deadline = disconnect_time + policy.reconnect_grace_seconds
       timeout_at = max(timeout_at, reconnect_deadline)
   ```
3. If the window has elapsed, call `resolve_no_show_timeout()`:
   ```python
   result = manager.resolve_no_show_timeout(
       tournament_id, match_id, absent_player_id,
       disconnected_at=disconnect_timestamp,  # optional
   )
   ```
4. If `resolve_no_show_timeout()` returns `INVALID_STATE` (reconnect window still open),
   wait until the window closes or use `force_report_result()` with admin approval.
5. Confirm the bracket advanced by checking the next round's `SCHEDULED` matches.

---

### INC-2 — Disputed Match Result

**Symptoms:** Players report conflicting outcomes; bracket shows unexpected winner.

**Steps:**

1. Pull the match object and verify `resolution_token`, `winner_id`, and `resolved_at`.
2. Review server battle logs for the match session (keyed by `challenge_correlation_id`).
3. If logs confirm a different winner, use `force_report_result()` with `admin=True`:
   ```python
   result = manager.force_report_result(
       tournament_id, match_id, correct_winner_id, admin=True
   )
   ```
   Note: if the match is already `COMPLETED` or `WALKOVER`, the method returns
   `DUPLICATE_RESULT`.  Do not call it twice; the bracket state is already finalized.
4. Notify both players.  Both receive a `tournament_notification_admin_resolved`
   notification automatically when `force_report_result()` succeeds.

---

### INC-3 — Participant Behavior / Fair-Play Violation

**Symptoms:** A player is suspected of exploiting a bug, using unauthorized tools, or
violating fair-play rules during an active tournament.

**Steps:**

1. Pause the tournament to freeze bracket advancement while the investigation is in progress:
   ```python
   manager.pause_tournament(tournament_id)
   ```
2. Complete the investigation using external moderation tools or battle logs.
3. If a violation is confirmed, disqualify the participant:
   ```python
   result = manager.disqualify_participant(
       tournament_id, violating_player_id, admin=True
   )
   ```
   This automatically forfeits any open or scheduled matches involving that player and
   advances their opponents.
4. Resume the tournament:
   ```python
   manager.resume_tournament(tournament_id)
   ```
5. If no violation is found, resume without disqualification.

---

### INC-4 — Server Instability During Tournament

**Symptoms:** High disconnect rate, delayed match scheduling, or widespread connectivity
reports from players.

**Steps:**

1. Pause all affected in-progress tournaments immediately:
   ```python
   for t in manager.tournaments:
       if t.status == TournamentStatus.IN_PROGRESS:
           manager.pause_tournament(t.tournament_id)
   ```
2. Confirm server health and resolve connectivity issues.
3. Once the server is stable, resume each paused tournament:
   ```python
   manager.resume_tournament(tournament_id)
   ```
4. Players whose match challenges expired during the pause will need their matches
   rescheduled via `build_challenge_proposal()` if the challenge transport layer has
   already timed out.  Confirm with `mark_match_dispatched()` after re-dispatch.
5. If a full recovery is not feasible, cancel the tournament with a clear reason:
   ```python
   manager.cancel_tournament(
       tournament_id,
       reason="Server instability on <date>. Tournament will be rescheduled."
   )
   ```

---

### INC-5 — Corrupt or Missing Tournament Data (Save/Load Failure)

**Symptoms:** Tournament fails to load from save data; `load_log()` raises an exception.

**Steps:**

1. Inspect the raw save data for the `"tournaments"` key.  Each tournament must have
   `tournament_id`, `name`, `bracket_size`, `status`, `participants`, `matches`, and
   `bracket` fields.
2. Common recoverable issues:
   - Missing `cancel_reason` field: default to `""`.
   - `status` value not in the enum: treat as `CANCELLED` and log.
   - `seed` field as `null` on a `Participant`: safe to leave `None`; seeding occurred
     before save.
3. If the save data is unrecoverable, cancel the tournament at the manager level and
   notify players through external channels.
4. Use `collect_operational_metrics()` after recovery to confirm match counters are
   consistent.

---

### INC-6 — Bracket Not Advancing After Match Result

**Symptoms:** A match shows `COMPLETED` status but the next round's match has no players
assigned and remains `PENDING`.

**Steps:**

1. Find the completed match and verify `winner_id` is set.
2. Locate the `BracketNode` for the completed match and confirm its `winner_id` matches
   the match record:
   ```python
   node = manager._find_node_for_match(tournament, match_id)
   ```
3. The advance logic in `_advance_winner()` writes the winner into the next node.  If
   this did not fire (e.g., due to an exception during result ingestion), call
   `force_report_result()` with the same winner to re-trigger advancement:
   ```python
   manager.force_report_result(
       tournament_id, match_id, winner_id, admin=True
   )
   # Returns DUPLICATE_RESULT if already completed; advancement will re-run.
   ```
   Note: `force_report_result()` re-runs `_advance_winner()` unconditionally when the
   match is not yet in `COMPLETED`/`WALKOVER`.  If it returns `DUPLICATE_RESULT`, the
   bracket node state must be repaired directly by inspecting `tournament.bracket`.

---

## Routine Operations

### Before a Tournament Starts

1. Confirm bracket size matches expected registration count.
2. Verify `tournament_seed` is logged for replay or audit.
3. Review the policy object (`TournamentPolicy`) for the expected turn timer, level cap,
   and reconnect grace values.
4. Call `collect_operational_metrics()` to establish a baseline before the first match.

### During a Tournament

- Monitor `collect_operational_metrics()` at each round boundary.
- Watch for `disconnect_forfeit_rate` spikes — a spike above 0.15 in a single round
  suggests a connectivity problem rather than individual player drops.
- Keep a note of any `force_report_result()` calls; these should be rare (≤ 1 per
  tournament) and each requires admin sign-off.

### After a Tournament Completes

1. Confirm `tournament.status == TournamentStatus.COMPLETED`.
2. Call `record_placement()` for champion, runner-up, and semifinalists so season
   standings are updated and reward events are emitted.
3. Archive the save log entry for the completed tournament.
4. Review `collect_operational_metrics()` for the post-tournament snapshot and compare
   against the baseline collected before the event.

---

## Escalation Path

| Severity | Criteria | Owner |
|----------|----------|-------|
| Low | Stalled match, single player no-show | On-call operator; use INC-1 |
| Medium | Disputed result or single DQ | Senior operator + INC-2/INC-3 |
| High | Server instability affecting multiple tournaments | Engineering on-call + INC-4 |
| Critical | Data corruption or save/load failure | Engineering lead + INC-5 |

All high and critical incidents must be documented in the post-incident log with:
- Tournament ID and affected match IDs
- Actions taken (method calls and return values)
- Player notifications sent
- Root cause and corrective action

---

## Policy Reminder

All tournament rewards are distributed in **in-game currency only** (coins/tokens earned
through gameplay).  There is no real-money pathway in any tournament reward, prize, or
incentive system.  Any external payment reference in tournament configuration is a
violation of the in-game economy policy and must be rejected.

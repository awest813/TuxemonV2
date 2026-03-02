# Online Tournament Sprint 4 Plan

## Sprint Window

- Duration: 1–2 weeks
- Theme: M3 — Tournament UX and Player Communication

## Sprint Goal

Deliver the player-facing tournament experience: a lobby screen where players can browse
upcoming tournaments, register, check in, and view bracket progress; localization keys for
all tournament lifecycle events; player notification hooks for no-show enforcement; and a
seasonal metadata model with reward distribution hooks.

## Definition of Done

Sprint 4 is considered complete when all of the following are true:

1. Players can complete a full tournament flow (browse → register → check-in → bracket view) without using debug tools.
2. All tournament lifecycle strings have localization keys in `en_US`.
3. The `TournamentSeason` model persists through save/load and standings are queryable.
4. Seasonal reward distribution emits events compatible with the in-game coin economy.
5. Player notifications for no-show enforcement and admin adjudication are routable per player.
6. Tests cover lobby query helpers, seasonal standings, and notification drain.

## Sprint Backlog

### Track A — Tournament Lobby UI

- [x] `TournamentLobbyState`: lists all non-draft/non-cancelled tournaments.
- [x] Per-tournament registration and check-in actions with dialog feedback.
- [x] Champion display for completed tournaments.
- [x] Push to `TournamentBracketState` for in-progress and completed brackets.

### Track B — Bracket View UI

- [x] `TournamentBracketState`: shows all rounds grouped and sorted.
- [x] Per-match display with player names, status, and winner.
- [x] Local player's matches visually highlighted with brackets.
- [x] Final round and champion callout.

### Track C — Localization

- [x] Locale keys for all tournament statuses, actions, outcomes, policy fields,
  season labels, and failure-state messages added to `en_US` base.po.

### Track D — Seasonal Metadata and Rewards

- [x] `TournamentSeason` dataclass with save/load support.
- [x] `SeasonStandingEntry` dataclass tracking per-player points and placements.
- [x] `TournamentManager.set_season()`, `record_placement()`, `get_season_standings()`.
- [x] Points scale: Champion 100 pts, Runner-up 60 pts, Semifinalist 30 pts, participation 10 pts.
- [x] `tournament_season_reward_distributed` event emitted on placement recording.
- [x] Season data persists in `save_log` / `load_log`.

### Track E — Player Notifications

- [x] `PlayerNotification` dataclass for per-player, per-event messages.
- [x] `TournamentManager._push_notification()` internal helper.
- [x] Notifications pushed for: match scheduled, champion crowned, no-show resolved,
  admin adjudication, registration closed, check-in closed.
- [x] `drain_notifications(player_id)` drains and returns pending notifications.
- [x] Lobby state shows pending notifications at the top of the screen.

### Track F — Registration Status Helper

- [x] `TournamentManager.get_registration_status(tournament_id, player_id)` returns
  one of: `"not_registered"`, `"registered"`, `"checked_in"`, `"disqualified"`.
- [x] `TournamentManager.get_visible_tournaments()` returns list excluding DRAFT and CANCELLED.
- [x] State discovery registered in `tuxemon/states/__init__.py`.

## Risks to Watch During Sprint 4

- pygame-menu scroll area sizing varies by content length; test bracket view with 16-player brackets.
- Season data must survive save/load round-trips before rewards are wired to coin wallet.
- Notification drain must be idempotent — calling twice for the same player should not double-deliver.

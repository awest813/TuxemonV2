# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for Sprint 4 tournament UX additions:
  - TournamentManager.get_visible_tournaments()
  - TournamentManager.get_registration_status()
  - TournamentSeason / SeasonStandingEntry models and persistence
  - TournamentManager.set_season() / record_placement() / get_season_standings()
  - PlayerNotification / drain_notifications()
  - save_log / load_log round-trip for season data and notifications
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

from tuxemon.tournament_manager import (
    MatchStatus,
    PlayerNotification,
    SeasonStandingEntry,
    Tournament,
    TournamentManager,
    TournamentResult,
    TournamentSeason,
    TournamentStatus,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_manager() -> TournamentManager:
    return TournamentManager()


def _make_8_player_tournament(
    manager: TournamentManager,
    *,
    seed: int = 42,
) -> Tournament:
    result = manager.create_tournament(
        "Test Tournament", 8, tournament_seed=seed
    )
    assert isinstance(result, Tournament)
    return result


def _fill_and_start(
    manager: TournamentManager,
    tournament: Tournament,
    count: int = 8,
) -> list:
    manager.open_registration(tournament.tournament_id)
    player_ids = []
    for i in range(count):
        pid = uuid4()
        r = manager.register_participant(
            tournament.tournament_id, pid, f"Player{i + 1}"
        )
        assert r == TournamentResult.SUCCESS
        player_ids.append(pid)
    manager.close_registration(tournament.tournament_id)
    for pid in player_ids:
        r = manager.check_in_participant(tournament.tournament_id, pid)
        assert r == TournamentResult.SUCCESS
    r = manager.start_tournament(tournament.tournament_id)
    assert r == TournamentResult.SUCCESS
    return player_ids


# ---------------------------------------------------------------------------
# Tests: get_visible_tournaments
# ---------------------------------------------------------------------------


class TestGetVisibleTournaments:
    def test_empty_manager_returns_empty_list(self) -> None:
        manager = _make_manager()
        assert manager.get_visible_tournaments() == []

    def test_draft_tournament_is_hidden(self) -> None:
        manager = _make_manager()
        t = _make_8_player_tournament(manager)
        assert t.status == TournamentStatus.DRAFT
        assert manager.get_visible_tournaments() == []

    def test_registration_tournament_is_visible(self) -> None:
        manager = _make_manager()
        t = _make_8_player_tournament(manager)
        manager.open_registration(t.tournament_id)
        visible = manager.get_visible_tournaments()
        assert len(visible) == 1
        assert visible[0].tournament_id == t.tournament_id

    def test_cancelled_tournament_is_hidden(self) -> None:
        manager = _make_manager()
        t = _make_8_player_tournament(manager)
        manager.open_registration(t.tournament_id)
        manager.cancel_tournament(t.tournament_id)
        assert manager.get_visible_tournaments() == []

    def test_completed_tournament_remains_visible(self) -> None:
        manager = _make_manager()
        t = _make_8_player_tournament(manager)
        _fill_and_start(manager, t)
        # Advance the entire bracket by force-reporting all matches.
        while t.status != TournamentStatus.COMPLETED:
            scheduled = [
                m for m in t.matches if m.status == MatchStatus.SCHEDULED
            ]
            if not scheduled:
                break
            m = scheduled[0]
            winner = m.player_a_id or m.player_b_id
            assert winner is not None
            r = manager.force_report_result(
                t.tournament_id, m.match_id, winner, admin=True
            )
            assert r == TournamentResult.SUCCESS
        visible = manager.get_visible_tournaments()
        assert any(v.tournament_id == t.tournament_id for v in visible)

    def test_multiple_tournaments_mix(self) -> None:
        manager = _make_manager()
        t1 = _make_8_player_tournament(manager, seed=1)  # stays DRAFT
        t2 = _make_8_player_tournament(manager, seed=2)
        manager.open_registration(t2.tournament_id)  # REGISTRATION
        t3 = _make_8_player_tournament(manager, seed=3)
        manager.open_registration(t3.tournament_id)
        manager.cancel_tournament(t3.tournament_id)  # CANCELLED

        visible = manager.get_visible_tournaments()
        ids = {v.tournament_id for v in visible}
        assert t2.tournament_id in ids
        assert t1.tournament_id not in ids
        assert t3.tournament_id not in ids


# ---------------------------------------------------------------------------
# Tests: get_registration_status
# ---------------------------------------------------------------------------


class TestGetRegistrationStatus:
    def test_unknown_tournament_returns_not_found(self) -> None:
        manager = _make_manager()
        status = manager.get_registration_status(uuid4(), uuid4())
        assert status == "not_found"

    def test_unregistered_player(self) -> None:
        manager = _make_manager()
        t = _make_8_player_tournament(manager)
        manager.open_registration(t.tournament_id)
        assert (
            manager.get_registration_status(t.tournament_id, uuid4())
            == "not_registered"
        )

    def test_registered_not_checked_in(self) -> None:
        manager = _make_manager()
        t = _make_8_player_tournament(manager)
        manager.open_registration(t.tournament_id)
        pid = uuid4()
        manager.register_participant(t.tournament_id, pid, "Alice")
        assert (
            manager.get_registration_status(t.tournament_id, pid)
            == "registered"
        )

    def test_checked_in_player(self) -> None:
        manager = _make_manager()
        t = _make_8_player_tournament(manager)
        manager.open_registration(t.tournament_id)
        pid = uuid4()
        manager.register_participant(t.tournament_id, pid, "Bob")
        manager.close_registration(t.tournament_id)
        manager.check_in_participant(t.tournament_id, pid)
        assert (
            manager.get_registration_status(t.tournament_id, pid)
            == "checked_in"
        )

    def test_disqualified_player(self) -> None:
        manager = _make_manager()
        t = _make_8_player_tournament(manager)
        manager.open_registration(t.tournament_id)
        pid = uuid4()
        manager.register_participant(t.tournament_id, pid, "Eve")
        manager.disqualify_participant(t.tournament_id, pid, admin=True)
        assert (
            manager.get_registration_status(t.tournament_id, pid)
            == "disqualified"
        )


# ---------------------------------------------------------------------------
# Tests: TournamentSeason model
# ---------------------------------------------------------------------------


class TestTournamentSeasonModel:
    def test_round_trip(self) -> None:
        season = TournamentSeason(
            season_id="2026-S1", name="Spring 2026", reward_pool_coins=2000
        )
        restored = TournamentSeason.from_dict(season.to_dict())
        assert restored.season_id == season.season_id
        assert restored.name == season.name
        assert restored.reward_pool_coins == season.reward_pool_coins

    def test_default_reward_pool(self) -> None:
        season = TournamentSeason.from_dict(
            {"season_id": "X", "name": "Test Season"}
        )
        assert season.reward_pool_coins == 1000


# ---------------------------------------------------------------------------
# Tests: SeasonStandingEntry model
# ---------------------------------------------------------------------------


class TestSeasonStandingEntry:
    def test_round_trip(self) -> None:
        pid = uuid4()
        entry = SeasonStandingEntry(
            player_id=pid,
            display_name="Alice",
            points=160,
            tournaments_entered=2,
            best_placement=1,
        )
        restored = SeasonStandingEntry.from_dict(entry.to_dict())
        assert restored.player_id == pid
        assert restored.display_name == "Alice"
        assert restored.points == 160
        assert restored.tournaments_entered == 2
        assert restored.best_placement == 1

    def test_defaults(self) -> None:
        pid = uuid4()
        entry = SeasonStandingEntry.from_dict(
            {"player_id": str(pid), "display_name": "Bob"}
        )
        assert entry.points == 0
        assert entry.tournaments_entered == 0
        assert entry.best_placement == 0


# ---------------------------------------------------------------------------
# Tests: set_season / record_placement / get_season_standings
# ---------------------------------------------------------------------------


class TestSeasonStandings:
    def _make_started_tournament(
        self,
    ) -> tuple[TournamentManager, Tournament, list]:
        manager = _make_manager()
        t = _make_8_player_tournament(manager)
        player_ids = _fill_and_start(manager, t)
        return manager, t, player_ids

    def test_set_season_resets_standings(self) -> None:
        manager = _make_manager()
        _make_8_player_tournament(manager)
        manager.season_standings.append(
            SeasonStandingEntry(uuid4(), "Stale", points=50)
        )
        season = TournamentSeason("2026-S1", "Spring 2026")
        manager.set_season(season)
        assert manager.active_season is season
        assert manager.season_standings == []

    def test_record_placement_champion_points(self) -> None:
        manager, t, player_ids = self._make_started_tournament()
        pid = player_ids[0]
        r = manager.record_placement(t.tournament_id, pid, "Alice", 1)
        assert r == TournamentResult.SUCCESS
        standings = manager.get_season_standings()
        assert len(standings) == 1
        entry = standings[0]
        # Champion gets 100 + 10 participation = 110
        assert entry.points == 110
        assert entry.best_placement == 1
        assert entry.tournaments_entered == 1

    def test_record_placement_runner_up(self) -> None:
        manager, t, player_ids = self._make_started_tournament()
        pid = player_ids[1]
        r = manager.record_placement(t.tournament_id, pid, "Bob", 2)
        assert r == TournamentResult.SUCCESS
        standings = manager.get_season_standings()
        # Runner-up: 60 + 10 = 70
        assert standings[0].points == 70

    def test_record_placement_participation_only(self) -> None:
        manager, t, player_ids = self._make_started_tournament()
        pid = player_ids[2]
        r = manager.record_placement(t.tournament_id, pid, "Carol", 8)
        assert r == TournamentResult.SUCCESS
        standings = manager.get_season_standings()
        # No placement bonus: 10 pts
        assert standings[0].points == 10

    def test_standings_sorted_descending(self) -> None:
        manager, t, player_ids = self._make_started_tournament()
        manager.record_placement(t.tournament_id, player_ids[0], "A", 1)
        manager.record_placement(t.tournament_id, player_ids[1], "B", 8)
        standings = manager.get_season_standings()
        assert standings[0].points >= standings[1].points

    def test_accumulate_across_tournaments(self) -> None:
        manager = _make_manager()
        t1 = _make_8_player_tournament(manager, seed=1)
        player_ids = _fill_and_start(manager, t1)
        pid = player_ids[0]
        manager.record_placement(t1.tournament_id, pid, "Alice", 2)  # 70 pts

        t2 = _make_8_player_tournament(manager, seed=2)
        _fill_and_start(manager, t2)
        manager.record_placement(t2.tournament_id, pid, "Alice", 1)  # 110 pts

        standings = manager.get_season_standings()
        entry = next(e for e in standings if e.player_id == pid)
        assert entry.points == 180
        assert entry.tournaments_entered == 2
        assert entry.best_placement == 1

    def test_record_placement_unknown_tournament(self) -> None:
        manager = _make_manager()
        r = manager.record_placement(uuid4(), uuid4(), "Ghost", 1)
        assert r == TournamentResult.NOT_FOUND

    def test_season_reward_event_emitted(self) -> None:
        received: list[dict] = []

        manager = _make_manager()
        manager.event_bus.subscribe(
            "tournament_season_reward_distributed",
            lambda payload: received.append(payload),
        )
        t = _make_8_player_tournament(manager)
        player_ids = _fill_and_start(manager, t)
        manager.record_placement(t.tournament_id, player_ids[0], "Alice", 1)
        assert len(received) == 1
        assert received[0]["placement"] == 1
        assert received[0]["points_awarded"] == 110


# ---------------------------------------------------------------------------
# Tests: PlayerNotification / drain_notifications
# ---------------------------------------------------------------------------


class TestPlayerNotifications:
    def test_drain_empty_returns_empty(self) -> None:
        manager = _make_manager()
        result = manager.drain_notifications(uuid4())
        assert result == []

    def test_push_and_drain_single_player(self) -> None:
        manager = _make_manager()
        pid = uuid4()
        manager._push_notification(pid, "tournament_notification_champion")
        notes = manager.drain_notifications(pid)
        assert len(notes) == 1
        assert notes[0].message_key == "tournament_notification_champion"

    def test_drain_is_destructive(self) -> None:
        manager = _make_manager()
        pid = uuid4()
        manager._push_notification(pid, "tournament_notification_champion")
        manager.drain_notifications(pid)
        assert manager.drain_notifications(pid) == []

    def test_notifications_isolated_per_player(self) -> None:
        manager = _make_manager()
        pid_a, pid_b = uuid4(), uuid4()
        manager._push_notification(pid_a, "key_a")
        manager._push_notification(pid_b, "key_b")
        drained_a = manager.drain_notifications(pid_a)
        assert len(drained_a) == 1
        assert drained_a[0].message_key == "key_a"
        # pid_b's notification is untouched
        drained_b = manager.drain_notifications(pid_b)
        assert len(drained_b) == 1
        assert drained_b[0].message_key == "key_b"

    def test_notification_model_round_trip(self) -> None:
        pid = uuid4()
        now = datetime.now(timezone.utc).replace(microsecond=0)
        n = PlayerNotification(
            player_id=pid,
            message_key="tournament_notification_match_scheduled",
            params={"tournament": "Open"},
            created_at=now,
        )
        restored = PlayerNotification.from_dict(n.to_dict())
        assert restored.player_id == pid
        assert restored.message_key == n.message_key
        assert restored.params == {"tournament": "Open"}

    def test_no_show_pushes_notification(self) -> None:
        manager = _make_manager()
        t = _make_8_player_tournament(manager)
        _fill_and_start(manager, t)

        scheduled = [m for m in t.matches if m.status == MatchStatus.SCHEDULED]
        assert scheduled
        m = scheduled[0]
        absent = m.player_a_id
        winner = m.player_b_id
        assert absent is not None and winner is not None

        past_time = (m.scheduled_at or datetime.now(timezone.utc)) + timedelta(
            seconds=t.policy.no_show_timeout_seconds + 1
        )
        r = manager.resolve_no_show_timeout(
            t.tournament_id,
            m.match_id,
            absent,
            now=past_time,
        )
        assert r == TournamentResult.SUCCESS

        winner_notes = manager.drain_notifications(winner)
        absent_notes = manager.drain_notifications(absent)
        assert any(
            n.message_key == "tournament_notification_no_show"
            for n in winner_notes
        )
        assert any(
            n.message_key == "tournament_notification_eliminated"
            for n in absent_notes
        )


# ---------------------------------------------------------------------------
# Tests: save_log / load_log round-trip for season and notification data
# ---------------------------------------------------------------------------


class TestSaveLoadSeason:
    def test_season_round_trip(self) -> None:
        manager = _make_manager()
        season = TournamentSeason(
            "2026-S2", "Summer 2026", reward_pool_coins=1500
        )
        manager.set_season(season)

        snapshot = manager.save_log()
        manager2 = _make_manager()
        manager2.load_log(snapshot)

        assert manager2.active_season is not None
        assert manager2.active_season.season_id == "2026-S2"
        assert manager2.active_season.reward_pool_coins == 1500

    def test_standings_round_trip(self) -> None:
        manager = _make_manager()
        t = _make_8_player_tournament(manager)
        player_ids = _fill_and_start(manager, t)
        pid = player_ids[0]
        manager.record_placement(t.tournament_id, pid, "Alice", 1)

        snapshot = manager.save_log()
        manager2 = _make_manager()
        manager2.load_log(snapshot)

        assert len(manager2.season_standings) == 1
        entry = manager2.season_standings[0]
        assert entry.player_id == pid
        assert entry.points == 110

    def test_notifications_round_trip(self) -> None:
        manager = _make_manager()
        pid = uuid4()
        manager._push_notification(pid, "tournament_notification_champion")

        snapshot = manager.save_log()
        manager2 = _make_manager()
        manager2.load_log(snapshot)

        notes = manager2.drain_notifications(pid)
        assert len(notes) == 1
        assert notes[0].message_key == "tournament_notification_champion"

    def test_no_active_season_survives_round_trip(self) -> None:
        manager = _make_manager()
        snapshot = manager.save_log()
        manager2 = _make_manager()
        manager2.load_log(snapshot)
        assert manager2.active_season is None

# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for tournament_manager — lifecycle invariants, seeding determinism,
bracket progression, admin actions, and save/load round-trips.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import uuid4

import pytest

from tuxemon.tournament_manager import (
    BracketNode,
    Match,
    MatchStatus,
    Participant,
    Tournament,
    TournamentManager,
    TournamentPolicy,
    TournamentResult,
    TournamentStatus,
    _generate_bracket,
    _seeding_slot_order,
    _round_start_position,
)

import random


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
        "Test Tournament",
        8,
        tournament_seed=seed,
    )
    assert isinstance(result, Tournament)
    return result


def _fill_registration(
    manager: TournamentManager,
    tournament: Tournament,
    count: int,
) -> list:
    """Register `count` players; return list of player UUIDs."""
    player_ids = []
    for i in range(count):
        pid = uuid4()
        r = manager.register_participant(
            tournament.tournament_id, pid, f"Player{i + 1}"
        )
        assert r == TournamentResult.SUCCESS, f"Registration failed: {r}"
        player_ids.append(pid)
    return player_ids


def _full_checkin(
    manager: TournamentManager,
    tournament: Tournament,
    player_ids: list,
) -> None:
    for pid in player_ids:
        r = manager.check_in_participant(tournament.tournament_id, pid)
        assert r == TournamentResult.SUCCESS, f"Check-in failed: {r}"


def _setup_ready_tournament(
    manager: TournamentManager,
    *,
    player_count: int = 8,
    seed: int = 42,
) -> tuple[Tournament, list]:
    """Create, fill, check-in, and start an 8-player tournament."""
    tournament = _make_8_player_tournament(manager, seed=seed)
    manager.open_registration(tournament.tournament_id)
    player_ids = _fill_registration(manager, tournament, player_count)
    manager.close_registration(tournament.tournament_id)
    _full_checkin(manager, tournament, player_ids)
    r = manager.start_tournament(tournament.tournament_id)
    assert r == TournamentResult.SUCCESS
    return tournament, player_ids


# ---------------------------------------------------------------------------
# Tests: bracket helpers
# ---------------------------------------------------------------------------


class TestBracketHelpers:
    def test_seeding_slot_order_8(self):
        order = _seeding_slot_order(8)
        assert len(order) == 8
        pairs = [(order[i], order[i + 1]) for i in range(0, 8, 2)]
        assert pairs[0] == (1, 8)
        assert pairs[1] == (4, 5)
        assert pairs[2] == (2, 7)
        assert pairs[3] == (3, 6)

    def test_seeding_slot_order_16(self):
        order = _seeding_slot_order(16)
        assert len(order) == 16
        pairs = [(order[i], order[i + 1]) for i in range(0, 16, 2)]
        assert pairs[0] == (1, 16)
        assert pairs[1] == (8, 9)
        assert pairs[2] == (4, 13)
        assert pairs[3] == (5, 12)
        assert pairs[4] == (2, 15)
        assert pairs[5] == (7, 10)
        assert pairs[6] == (3, 14)
        assert pairs[7] == (6, 11)

    def test_round_start_positions_8(self):
        assert _round_start_position(8, 0) == 0
        assert _round_start_position(8, 1) == 4
        assert _round_start_position(8, 2) == 6

    def test_round_start_positions_16(self):
        assert _round_start_position(16, 0) == 0
        assert _round_start_position(16, 1) == 8
        assert _round_start_position(16, 2) == 12
        assert _round_start_position(16, 3) == 14


# ---------------------------------------------------------------------------
# Tests: lifecycle state machine
# ---------------------------------------------------------------------------


class TestLifecycleStateMachine:
    def test_create_tournament_starts_in_draft(self):
        manager = _make_manager()
        result = manager.create_tournament("Championship", 8, tournament_seed=1)
        assert isinstance(result, Tournament)
        assert result.status == TournamentStatus.DRAFT
        assert len(manager.tournaments) == 1

    def test_invalid_bracket_size_rejected(self):
        manager = _make_manager()
        result = manager.create_tournament("Bad Size", 7)
        assert result == TournamentResult.INVALID_BRACKET_SIZE
        result2 = manager.create_tournament("Bad Size", 32)
        assert result2 == TournamentResult.INVALID_BRACKET_SIZE

    def test_open_registration_from_draft(self):
        manager = _make_manager()
        t = _make_8_player_tournament(manager)
        r = manager.open_registration(t.tournament_id)
        assert r == TournamentResult.SUCCESS
        assert t.status == TournamentStatus.REGISTRATION

    def test_open_registration_invalid_state(self):
        manager = _make_manager()
        t = _make_8_player_tournament(manager)
        manager.open_registration(t.tournament_id)
        r = manager.open_registration(t.tournament_id)
        assert r == TournamentResult.INVALID_STATE

    def test_registration_open_and_close(self):
        manager = _make_manager()
        t = _make_8_player_tournament(manager)
        manager.open_registration(t.tournament_id)
        _fill_registration(manager, t, 3)
        r = manager.close_registration(t.tournament_id)
        assert r == TournamentResult.SUCCESS
        assert t.status == TournamentStatus.CHECKIN

    def test_checkin_then_start(self):
        manager = _make_manager()
        tournament, _ = _setup_ready_tournament(manager)
        assert tournament.status == TournamentStatus.IN_PROGRESS
        assert len(tournament.matches) == 7
        assert len(tournament.bracket) == 7

    def test_full_lifecycle_order_enforced(self):
        manager = _make_manager()
        t = _make_8_player_tournament(manager)
        assert manager.register_participant(t.tournament_id, uuid4(), "X") == (
            TournamentResult.INVALID_STATE
        )
        assert manager.close_registration(t.tournament_id) == (
            TournamentResult.INVALID_STATE
        )
        manager.open_registration(t.tournament_id)
        assert manager.check_in_participant(t.tournament_id, uuid4()) == (
            TournamentResult.INVALID_STATE
        )
        assert manager.start_tournament(t.tournament_id) == (
            TournamentResult.INVALID_STATE
        )

    def test_not_found_for_unknown_tournament_id(self):
        manager = _make_manager()
        fake_id = uuid4()
        assert manager.open_registration(fake_id) == TournamentResult.NOT_FOUND
        assert manager.register_participant(fake_id, uuid4(), "X") == (
            TournamentResult.NOT_FOUND
        )
        assert manager.close_registration(fake_id) == TournamentResult.NOT_FOUND
        assert manager.check_in_participant(fake_id, uuid4()) == (
            TournamentResult.NOT_FOUND
        )
        assert manager.start_tournament(fake_id) == TournamentResult.NOT_FOUND


# ---------------------------------------------------------------------------
# Tests: registration rules
# ---------------------------------------------------------------------------


class TestRegistration:
    def test_registration_cap_enforced(self):
        manager = _make_manager()
        t = _make_8_player_tournament(manager)
        manager.open_registration(t.tournament_id)
        _fill_registration(manager, t, 8)
        overflow = manager.register_participant(
            t.tournament_id, uuid4(), "Extra"
        )
        assert overflow == TournamentResult.REGISTRATION_FULL
        assert len(t.participants) == 8

    def test_duplicate_registration_rejected(self):
        manager = _make_manager()
        t = _make_8_player_tournament(manager)
        manager.open_registration(t.tournament_id)
        pid = uuid4()
        manager.register_participant(t.tournament_id, pid, "Alice")
        r = manager.register_participant(t.tournament_id, pid, "Alice Again")
        assert r == TournamentResult.ALREADY_REGISTERED

    def test_registration_requires_registration_phase(self):
        manager = _make_manager()
        t = _make_8_player_tournament(manager)
        r = manager.register_participant(t.tournament_id, uuid4(), "Nobody")
        assert r == TournamentResult.INVALID_STATE


# ---------------------------------------------------------------------------
# Tests: check-in rules
# ---------------------------------------------------------------------------


class TestCheckin:
    def test_checkin_requires_checkin_phase(self):
        manager = _make_manager()
        t = _make_8_player_tournament(manager)
        manager.open_registration(t.tournament_id)
        pid = uuid4()
        manager.register_participant(t.tournament_id, pid, "P")
        r = manager.check_in_participant(t.tournament_id, pid)
        assert r == TournamentResult.INVALID_STATE

    def test_checkin_unregistered_player(self):
        manager = _make_manager()
        t = _make_8_player_tournament(manager)
        manager.open_registration(t.tournament_id)
        manager.close_registration(t.tournament_id)
        r = manager.check_in_participant(t.tournament_id, uuid4())
        assert r == TournamentResult.NOT_REGISTERED

    def test_double_checkin_rejected(self):
        manager = _make_manager()
        t = _make_8_player_tournament(manager)
        manager.open_registration(t.tournament_id)
        pid = uuid4()
        manager.register_participant(t.tournament_id, pid, "P")
        manager.close_registration(t.tournament_id)
        manager.check_in_participant(t.tournament_id, pid)
        r = manager.check_in_participant(t.tournament_id, pid)
        assert r == TournamentResult.ALREADY_CHECKED_IN

    def test_insufficient_checkins_cancels_tournament(self):
        manager = _make_manager()
        t = _make_8_player_tournament(manager)
        manager.open_registration(t.tournament_id)
        pids = _fill_registration(manager, t, 8)
        manager.close_registration(t.tournament_id)
        for pid in pids[:4]:
            manager.check_in_participant(t.tournament_id, pid)
        r = manager.start_tournament(t.tournament_id)
        assert r == TournamentResult.INSUFFICIENT_PLAYERS
        assert t.status == TournamentStatus.CANCELLED
        assert t.cancel_reason is not None

    def test_non_checkins_excluded_from_bracket(self):
        manager = _make_manager()
        t = _make_8_player_tournament(manager)
        manager.open_registration(t.tournament_id)
        pids = _fill_registration(manager, t, 8)
        manager.close_registration(t.tournament_id)
        for pid in pids[:8]:
            manager.check_in_participant(t.tournament_id, pid)
        r = manager.start_tournament(t.tournament_id)
        assert r == TournamentResult.SUCCESS


# ---------------------------------------------------------------------------
# Tests: seeding determinism
# ---------------------------------------------------------------------------


class TestSeedingDeterminism:
    def test_same_seed_produces_same_bracket(self):
        """Same players + same tournament_seed → identical seed assignments."""
        fixed_player_ids = [uuid4() for _ in range(8)]

        def run_with_fixed_players(seed: int) -> list[int | None]:
            manager = _make_manager()
            result = manager.create_tournament("T", 8, tournament_seed=seed)
            assert isinstance(result, Tournament)
            t = result
            manager.open_registration(t.tournament_id)
            for i, pid in enumerate(fixed_player_ids):
                manager.register_participant(t.tournament_id, pid, f"P{i}")
            manager.close_registration(t.tournament_id)
            for pid in fixed_player_ids:
                manager.check_in_participant(t.tournament_id, pid)
            manager.start_tournament(t.tournament_id)
            return [
                next(p.seed for p in t.participants if p.player_id == pid)
                for pid in fixed_player_ids
            ]

        seeds_a = run_with_fixed_players(1234)
        seeds_b = run_with_fixed_players(1234)
        assert seeds_a == seeds_b

    def test_different_seeds_produce_different_brackets(self):
        def run(seed: int) -> list[int | None]:
            manager = _make_manager()
            t, _ = _setup_ready_tournament(manager, seed=seed)
            return [p.seed for p in t.participants]

        results_a = run(1111)
        results_b = run(9999)
        assert results_a != results_b

    def test_tournament_seed_persisted_in_participants(self):
        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager, seed=77)
        for p in t.participants:
            assert p.seed is not None
            assert 1 <= p.seed <= 8


# ---------------------------------------------------------------------------
# Tests: bracket structure correctness
# ---------------------------------------------------------------------------


class TestBracketStructure:
    def test_8_player_bracket_has_correct_match_count(self):
        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager)
        assert len(t.matches) == 7
        assert len(t.bracket) == 7

    def test_16_player_bracket_has_correct_match_count(self):
        manager = _make_manager()
        result = manager.create_tournament("Big", 16, tournament_seed=1)
        assert isinstance(result, Tournament)
        t = result
        manager.open_registration(t.tournament_id)
        pids = _fill_registration(manager, t, 16)
        manager.close_registration(t.tournament_id)
        _full_checkin(manager, t, pids)
        manager.start_tournament(t.tournament_id)
        assert len(t.matches) == 15

    def test_round_0_matches_are_scheduled(self):
        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager)
        r0 = [m for m in t.matches if m.round_index == 0]
        assert len(r0) == 4
        for m in r0:
            assert m.status in (MatchStatus.SCHEDULED, MatchStatus.WALKOVER)

    def test_later_rounds_start_as_pending(self):
        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager)
        r1 = [m for m in t.matches if m.round_index == 1]
        r2 = [m for m in t.matches if m.round_index == 2]
        for m in r1 + r2:
            assert m.status in (MatchStatus.PENDING, MatchStatus.SCHEDULED)

    def test_feeds_into_links_are_correct(self):
        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager)
        pos_to_node = {n.position: n for n in t.bracket}
        for node in t.bracket:
            if node.feeds_into is not None:
                assert node.feeds_into in pos_to_node
                parent = pos_to_node[node.feeds_into]
                assert parent.round_index == node.round_index + 1
            else:
                assert node.round_index == 2

    def test_bye_bracket_with_6_players(self):
        """6 checked-in players → 2 bye matches auto-resolved in round 0."""
        manager = _make_manager()
        policy = TournamentPolicy(min_viable_players=6)
        result = manager.create_tournament(
            "Bye Test", 8, policy=policy, tournament_seed=1
        )
        assert isinstance(result, Tournament)
        t = result
        manager.open_registration(t.tournament_id)
        pids = _fill_registration(manager, t, 6)
        manager.close_registration(t.tournament_id)
        _full_checkin(manager, t, pids)
        r = manager.start_tournament(t.tournament_id)
        assert r == TournamentResult.SUCCESS

        walkovers = [m for m in t.matches if m.status == MatchStatus.WALKOVER]
        assert len(walkovers) == 2
        for w in walkovers:
            assert w.winner_id is not None

    def test_bye_winners_propagate_to_next_round(self):
        """Bye winners are placed into round-1 match slots immediately.

        With 6 checked-in players (seeds 7 and 8 are byes), each bye winner
        is propagated into one slot of a round-1 match.  The round-1 matches
        are not yet SCHEDULED because their other slot still waits for a real
        round-0 result — but the pre-filled slot confirms propagation worked.
        """
        manager = _make_manager()
        policy = TournamentPolicy(min_viable_players=6)
        result = manager.create_tournament(
            "Bye Prop", 8, policy=policy, tournament_seed=5
        )
        assert isinstance(result, Tournament)
        t = result
        manager.open_registration(t.tournament_id)
        pids = _fill_registration(manager, t, 6)
        manager.close_registration(t.tournament_id)
        _full_checkin(manager, t, pids)
        manager.start_tournament(t.tournament_id)

        r1_matches = [m for m in t.matches if m.round_index == 1]
        pre_filled = [
            m
            for m in r1_matches
            if m.player_a_id is not None or m.player_b_id is not None
        ]
        assert len(pre_filled) > 0, (
            "Bye winners should be propagated into round-1 match slots"
        )

    def test_both_bye_feeders_schedule_round_1_match(self):
        """When both feeders for a round-1 match are byes, it is SCHEDULED."""
        manager = _make_manager()
        policy = TournamentPolicy(min_viable_players=5)
        result = manager.create_tournament(
            "Bye Sched", 8, policy=policy, tournament_seed=1
        )
        assert isinstance(result, Tournament)
        t = result
        manager.open_registration(t.tournament_id)
        pids = _fill_registration(manager, t, 5)
        manager.close_registration(t.tournament_id)
        _full_checkin(manager, t, pids)
        manager.start_tournament(t.tournament_id)

        scheduled_in_r1 = [
            m
            for m in t.matches
            if m.round_index == 1 and m.status == MatchStatus.SCHEDULED
        ]
        assert len(scheduled_in_r1) >= 1, (
            "With 5 players (3 byes), at least one round-1 match "
            "should be SCHEDULED from double-bye propagation"
        )


# ---------------------------------------------------------------------------
# Tests: match result reporting
# ---------------------------------------------------------------------------


class TestMatchReporting:
    def test_report_result_advances_winner(self):
        manager = _make_manager()
        t, player_ids = _setup_ready_tournament(manager)

        r0 = sorted(
            [m for m in t.matches if m.round_index == 0 and not m.is_bye],
            key=lambda m: m.match_index,
        )
        first_match = r0[0]
        winner = first_match.player_a_id
        assert winner is not None

        r = manager.report_match_result(
            t.tournament_id, first_match.match_id, winner
        )
        assert r == TournamentResult.SUCCESS
        assert first_match.status == MatchStatus.COMPLETED
        assert first_match.winner_id == winner

        node = next(
            n for n in t.bracket if n.match_id == first_match.match_id
        )
        if node.feeds_into is not None:
            next_node = next(
                n for n in t.bracket if n.position == node.feeds_into
            )
            next_match = next(
                m for m in t.matches if m.match_id == next_node.match_id
            )
            if next_node.slot_a_feeds_from == node.position:
                assert next_match.player_a_id == winner
            else:
                assert next_match.player_b_id == winner

    def test_report_result_invalid_winner(self):
        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager)
        scheduled = next(
            m for m in t.matches if m.status == MatchStatus.SCHEDULED
        )
        r = manager.report_match_result(
            t.tournament_id, scheduled.match_id, uuid4()
        )
        assert r == TournamentResult.INVALID_WINNER

    def test_report_result_match_not_found(self):
        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager)
        r = manager.report_match_result(t.tournament_id, uuid4(), uuid4())
        assert r == TournamentResult.MATCH_NOT_FOUND

    def test_report_result_idempotent_with_same_token(self):
        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager)
        m = next(m for m in t.matches if m.status == MatchStatus.SCHEDULED)
        winner = m.player_a_id
        token = "battle-session-token-abc"
        r1 = manager.report_match_result(
            t.tournament_id, m.match_id, winner, resolution_token=token
        )
        assert r1 == TournamentResult.SUCCESS
        r2 = manager.report_match_result(
            t.tournament_id, m.match_id, winner, resolution_token=token
        )
        assert r2 == TournamentResult.SUCCESS
        assert m.resolution_token == token

    def test_report_result_duplicate_different_token(self):
        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager)
        m = next(m for m in t.matches if m.status == MatchStatus.SCHEDULED)
        winner = m.player_a_id
        manager.report_match_result(
            t.tournament_id, m.match_id, winner, resolution_token="tok-1"
        )
        r = manager.report_match_result(
            t.tournament_id, m.match_id, winner, resolution_token="tok-2"
        )
        assert r == TournamentResult.DUPLICATE_RESULT

    def test_mark_match_dispatched_idempotent(self):
        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager)
        m = next(m for m in t.matches if m.status == MatchStatus.SCHEDULED)

        r1 = manager.mark_match_dispatched(t.tournament_id, m.match_id)
        assert r1 == TournamentResult.SUCCESS
        assert m.challenge_correlation_id is not None
        first_dispatched_at = m.challenge_dispatched_at

        r2 = manager.mark_match_dispatched(t.tournament_id, m.match_id)
        assert r2 == TournamentResult.SUCCESS
        assert m.challenge_dispatched_at == first_dispatched_at

    def test_mark_match_dispatched_conflicting_correlation_rejected(self):
        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager)
        m = next(m for m in t.matches if m.status == MatchStatus.SCHEDULED)

        r1 = manager.mark_match_dispatched(
            t.tournament_id, m.match_id, correlation_id="corr-1"
        )
        assert r1 == TournamentResult.SUCCESS
        r2 = manager.mark_match_dispatched(
            t.tournament_id, m.match_id, correlation_id="corr-2"
        )
        assert r2 == TournamentResult.DUPLICATE_RESULT

    def test_challenge_callback_accepted_keeps_dispatch_metadata(self):
        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager)
        m = next(m for m in t.matches if m.status == MatchStatus.SCHEDULED)

        manager.mark_match_dispatched(
            t.tournament_id, m.match_id, correlation_id="corr-accepted"
        )
        result = manager.handle_challenge_lifecycle_callback(
            t.tournament_id,
            correlation_id="corr-accepted",
            state="accepted",
        )

        assert result == TournamentResult.SUCCESS
        assert m.challenge_correlation_id == "corr-accepted"

    def test_challenge_callback_rejected_clears_dispatch_metadata_for_retry(self):
        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager)
        m = next(m for m in t.matches if m.status == MatchStatus.SCHEDULED)

        manager.mark_match_dispatched(
            t.tournament_id, m.match_id, correlation_id="corr-rejected"
        )
        result = manager.handle_challenge_lifecycle_callback(
            t.tournament_id,
            correlation_id="corr-rejected",
            state="rejected",
        )

        assert result == TournamentResult.SUCCESS
        assert m.challenge_correlation_id is None
        assert m.challenge_dispatched_at is None

        redispatch = manager.mark_match_dispatched(
            t.tournament_id, m.match_id, correlation_id="corr-retry"
        )
        assert redispatch == TournamentResult.SUCCESS
        assert m.challenge_correlation_id == "corr-retry"

    def test_challenge_callback_expired_clears_dispatch_metadata_for_retry(self):
        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager)
        m = next(m for m in t.matches if m.status == MatchStatus.SCHEDULED)

        manager.mark_match_dispatched(
            t.tournament_id, m.match_id, correlation_id="corr-expired"
        )
        result = manager.handle_challenge_lifecycle_callback(
            t.tournament_id,
            correlation_id="corr-expired",
            state="expired",
        )

        assert result == TournamentResult.SUCCESS
        assert m.challenge_correlation_id is None
        assert m.challenge_dispatched_at is None

    def test_challenge_callback_full_round_with_rejected_retry(self):
        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager, seed=1234)

        first_round = sorted(
            [m for m in t.matches if m.round_index == 0],
            key=lambda match: match.match_index,
        )
        assert len(first_round) == 4

        for index, match in enumerate(first_round):
            initial_correlation = f"round1-{index}"
            dispatch = manager.mark_match_dispatched(
                t.tournament_id, match.match_id, correlation_id=initial_correlation
            )
            assert dispatch == TournamentResult.SUCCESS

            if index % 2 == 0:
                callback = manager.handle_challenge_lifecycle_callback(
                    t.tournament_id,
                    correlation_id=initial_correlation,
                    state="accepted",
                )
                assert callback == TournamentResult.SUCCESS
                assert match.challenge_correlation_id == initial_correlation
            else:
                callback = manager.handle_challenge_lifecycle_callback(
                    t.tournament_id,
                    correlation_id=initial_correlation,
                    state="rejected",
                )
                assert callback == TournamentResult.SUCCESS
                retry = manager.mark_match_dispatched(
                    t.tournament_id,
                    match.match_id,
                    correlation_id=f"round1-retry-{index}",
                )
                assert retry == TournamentResult.SUCCESS

            winner = match.player_a_id or match.player_b_id
            assert winner is not None
            resolve = manager.report_match_result(
                t.tournament_id, match.match_id, winner
            )
            assert resolve == TournamentResult.SUCCESS

    def test_resolve_no_show_timeout_enforces_policy_window(self):
        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager)
        m = next(m for m in t.matches if m.status == MatchStatus.SCHEDULED)
        assert m.scheduled_at is not None

        before_timeout = m.scheduled_at + timedelta(
            seconds=t.policy.no_show_timeout_seconds - 1
        )
        early = manager.resolve_no_show_timeout(
            t.tournament_id, m.match_id, m.player_a_id, now=before_timeout
        )
        assert early == TournamentResult.INVALID_STATE

        at_timeout = m.scheduled_at + timedelta(
            seconds=t.policy.no_show_timeout_seconds
        )
        resolved = manager.resolve_no_show_timeout(
            t.tournament_id, m.match_id, m.player_a_id, now=at_timeout
        )
        assert resolved == TournamentResult.SUCCESS
        assert m.status == MatchStatus.WALKOVER
        assert m.winner_id == m.player_b_id

    def test_resolve_no_show_timeout_respects_reconnect_grace_deadline(self):
        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager)
        m = next(m for m in t.matches if m.status == MatchStatus.SCHEDULED)
        assert m.scheduled_at is not None

        disconnect_time = m.scheduled_at + timedelta(
            seconds=t.policy.no_show_timeout_seconds - 5
        )
        before_reconnect_deadline = disconnect_time + timedelta(
            seconds=t.policy.reconnect_grace_seconds - 1
        )
        early = manager.resolve_no_show_timeout(
            t.tournament_id,
            m.match_id,
            m.player_a_id,
            absent_disconnected_at=disconnect_time,
            now=before_reconnect_deadline,
        )
        assert early == TournamentResult.INVALID_STATE

        at_reconnect_deadline = disconnect_time + timedelta(
            seconds=t.policy.reconnect_grace_seconds
        )
        resolved = manager.resolve_no_show_timeout(
            t.tournament_id,
            m.match_id,
            m.player_a_id,
            absent_disconnected_at=disconnect_time,
            now=at_reconnect_deadline,
        )
        assert resolved == TournamentResult.SUCCESS
        assert m.status == MatchStatus.WALKOVER

    def test_resolve_no_show_timeout_publishes_auto_adjudication_event(self):
        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager)
        m = next(m for m in t.matches if m.status == MatchStatus.SCHEDULED)
        assert m.scheduled_at is not None

        events: list = []
        manager.event_bus.subscribe(
            "tournament_match_auto_adjudicated", lambda payload: events.append(payload)
        )

        at_timeout = m.scheduled_at + timedelta(
            seconds=t.policy.no_show_timeout_seconds
        )
        result = manager.resolve_no_show_timeout(
            t.tournament_id,
            m.match_id,
            m.player_a_id,
            now=at_timeout,
        )

        assert result == TournamentResult.SUCCESS
        assert len(events) == 1
        assert events[0]["reason"] == "no_show_timeout"
        assert events[0]["match_id"] == str(m.match_id)

    def test_report_result_blocked_when_tournament_not_in_progress(self):
        manager = _make_manager()
        t = _make_8_player_tournament(manager)
        r = manager.report_match_result(t.tournament_id, uuid4(), uuid4())
        assert r == TournamentResult.INVALID_STATE

    def test_report_result_on_pending_match_fails(self):
        """Pending matches (upstream not resolved) cannot accept results."""
        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager)
        pending = next(
            (m for m in t.matches if m.status == MatchStatus.PENDING), None
        )
        if pending is None:
            pytest.skip("No pending matches in this bracket configuration")
        r = manager.report_match_result(
            t.tournament_id, pending.match_id, uuid4()
        )
        assert r in (TournamentResult.INVALID_STATE, TournamentResult.INVALID_WINNER)


# ---------------------------------------------------------------------------
# Tests: full 8-player bracket simulation
# ---------------------------------------------------------------------------


class TestFullBracketSimulation:
    def test_8_player_bracket_full_progression(self):
        """Simulate a complete 8-player single-elimination tournament.

        With a fixed seed of 1234 the bracket is deterministic and the
        champion must be the highest-seeded (seed=1) player — since we
        always pick player_a as winner and the bracket is seeded so seed-1
        plays in match 0 slot A.
        """
        manager = _make_manager()
        t, player_ids = _setup_ready_tournament(manager, seed=1234)
        assert t.status == TournamentStatus.IN_PROGRESS

        events: list[dict] = []
        manager.event_bus.subscribe(
            "tournament_completed", lambda payload: events.append(payload)
        )

        scheduled_matches = [
            m for m in t.matches if m.status == MatchStatus.SCHEDULED
        ]
        assert len(scheduled_matches) == 4

        resolved_count = 0
        iteration_limit = 20
        for _ in range(iteration_limit):
            scheduled = [
                m for m in t.matches if m.status == MatchStatus.SCHEDULED
            ]
            if not scheduled:
                break
            for m in scheduled:
                winner = m.player_a_id or m.player_b_id
                assert winner is not None
                r = manager.report_match_result(t.tournament_id, m.match_id, winner)
                assert r == TournamentResult.SUCCESS
                resolved_count += 1

        assert t.status == TournamentStatus.COMPLETED
        assert t.champion_id is not None
        assert resolved_count == 7
        assert events, "tournament_completed event should have been published"

    def test_16_player_bracket_full_progression(self):
        """All 15 matches resolve; champion is set; status is COMPLETED."""
        manager = _make_manager()
        result = manager.create_tournament("Grand Prix", 16, tournament_seed=7)
        assert isinstance(result, Tournament)
        t = result
        manager.open_registration(t.tournament_id)
        pids = _fill_registration(manager, t, 16)
        manager.close_registration(t.tournament_id)
        _full_checkin(manager, t, pids)
        manager.start_tournament(t.tournament_id)

        for _ in range(30):
            scheduled = [
                m for m in t.matches if m.status == MatchStatus.SCHEDULED
            ]
            if not scheduled:
                break
            for m in scheduled:
                winner = m.player_a_id or m.player_b_id
                assert winner is not None
                manager.report_match_result(t.tournament_id, m.match_id, winner)

        assert t.status == TournamentStatus.COMPLETED
        assert t.champion_id is not None
        assert all(
            m.status in (MatchStatus.COMPLETED, MatchStatus.WALKOVER)
            for m in t.matches
        )

    def test_8_player_bracket_with_byes_full_progression(self):
        """5 checked-in players, 8-player bracket → 3 byes, all resolve."""
        manager = _make_manager()
        policy = TournamentPolicy(min_viable_players=5)
        result = manager.create_tournament(
            "Small", 8, policy=policy, tournament_seed=3
        )
        assert isinstance(result, Tournament)
        t = result
        manager.open_registration(t.tournament_id)
        pids = _fill_registration(manager, t, 5)
        manager.close_registration(t.tournament_id)
        _full_checkin(manager, t, pids)
        manager.start_tournament(t.tournament_id)

        for _ in range(20):
            scheduled = [
                m for m in t.matches if m.status == MatchStatus.SCHEDULED
            ]
            if not scheduled:
                break
            for m in scheduled:
                winner = m.player_a_id or m.player_b_id
                assert winner is not None
                manager.report_match_result(t.tournament_id, m.match_id, winner)

        assert t.status == TournamentStatus.COMPLETED
        assert t.champion_id is not None


# ---------------------------------------------------------------------------
# Tests: admin actions
# ---------------------------------------------------------------------------


class TestAdminActions:
    def test_pause_and_resume_tournament(self):
        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager)

        assert manager.pause_tournament(t.tournament_id) == TournamentResult.SUCCESS
        assert t.status == TournamentStatus.PAUSED

        assert manager.resume_tournament(t.tournament_id) == TournamentResult.SUCCESS
        assert t.status == TournamentStatus.IN_PROGRESS

    def test_pause_requires_in_progress(self):
        manager = _make_manager()
        t = _make_8_player_tournament(manager)
        r = manager.pause_tournament(t.tournament_id)
        assert r == TournamentResult.INVALID_STATE

    def test_resume_requires_paused(self):
        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager)
        r = manager.resume_tournament(t.tournament_id)
        assert r == TournamentResult.INVALID_STATE

    def test_cancel_tournament(self):
        manager = _make_manager()
        t = _make_8_player_tournament(manager)
        r = manager.cancel_tournament(t.tournament_id, reason="Test cancelled")
        assert r == TournamentResult.SUCCESS
        assert t.status == TournamentStatus.CANCELLED
        assert t.cancel_reason == "Test cancelled"

    def test_cancel_completed_tournament_fails(self):
        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager)
        for _ in range(10):
            for m in [x for x in t.matches if x.status == MatchStatus.SCHEDULED]:
                manager.report_match_result(
                    t.tournament_id, m.match_id, m.player_a_id or m.player_b_id
                )
            if t.status == TournamentStatus.COMPLETED:
                break
        assert t.status == TournamentStatus.COMPLETED
        r = manager.cancel_tournament(t.tournament_id)
        assert r == TournamentResult.INVALID_STATE

    def test_force_report_result_admin_only(self):
        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager)
        m = next(m for m in t.matches if m.status == MatchStatus.SCHEDULED)
        r = manager.force_report_result(
            t.tournament_id, m.match_id, m.player_a_id, admin=False
        )
        assert r == TournamentResult.UNAUTHORIZED

    def test_force_report_result_success(self):
        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager)
        m = next(m for m in t.matches if m.status == MatchStatus.SCHEDULED)
        winner = m.player_b_id
        r = manager.force_report_result(
            t.tournament_id, m.match_id, winner, admin=True
        )
        assert r == TournamentResult.SUCCESS
        assert m.winner_id == winner
        assert m.status == MatchStatus.COMPLETED

    def test_force_report_already_completed_returns_duplicate(self):
        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager)
        m = next(m for m in t.matches if m.status == MatchStatus.SCHEDULED)
        manager.force_report_result(
            t.tournament_id, m.match_id, m.player_a_id, admin=True
        )
        r = manager.force_report_result(
            t.tournament_id, m.match_id, m.player_a_id, admin=True
        )
        assert r == TournamentResult.DUPLICATE_RESULT

    def test_disqualify_participant_requires_admin(self):
        manager = _make_manager()
        t, pids = _setup_ready_tournament(manager)
        r = manager.disqualify_participant(
            t.tournament_id, pids[0], admin=False
        )
        assert r == TournamentResult.UNAUTHORIZED

    def test_disqualify_advances_opponent(self):
        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager)
        m = next(m for m in t.matches if m.status == MatchStatus.SCHEDULED)
        dq_player = m.player_a_id
        expected_winner = m.player_b_id
        assert dq_player is not None and expected_winner is not None

        r = manager.disqualify_participant(
            t.tournament_id, dq_player, admin=True
        )
        assert r == TournamentResult.SUCCESS
        assert m.winner_id == expected_winner
        assert m.status == MatchStatus.COMPLETED

        participant = next(
            p for p in t.participants if p.player_id == dq_player
        )
        assert participant.disqualified
        assert participant.disqualified_at is not None

    def test_disqualify_double_dq_rejected(self):
        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager)
        m = next(m for m in t.matches if m.status == MatchStatus.SCHEDULED)
        dq_player = m.player_a_id
        assert dq_player is not None

        manager.disqualify_participant(t.tournament_id, dq_player, admin=True)
        r = manager.disqualify_participant(
            t.tournament_id, dq_player, admin=True
        )
        assert r == TournamentResult.DISQUALIFIED

    def test_disqualify_unregistered_player(self):
        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager)
        r = manager.disqualify_participant(
            t.tournament_id, uuid4(), admin=True
        )
        assert r == TournamentResult.NOT_REGISTERED

    def test_report_result_still_works_when_paused(self):
        """Match results can still be submitted while tournament is paused."""
        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager)
        manager.pause_tournament(t.tournament_id)
        m = next(m for m in t.matches if m.status == MatchStatus.SCHEDULED)
        r = manager.report_match_result(
            t.tournament_id, m.match_id, m.player_a_id
        )
        assert r == TournamentResult.SUCCESS


# ---------------------------------------------------------------------------
# Tests: events
# ---------------------------------------------------------------------------


class TestEvents:
    def test_tournament_created_event_published(self):
        manager = _make_manager()
        events: list = []
        manager.event_bus.subscribe(
            "tournament_created", lambda p: events.append(p)
        )
        manager.create_tournament("E1", 8, tournament_seed=1)
        assert len(events) == 1

    def test_registration_events_published(self):
        manager = _make_manager()
        t = _make_8_player_tournament(manager)
        open_events: list = []
        reg_events: list = []
        manager.event_bus.subscribe(
            "tournament_registration_opened", lambda p: open_events.append(p)
        )
        manager.event_bus.subscribe(
            "tournament_participant_registered", lambda p: reg_events.append(p)
        )
        manager.open_registration(t.tournament_id)
        manager.register_participant(t.tournament_id, uuid4(), "P")
        assert len(open_events) == 1
        assert len(reg_events) == 1

    def test_match_completed_event_published(self):
        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager)
        events: list = []
        manager.event_bus.subscribe(
            "tournament_match_completed", lambda p: events.append(p)
        )
        m = next(x for x in t.matches if x.status == MatchStatus.SCHEDULED)
        manager.report_match_result(t.tournament_id, m.match_id, m.player_a_id)
        assert len(events) == 1
        assert events[0]["winner_id"] == str(m.player_a_id)

    def test_cancellation_event_includes_tournament(self):
        manager = _make_manager()
        t = _make_8_player_tournament(manager)
        events: list = []
        manager.event_bus.subscribe(
            "tournament_cancelled", lambda p: events.append(p)
        )
        manager.cancel_tournament(t.tournament_id, reason="Abandoned")
        assert len(events) == 1
        assert events[0].cancel_reason == "Abandoned"


# ---------------------------------------------------------------------------
# Tests: save / load round-trip
# ---------------------------------------------------------------------------


class TestSaveLoadRoundtrip:
    def test_empty_save_load(self):
        manager = _make_manager()
        saved = manager.save_log()
        restored = _make_manager()
        restored.load_log(saved)
        assert restored.tournaments == []

    def test_draft_tournament_round_trips(self):
        manager = _make_manager()
        _make_8_player_tournament(manager, seed=999)
        saved = manager.save_log()

        restored = _make_manager()
        restored.load_log(saved)
        assert len(restored.tournaments) == 1
        assert restored.tournaments[0].status == TournamentStatus.DRAFT
        assert restored.tournaments[0].tournament_seed == 999

    def test_policy_round_trips(self):
        manager = _make_manager()
        policy = TournamentPolicy(
            team_size=3,
            level_cap=30,
            turn_timer_seconds=45,
            reconnect_grace_seconds=60,
            duplicate_species_clause=False,
            no_show_timeout_seconds=120,
            min_viable_players=4,
        )
        manager.create_tournament("Policy Test", 8, policy=policy, tournament_seed=1)
        saved = manager.save_log()

        restored = _make_manager()
        restored.load_log(saved)
        p = restored.tournaments[0].policy
        assert p.team_size == 3
        assert p.level_cap == 30
        assert p.turn_timer_seconds == 45
        assert p.duplicate_species_clause is False
        assert p.min_viable_players == 4

    def test_in_progress_tournament_round_trips(self):
        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager, seed=5)
        m = next(x for x in t.matches if x.status == MatchStatus.SCHEDULED)
        manager.report_match_result(
            t.tournament_id, m.match_id, m.player_a_id, resolution_token="tok"
        )

        saved = manager.save_log()
        restored = _make_manager()
        restored.load_log(saved)

        assert len(restored.tournaments) == 1
        rt = restored.tournaments[0]
        assert rt.status == TournamentStatus.IN_PROGRESS
        assert len(rt.matches) == 7
        assert len(rt.bracket) == 7
        assert len(rt.participants) == 8

        restored_match = next(
            x for x in rt.matches if x.match_id == m.match_id
        )
        assert restored_match.status == MatchStatus.COMPLETED
        assert restored_match.resolution_token == "tok"

    def test_completed_tournament_round_trips_with_champion(self):
        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager, seed=42)

        for _ in range(10):
            for m in [x for x in t.matches if x.status == MatchStatus.SCHEDULED]:
                manager.report_match_result(
                    t.tournament_id, m.match_id, m.player_a_id or m.player_b_id
                )
            if t.status == TournamentStatus.COMPLETED:
                break

        champion_id = t.champion_id
        saved = manager.save_log()
        restored = _make_manager()
        restored.load_log(saved)

        rt = restored.tournaments[0]
        assert rt.status == TournamentStatus.COMPLETED
        assert rt.champion_id == champion_id

    def test_load_skips_malformed_tournament_entries(self):
        manager = _make_manager()
        data = {
            "tournaments": [
                {"bad": "data"},
                "not-a-dict",
                42,
                None,
            ]
        }
        manager.load_log(data)
        assert manager.tournaments == []

    def test_load_skips_malformed_participants_and_matches(self):
        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager, seed=1)
        saved = manager.save_log()

        raw_t = saved["tournaments"][0]
        raw_t["participants"].append({"bad": "data"})
        raw_t["participants"].append("garbage")
        raw_t["matches"].append({"bad": "data"})

        restored = _make_manager()
        restored.load_log(saved)
        rt = restored.tournaments[0]
        assert len(rt.participants) == 8
        assert len(rt.matches) == 7

    def test_naive_timestamps_coerced_to_utc(self):
        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager, seed=11)
        saved = manager.save_log()

        raw_t = saved["tournaments"][0]
        raw_t["created_at"] = "2025-06-15T10:30:00"
        for p in raw_t["participants"]:
            p["registered_at"] = "2025-06-15T10:30:00"

        restored = _make_manager()
        restored.load_log(saved)
        rt = restored.tournaments[0]
        assert rt.created_at.tzinfo is not None
        for p in rt.participants:
            assert p.registered_at.tzinfo is not None

    def test_multiple_tournaments_round_trip(self):
        manager = _make_manager()
        for i in range(3):
            manager.create_tournament(f"T{i}", 8, tournament_seed=i)

        saved = manager.save_log()
        restored = _make_manager()
        restored.load_log(saved)
        assert len(restored.tournaments) == 3
        names = {rt.name for rt in restored.tournaments}
        assert names == {"T0", "T1", "T2"}


# ---------------------------------------------------------------------------
# Tests: Participant and Match serialization
# ---------------------------------------------------------------------------


class TestSerializationEdgeCases:
    def test_participant_round_trips_with_all_fields(self):
        now = datetime.now(timezone.utc)
        p = Participant(
            player_id=uuid4(),
            display_name="Tester",
            registered_at=now,
            checked_in=True,
            seed=3,
            disqualified=True,
            disqualified_at=now,
        )
        restored = Participant.from_dict(p.to_dict())
        assert restored.player_id == p.player_id
        assert restored.display_name == "Tester"
        assert restored.checked_in is True
        assert restored.seed == 3
        assert restored.disqualified is True
        assert restored.disqualified_at is not None

    def test_match_round_trips_fully(self):
        now = datetime.now(timezone.utc)
        m = Match(
            match_id=uuid4(),
            round_index=1,
            match_index=0,
            player_a_id=uuid4(),
            player_b_id=uuid4(),
            winner_id=uuid4(),
            resolution_token="tok-xyz",
            status=MatchStatus.COMPLETED,
            is_bye=False,
            scheduled_at=now,
            resolved_at=now,
        )
        restored = Match.from_dict(m.to_dict())
        assert restored.match_id == m.match_id
        assert restored.winner_id == m.winner_id
        assert restored.resolution_token == "tok-xyz"
        assert restored.status == MatchStatus.COMPLETED
        assert restored.scheduled_at is not None
        assert restored.resolved_at is not None

    def test_match_round_trips_with_none_players(self):
        m = Match(
            match_id=uuid4(),
            round_index=0,
            match_index=0,
            player_a_id=uuid4(),
            player_b_id=None,
            status=MatchStatus.WALKOVER,
            is_bye=True,
        )
        restored = Match.from_dict(m.to_dict())
        assert restored.player_b_id is None
        assert restored.is_bye is True

    def test_bracket_node_round_trips_fully(self):
        node = BracketNode(
            position=4,
            round_index=1,
            match_index=0,
            match_id=uuid4(),
            feeds_into=6,
            slot_a_feeds_from=0,
            slot_b_feeds_from=1,
        )
        restored = BracketNode.from_dict(node.to_dict())
        assert restored.position == 4
        assert restored.feeds_into == 6
        assert restored.slot_a_feeds_from == 0
        assert restored.slot_b_feeds_from == 1

    def test_bracket_node_round_trips_with_nones(self):
        node = BracketNode(
            position=6,
            round_index=2,
            match_index=0,
            match_id=None,
            feeds_into=None,
            slot_a_feeds_from=None,
            slot_b_feeds_from=None,
        )
        restored = BracketNode.from_dict(node.to_dict())
        assert restored.feeds_into is None
        assert restored.slot_a_feeds_from is None

    def test_tournament_policy_round_trips(self):
        policy = TournamentPolicy(
            team_size=4,
            level_cap=40,
            turn_timer_seconds=30,
        )
        restored = TournamentPolicy.from_dict(policy.to_dict())
        assert restored.team_size == 4
        assert restored.level_cap == 40
        assert restored.turn_timer_seconds == 30


# ---------------------------------------------------------------------------
# Tests: SaveData integration
# ---------------------------------------------------------------------------


class TestSaveDataIntegration:
    def test_tournament_data_field_in_save_data(self):
        from tuxemon.save_state import SaveData

        save = SaveData()
        assert save.tournament_data == {}

    def test_tournament_data_field_accepts_tournament_log(self):
        from tuxemon.save_state import SaveData

        manager = _make_manager()
        t, _ = _setup_ready_tournament(manager, seed=1)
        saved_log = manager.save_log()

        save = SaveData(tournament_data=saved_log)
        restored = _make_manager()
        restored.load_log(save.tournament_data)
        assert len(restored.tournaments) == 1

    def test_missing_tournament_data_defaults_to_empty(self):
        from tuxemon.save_state import SaveData

        data = {
            "screenshot": None,
            "screenshot_width": None,
            "screenshot_height": None,
            "time": "2026-01-15 12:00",
            "version": 3,
            "npc_state": None,
        }
        save = SaveData(**data)
        assert save.tournament_data == {}

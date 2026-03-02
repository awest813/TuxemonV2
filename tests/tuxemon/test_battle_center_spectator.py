# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for SpectatorManager — Phase 2.2 read-only match streams.
"""

from __future__ import annotations

import pytest

from tuxemon.battle_center.spectator import (
    MatchClosedError,
    MatchEvent,
    MatchNotFoundError,
    MatchState,
    SpectatorManager,
)


@pytest.fixture
def mgr() -> SpectatorManager:
    return SpectatorManager()


# ---------------------------------------------------------------------------
# open_match
# ---------------------------------------------------------------------------


class TestOpenMatch:
    def test_opens_match_in_active_state(self, mgr):
        m = mgr.open_match("m1", "alice", "bob")
        assert m.state == MatchState.ACTIVE
        assert m.player_a == "alice"
        assert m.player_b == "bob"

    def test_duplicate_match_id_raises(self, mgr):
        mgr.open_match("m1", "alice", "bob")
        with pytest.raises(ValueError):
            mgr.open_match("m1", "carol", "dave")

    def test_match_count_increments(self, mgr):
        mgr.open_match("m1", "a", "b")
        mgr.open_match("m2", "c", "d")
        assert mgr.match_count() == 2

    def test_summary_has_required_keys(self, mgr):
        m = mgr.open_match("m1", "alice", "bob")
        s = m.summary()
        assert "match_id" in s
        assert "player_a" in s
        assert "player_b" in s
        assert "state" in s
        assert "spectator_count" in s
        assert "event_count" in s


# ---------------------------------------------------------------------------
# push_event
# ---------------------------------------------------------------------------


class TestPushEvent:
    def test_push_event_returns_match_event(self, mgr):
        mgr.open_match("m1", "alice", "bob")
        evt = mgr.push_event("m1", {"type": "turn", "turn": 1})
        assert isinstance(evt, MatchEvent)

    def test_event_sequence_increments(self, mgr):
        mgr.open_match("m1", "alice", "bob")
        e1 = mgr.push_event("m1", {"n": 1})
        e2 = mgr.push_event("m1", {"n": 2})
        assert e1.sequence == 1
        assert e2.sequence == 2

    def test_push_event_to_unknown_match_raises(self, mgr):
        with pytest.raises(MatchNotFoundError):
            mgr.push_event("ghost", {})

    def test_push_event_to_closed_match_raises(self, mgr):
        mgr.open_match("m1", "alice", "bob")
        mgr.close_match("m1")
        with pytest.raises(MatchClosedError):
            mgr.push_event("m1", {})


# ---------------------------------------------------------------------------
# close_match
# ---------------------------------------------------------------------------


class TestCloseMatch:
    def test_closes_active_match(self, mgr):
        mgr.open_match("m1", "alice", "bob")
        m = mgr.close_match("m1")
        assert m.state == MatchState.CLOSED

    def test_closed_at_set_on_close(self, mgr):
        mgr.open_match("m1", "alice", "bob")
        m = mgr.close_match("m1")
        assert m.closed_at is not None

    def test_close_unknown_match_raises(self, mgr):
        with pytest.raises(MatchNotFoundError):
            mgr.close_match("ghost")

    def test_close_already_closed_raises(self, mgr):
        mgr.open_match("m1", "alice", "bob")
        mgr.close_match("m1")
        with pytest.raises(MatchClosedError):
            mgr.close_match("m1")


# ---------------------------------------------------------------------------
# register_spectator / unregister_spectator
# ---------------------------------------------------------------------------


class TestSpectators:
    def test_register_spectator(self, mgr):
        mgr.open_match("m1", "alice", "bob")
        mgr.register_spectator("m1", "charlie")
        assert mgr.spectator_count("m1") == 1

    def test_register_spectator_idempotent(self, mgr):
        mgr.open_match("m1", "alice", "bob")
        mgr.register_spectator("m1", "charlie")
        mgr.register_spectator("m1", "charlie")
        assert mgr.spectator_count("m1") == 1

    def test_multiple_spectators(self, mgr):
        mgr.open_match("m1", "alice", "bob")
        mgr.register_spectator("m1", "charlie")
        mgr.register_spectator("m1", "dave")
        assert mgr.spectator_count("m1") == 2

    def test_cannot_join_closed_match(self, mgr):
        mgr.open_match("m1", "alice", "bob")
        mgr.close_match("m1")
        with pytest.raises(MatchClosedError):
            mgr.register_spectator("m1", "charlie")

    def test_unregister_returns_true_when_registered(self, mgr):
        mgr.open_match("m1", "alice", "bob")
        mgr.register_spectator("m1", "charlie")
        assert mgr.unregister_spectator("m1", "charlie") is True

    def test_unregister_returns_false_when_not_registered(self, mgr):
        mgr.open_match("m1", "alice", "bob")
        assert mgr.unregister_spectator("m1", "nobody") is False

    def test_unregister_removes_spectator(self, mgr):
        mgr.open_match("m1", "alice", "bob")
        mgr.register_spectator("m1", "charlie")
        mgr.unregister_spectator("m1", "charlie")
        assert mgr.spectator_count("m1") == 0

    def test_register_unknown_match_raises(self, mgr):
        with pytest.raises(MatchNotFoundError):
            mgr.register_spectator("ghost", "charlie")

    def test_unregister_unknown_match_raises(self, mgr):
        with pytest.raises(MatchNotFoundError):
            mgr.unregister_spectator("ghost", "charlie")


# ---------------------------------------------------------------------------
# get_feed
# ---------------------------------------------------------------------------


class TestGetFeed:
    def test_empty_feed_on_new_match(self, mgr):
        mgr.open_match("m1", "alice", "bob")
        assert mgr.get_feed("m1") == []

    def test_full_feed_returned(self, mgr):
        mgr.open_match("m1", "alice", "bob")
        mgr.push_event("m1", {"n": 1})
        mgr.push_event("m1", {"n": 2})
        assert len(mgr.get_feed("m1")) == 2

    def test_from_sequence_filters_old_events(self, mgr):
        mgr.open_match("m1", "alice", "bob")
        mgr.push_event("m1", {"n": 1})
        mgr.push_event("m1", {"n": 2})
        mgr.push_event("m1", {"n": 3})
        feed = mgr.get_feed("m1", from_sequence=1)
        assert len(feed) == 2
        assert feed[0].sequence == 2

    def test_feed_readable_after_close(self, mgr):
        mgr.open_match("m1", "alice", "bob")
        mgr.push_event("m1", {"n": 1})
        mgr.close_match("m1")
        assert len(mgr.get_feed("m1")) == 1

    def test_get_feed_unknown_match_raises(self, mgr):
        with pytest.raises(MatchNotFoundError):
            mgr.get_feed("ghost")


# ---------------------------------------------------------------------------
# list_active_matches
# ---------------------------------------------------------------------------


class TestListActiveMatches:
    def test_only_active_matches_listed(self, mgr):
        mgr.open_match("m1", "alice", "bob")
        mgr.open_match("m2", "carol", "dave")
        mgr.close_match("m1")
        active = mgr.list_active_matches()
        assert len(active) == 1
        assert active[0]["match_id"] == "m2"

    def test_empty_when_no_active_matches(self, mgr):
        assert mgr.list_active_matches() == []

# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for MatchmakingEngine — Phase 2.2.
"""
from __future__ import annotations

import pytest

from tuxemon.battle_center.lobby import LobbyManager, LobbyStatus
from tuxemon.battle_center.matchmaking import (
    MatchmakingEngine,
    entries_compatible,
)
from tuxemon.battle_center.lobby import LobbyEntry


# ---------------------------------------------------------------------------
# entries_compatible
# ---------------------------------------------------------------------------


def _entry(**kwargs) -> LobbyEntry:
    defaults = dict(
        player_id="x",
        ruleset="default",
        format="single",
        skill_band="open",
        region="any",
    )
    defaults.update(kwargs)
    return LobbyEntry(**defaults)


class TestEntriesCompatible:
    def test_identical_entries_compatible(self):
        a = _entry(player_id="a", ruleset="default", format="single", skill_band="open", region="any")
        b = _entry(player_id="b", ruleset="default", format="single", skill_band="open", region="any")
        assert entries_compatible(a, b) is True

    def test_different_ruleset_incompatible(self):
        a = _entry(player_id="a", ruleset="default")
        b = _entry(player_id="b", ruleset="no_items")
        assert entries_compatible(a, b) is False

    def test_different_format_incompatible(self):
        a = _entry(player_id="a", format="single")
        b = _entry(player_id="b", format="double")
        assert entries_compatible(a, b) is False

    def test_same_skill_band_compatible(self):
        a = _entry(player_id="a", skill_band="expert")
        b = _entry(player_id="b", skill_band="expert")
        assert entries_compatible(a, b) is True

    def test_different_skill_bands_incompatible(self):
        a = _entry(player_id="a", skill_band="beginner")
        b = _entry(player_id="b", skill_band="expert")
        assert entries_compatible(a, b) is False

    def test_open_skill_band_matches_any(self):
        a = _entry(player_id="a", skill_band="open")
        b = _entry(player_id="b", skill_band="expert")
        assert entries_compatible(a, b) is True

    def test_both_open_skill_compatible(self):
        a = _entry(player_id="a", skill_band="open")
        b = _entry(player_id="b", skill_band="open")
        assert entries_compatible(a, b) is True

    def test_same_region_compatible(self):
        a = _entry(player_id="a", region="eu")
        b = _entry(player_id="b", region="eu")
        assert entries_compatible(a, b) is True

    def test_different_regions_incompatible(self):
        a = _entry(player_id="a", region="eu")
        b = _entry(player_id="b", region="us")
        assert entries_compatible(a, b) is False

    def test_any_region_matches_specific(self):
        a = _entry(player_id="a", region="any")
        b = _entry(player_id="b", region="eu")
        assert entries_compatible(a, b) is True

    def test_both_any_region_compatible(self):
        a = _entry(player_id="a", region="any")
        b = _entry(player_id="b", region="any")
        assert entries_compatible(a, b) is True

    def test_all_filters_must_pass(self):
        a = _entry(player_id="a", ruleset="default", format="single", skill_band="open", region="any")
        b = _entry(player_id="b", ruleset="no_items", format="single", skill_band="open", region="any")
        assert entries_compatible(a, b) is False


# ---------------------------------------------------------------------------
# MatchmakingEngine
# ---------------------------------------------------------------------------


@pytest.fixture
def lobby():
    return LobbyManager()


@pytest.fixture
def engine(lobby):
    return MatchmakingEngine(lobby)


class TestMatchmakingEngine:
    def test_empty_queue_returns_no_matches(self, engine):
        assert engine.run_cycle() == []

    def test_single_player_returns_no_matches(self, lobby, engine):
        lobby.join_queue("alice")
        assert engine.run_cycle() == []

    def test_two_compatible_players_matched(self, lobby, engine):
        lobby.join_queue("alice", ruleset="default", format="single")
        lobby.join_queue("bob", ruleset="default", format="single")
        matches = engine.run_cycle()
        assert len(matches) == 1
        assert set(matches[0]) == {"alice", "bob"}

    def test_matched_players_removed_from_queue(self, lobby, engine):
        lobby.join_queue("alice")
        lobby.join_queue("bob")
        engine.run_cycle()
        assert lobby.queue_size() == 0

    def test_matched_players_have_matched_status(self, lobby, engine):
        lobby.join_queue("alice")
        lobby.join_queue("bob")
        engine.run_cycle()
        assert lobby.get_status("alice") == LobbyStatus.MATCHED
        assert lobby.get_status("bob") == LobbyStatus.MATCHED

    def test_incompatible_players_not_matched(self, lobby, engine):
        lobby.join_queue("alice", format="single")
        lobby.join_queue("bob", format="double")
        matches = engine.run_cycle()
        assert matches == []
        assert lobby.queue_size() == 2

    def test_four_players_two_pairs_matched(self, lobby, engine):
        lobby.join_queue("p1", ruleset="default", format="single")
        lobby.join_queue("p2", ruleset="default", format="single")
        lobby.join_queue("p3", ruleset="default", format="single")
        lobby.join_queue("p4", ruleset="default", format="single")
        matches = engine.run_cycle()
        assert len(matches) == 2
        assert lobby.queue_size() == 0

    def test_mixed_compatible_and_incompatible(self, lobby, engine):
        lobby.join_queue("alice", format="single", ruleset="default")
        lobby.join_queue("bob", format="double", ruleset="default")
        lobby.join_queue("carol", format="single", ruleset="default")
        matches = engine.run_cycle()
        assert len(matches) == 1
        ids = set(matches[0])
        assert "alice" in ids
        assert "carol" in ids
        assert lobby.queue_size() == 1
        assert lobby.get_entry("bob") is not None

    def test_region_filter_respected(self, lobby, engine):
        lobby.join_queue("alice", region="eu")
        lobby.join_queue("bob", region="us")
        matches = engine.run_cycle()
        assert matches == []

    def test_region_any_allows_cross_region_match(self, lobby, engine):
        lobby.join_queue("alice", region="any")
        lobby.join_queue("bob", region="eu")
        matches = engine.run_cycle()
        assert len(matches) == 1

    def test_skill_band_open_bridges_mismatch(self, lobby, engine):
        lobby.join_queue("alice", skill_band="open")
        lobby.join_queue("bob", skill_band="expert")
        matches = engine.run_cycle()
        assert len(matches) == 1

    def test_each_player_matched_at_most_once_per_cycle(self, lobby, engine):
        for i in range(5):
            lobby.join_queue(f"p{i}")
        matches = engine.run_cycle()
        matched_ids: list[str] = []
        for a, b in matches:
            matched_ids.extend([a, b])
        assert len(matched_ids) == len(set(matched_ids))

    def test_opponent_recorded_correctly(self, lobby, engine):
        lobby.join_queue("alice")
        lobby.join_queue("bob")
        engine.run_cycle()
        assert lobby.get_match_opponent("alice") == "bob"
        assert lobby.get_match_opponent("bob") == "alice"

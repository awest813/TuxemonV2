# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for the Battle Center LobbyManager — Phase 2.2 scaffold.

Verifies the queue lifecycle, status tracking, and match pairing
as specified in docs/gold_silver_blueprint.md and the Phase 2.2 scaffold.
"""
from __future__ import annotations

import pytest

from tuxemon.battle_center.lobby import (
    LobbyEntry,
    LobbyManager,
    LobbyStatus,
)


@pytest.fixture
def lobby() -> LobbyManager:
    return LobbyManager()


# ---------------------------------------------------------------------------
# LobbyEntry validation
# ---------------------------------------------------------------------------


def test_lobby_entry_valid_single():
    entry = LobbyEntry(player_id="player_1", format="single")
    assert entry.player_id == "player_1"
    assert entry.format == "single"


def test_lobby_entry_valid_double():
    entry = LobbyEntry(player_id="player_1", format="double")
    assert entry.format == "double"


def test_lobby_entry_invalid_format_raises():
    with pytest.raises(ValueError):
        LobbyEntry(player_id="player_1", format="triple")


def test_lobby_entry_to_dict():
    entry = LobbyEntry(player_id="p", ruleset="no_items", format="double")
    d = entry.to_dict()
    assert d["player_id"] == "p"
    assert d["ruleset"] == "no_items"
    assert d["format"] == "double"


# ---------------------------------------------------------------------------
# join_queue
# ---------------------------------------------------------------------------


def test_join_queue_returns_entry(lobby: LobbyManager):
    entry = lobby.join_queue("player_1")
    assert isinstance(entry, LobbyEntry)
    assert entry.player_id == "player_1"


def test_join_queue_status_searching(lobby: LobbyManager):
    lobby.join_queue("player_1")
    assert lobby.get_status("player_1") == LobbyStatus.SEARCHING


def test_join_queue_increments_size(lobby: LobbyManager):
    lobby.join_queue("player_1")
    lobby.join_queue("player_2")
    assert lobby.queue_size() == 2


def test_join_queue_idempotent_re_entry(lobby: LobbyManager):
    lobby.join_queue("player_1", ruleset="default")
    lobby.join_queue("player_1", ruleset="no_items")
    assert lobby.queue_size() == 1
    entry = lobby.get_entry("player_1")
    assert entry is not None
    assert entry.ruleset == "no_items"


def test_join_queue_respects_options(lobby: LobbyManager):
    lobby.join_queue(
        "player_1",
        ruleset="no_items",
        format="double",
        skill_band="expert",
        region="eu",
    )
    entry = lobby.get_entry("player_1")
    assert entry is not None
    assert entry.ruleset == "no_items"
    assert entry.format == "double"
    assert entry.skill_band == "expert"
    assert entry.region == "eu"


# ---------------------------------------------------------------------------
# cancel
# ---------------------------------------------------------------------------


def test_cancel_returns_true_when_in_queue(lobby: LobbyManager):
    lobby.join_queue("player_1")
    assert lobby.cancel("player_1") is True


def test_cancel_returns_false_when_not_in_queue(lobby: LobbyManager):
    assert lobby.cancel("unknown_player") is False


def test_cancel_sets_status_cancelled(lobby: LobbyManager):
    lobby.join_queue("player_1")
    lobby.cancel("player_1")
    assert lobby.get_status("player_1") == LobbyStatus.CANCELLED


def test_cancel_removes_from_queue(lobby: LobbyManager):
    lobby.join_queue("player_1")
    lobby.cancel("player_1")
    assert lobby.queue_size() == 0
    assert lobby.get_entry("player_1") is None


# ---------------------------------------------------------------------------
# get_status
# ---------------------------------------------------------------------------


def test_status_idle_for_unknown_player(lobby: LobbyManager):
    assert lobby.get_status("nobody") == LobbyStatus.IDLE


# ---------------------------------------------------------------------------
# match
# ---------------------------------------------------------------------------


def test_match_returns_true_when_both_in_queue(lobby: LobbyManager):
    lobby.join_queue("player_a")
    lobby.join_queue("player_b")
    assert lobby.match("player_a", "player_b") is True


def test_match_sets_status_matched(lobby: LobbyManager):
    lobby.join_queue("player_a")
    lobby.join_queue("player_b")
    lobby.match("player_a", "player_b")
    assert lobby.get_status("player_a") == LobbyStatus.MATCHED
    assert lobby.get_status("player_b") == LobbyStatus.MATCHED


def test_match_removes_from_queue(lobby: LobbyManager):
    lobby.join_queue("player_a")
    lobby.join_queue("player_b")
    lobby.match("player_a", "player_b")
    assert lobby.queue_size() == 0


def test_match_records_opponent(lobby: LobbyManager):
    lobby.join_queue("player_a")
    lobby.join_queue("player_b")
    lobby.match("player_a", "player_b")
    assert lobby.get_match_opponent("player_a") == "player_b"
    assert lobby.get_match_opponent("player_b") == "player_a"


def test_match_returns_false_when_one_not_in_queue(lobby: LobbyManager):
    lobby.join_queue("player_a")
    assert lobby.match("player_a", "player_b") is False


def test_match_returns_false_when_both_not_in_queue(lobby: LobbyManager):
    assert lobby.match("player_a", "player_b") is False


# ---------------------------------------------------------------------------
# queue_snapshot
# ---------------------------------------------------------------------------


def test_queue_snapshot_returns_all_entries(lobby: LobbyManager):
    lobby.join_queue("player_1")
    lobby.join_queue("player_2")
    snapshot = lobby.queue_snapshot()
    ids = {e.player_id for e in snapshot}
    assert ids == {"player_1", "player_2"}


def test_queue_snapshot_empty_when_no_players(lobby: LobbyManager):
    assert lobby.queue_snapshot() == []

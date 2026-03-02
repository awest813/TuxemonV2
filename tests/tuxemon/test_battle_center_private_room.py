# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for PrivateRoomManager — Phase 2.2 direct-challenge rooms.
"""

from __future__ import annotations

import pytest

from tuxemon.battle_center.private_room import (
    PrivateRoom,
    PrivateRoomManager,
    RoomAlreadyFinalizedError,
    RoomNotFoundError,
    RoomStatus,
    UnauthorizedRoomAction,
)


@pytest.fixture
def mgr() -> PrivateRoomManager:
    return PrivateRoomManager()


# ---------------------------------------------------------------------------
# PrivateRoom construction
# ---------------------------------------------------------------------------


class TestPrivateRoomConstruction:
    def test_valid_room_created(self, mgr):
        room = mgr.create_room("alice", "bob")
        assert room.host_id == "alice"
        assert room.guest_id == "bob"
        assert room.status == RoomStatus.PENDING

    def test_room_code_is_not_empty(self, mgr):
        room = mgr.create_room("alice", "bob")
        assert len(room.room_code) > 0

    def test_room_code_uppercase_alphanumeric(self, mgr):
        room = mgr.create_room("alice", "bob")
        assert room.room_code.isalnum()
        assert room.room_code == room.room_code.upper()

    def test_invalid_format_raises(self):
        with pytest.raises(ValueError):
            PrivateRoom(
                room_code="TEST01",
                host_id="alice",
                guest_id="bob",
                format="triple",
            )

    def test_self_challenge_raises(self):
        with pytest.raises(ValueError):
            PrivateRoom(
                room_code="TEST01",
                host_id="alice",
                guest_id="alice",
            )

    def test_empty_host_raises(self):
        with pytest.raises(ValueError):
            PrivateRoom(room_code="TEST01", host_id="", guest_id="bob")

    def test_empty_guest_raises(self):
        with pytest.raises(ValueError):
            PrivateRoom(room_code="TEST01", host_id="alice", guest_id="")

    def test_room_defaults(self, mgr):
        room = mgr.create_room("alice", "bob")
        assert room.ruleset == "default"
        assert room.format == "single"

    def test_custom_options(self, mgr):
        room = mgr.create_room(
            "alice", "bob", ruleset="no_items", format="double"
        )
        assert room.ruleset == "no_items"
        assert room.format == "double"

    def test_to_dict_keys(self, mgr):
        room = mgr.create_room("alice", "bob")
        d = room.to_dict()
        assert "room_code" in d
        assert "host_id" in d
        assert "guest_id" in d
        assert "status" in d


# ---------------------------------------------------------------------------
# get_room
# ---------------------------------------------------------------------------


class TestGetRoom:
    def test_get_room_returns_room(self, mgr):
        room = mgr.create_room("alice", "bob")
        assert mgr.get_room(room.room_code) is room

    def test_get_room_unknown_returns_none(self, mgr):
        assert mgr.get_room("XXXXXX") is None


# ---------------------------------------------------------------------------
# accept_room
# ---------------------------------------------------------------------------


class TestAcceptRoom:
    def test_guest_can_accept(self, mgr):
        room = mgr.create_room("alice", "bob")
        accepted = mgr.accept_room(room.room_code, "bob")
        assert accepted.status == RoomStatus.CONFIRMED

    def test_non_guest_cannot_accept(self, mgr):
        room = mgr.create_room("alice", "bob")
        with pytest.raises(UnauthorizedRoomAction):
            mgr.accept_room(room.room_code, "charlie")

    def test_host_cannot_accept_own_room(self, mgr):
        room = mgr.create_room("alice", "bob")
        with pytest.raises(UnauthorizedRoomAction):
            mgr.accept_room(room.room_code, "alice")

    def test_accept_unknown_room_raises(self, mgr):
        with pytest.raises(RoomNotFoundError):
            mgr.accept_room("XXXXXX", "bob")

    def test_cannot_accept_already_confirmed(self, mgr):
        room = mgr.create_room("alice", "bob")
        mgr.accept_room(room.room_code, "bob")
        with pytest.raises(RoomAlreadyFinalizedError):
            mgr.accept_room(room.room_code, "bob")

    def test_cannot_accept_declined_room(self, mgr):
        room = mgr.create_room("alice", "bob")
        mgr.decline_room(room.room_code, "bob")
        with pytest.raises(RoomAlreadyFinalizedError):
            mgr.accept_room(room.room_code, "bob")


# ---------------------------------------------------------------------------
# decline_room
# ---------------------------------------------------------------------------


class TestDeclineRoom:
    def test_guest_can_decline(self, mgr):
        room = mgr.create_room("alice", "bob")
        declined = mgr.decline_room(room.room_code, "bob")
        assert declined.status == RoomStatus.DECLINED

    def test_host_cannot_decline(self, mgr):
        room = mgr.create_room("alice", "bob")
        with pytest.raises(UnauthorizedRoomAction):
            mgr.decline_room(room.room_code, "alice")

    def test_non_guest_cannot_decline(self, mgr):
        room = mgr.create_room("alice", "bob")
        with pytest.raises(UnauthorizedRoomAction):
            mgr.decline_room(room.room_code, "eve")

    def test_decline_unknown_room_raises(self, mgr):
        with pytest.raises(RoomNotFoundError):
            mgr.decline_room("XXXXXX", "bob")

    def test_cannot_decline_already_finalized(self, mgr):
        room = mgr.create_room("alice", "bob")
        mgr.accept_room(room.room_code, "bob")
        with pytest.raises(RoomAlreadyFinalizedError):
            mgr.decline_room(room.room_code, "bob")


# ---------------------------------------------------------------------------
# cancel_room
# ---------------------------------------------------------------------------


class TestCancelRoom:
    def test_host_can_cancel(self, mgr):
        room = mgr.create_room("alice", "bob")
        cancelled = mgr.cancel_room(room.room_code, "alice")
        assert cancelled.status == RoomStatus.CANCELLED

    def test_guest_cannot_cancel(self, mgr):
        room = mgr.create_room("alice", "bob")
        with pytest.raises(UnauthorizedRoomAction):
            mgr.cancel_room(room.room_code, "bob")

    def test_cancel_unknown_room_raises(self, mgr):
        with pytest.raises(RoomNotFoundError):
            mgr.cancel_room("XXXXXX", "alice")

    def test_cannot_cancel_already_finalized(self, mgr):
        room = mgr.create_room("alice", "bob")
        mgr.accept_room(room.room_code, "bob")
        with pytest.raises(RoomAlreadyFinalizedError):
            mgr.cancel_room(room.room_code, "alice")


# ---------------------------------------------------------------------------
# list_rooms_for_player and active_room_count
# ---------------------------------------------------------------------------


class TestManagerHelpers:
    def test_list_rooms_for_host(self, mgr):
        room = mgr.create_room("alice", "bob")
        rooms = mgr.list_rooms_for_player("alice")
        assert room in rooms

    def test_list_rooms_for_guest(self, mgr):
        room = mgr.create_room("alice", "bob")
        rooms = mgr.list_rooms_for_player("bob")
        assert room in rooms

    def test_list_rooms_for_uninvolved_player(self, mgr):
        mgr.create_room("alice", "bob")
        assert mgr.list_rooms_for_player("charlie") == []

    def test_active_room_count_pending(self, mgr):
        mgr.create_room("a", "b")
        mgr.create_room("c", "d")
        assert mgr.active_room_count() == 2

    def test_active_room_count_after_finalization(self, mgr):
        r1 = mgr.create_room("a", "b")
        mgr.create_room("c", "d")
        mgr.accept_room(r1.room_code, "b")
        assert mgr.active_room_count() == 1

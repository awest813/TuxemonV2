# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Battle Center private room / direct-challenge system — Phase 2.2.

A private room lets one player (the *host*) invite a specific opponent
to a match without entering the public queue.  The invited player may
accept or decline.  If accepted, the :class:`PrivateRoomManager` marks
the room as ``CONFIRMED`` and both players can proceed to the battle
screen.  If declined or if the host cancels, the room is discarded.

Room lifecycle
--------------
1. Host calls :meth:`PrivateRoomManager.create_room` → ``PENDING``
2. Invited player calls :meth:`PrivateRoomManager.accept_room` → ``CONFIRMED``
   OR calls :meth:`PrivateRoomManager.decline_room` → ``DECLINED``
   OR host calls :meth:`PrivateRoomManager.cancel_room` → ``CANCELLED``

Room codes
----------
Each room receives a short, uppercase alphanumeric *room_code* that both
players share out-of-band (e.g. via chat).  Codes are unique within the
manager's lifetime.

Usage::

    mgr = PrivateRoomManager()
    room = mgr.create_room("alice", "bob", ruleset="no_items", format="double")
    print(room.room_code)  # e.g. "A1B2"

    mgr.accept_room(room.room_code, "bob")
    assert mgr.get_room(room.room_code).status == RoomStatus.CONFIRMED
"""

from __future__ import annotations

import logging
import random
import string
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

_CODE_CHARS = string.ascii_uppercase + string.digits
_CODE_LENGTH = 6


def _generate_code() -> str:
    return "".join(random.choices(_CODE_CHARS, k=_CODE_LENGTH))


class RoomStatus(Enum):
    """Lifecycle state of a private challenge room."""

    PENDING = "pending"
    CONFIRMED = "confirmed"
    DECLINED = "declined"
    CANCELLED = "cancelled"


@dataclass
class PrivateRoom:
    """
    A single direct-challenge room between two known players.

    Attributes:
        room_code:   Short alphanumeric identifier shared by both players.
        host_id:     Player ID of the room creator.
        guest_id:    Player ID of the invited opponent.
        ruleset:     Battle ruleset slug for the match.
        format:      ``"single"`` or ``"double"``.
        status:      Current lifecycle state (see :class:`RoomStatus`).
        created_at:  Timestamp when the room was created.
    """

    room_code: str
    host_id: str
    guest_id: str
    ruleset: str = "default"
    format: str = "single"
    status: RoomStatus = RoomStatus.PENDING
    created_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if self.format not in {"single", "double"}:
            raise ValueError(
                f"Invalid format {self.format!r}; expected 'single' or 'double'."
            )
        if not self.host_id or not self.guest_id:
            raise ValueError("host_id and guest_id must not be empty.")
        if self.host_id == self.guest_id:
            raise ValueError("A player cannot challenge themselves.")

    def to_dict(self) -> dict[str, Any]:
        """Serialise the room for network transport or logging."""
        return {
            "room_code": self.room_code,
            "host_id": self.host_id,
            "guest_id": self.guest_id,
            "ruleset": self.ruleset,
            "format": self.format,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
        }


class PrivateRoomError(Exception):
    """Base exception for private-room lifecycle violations."""


class RoomNotFoundError(PrivateRoomError):
    """Raised when an operation targets a non-existent room code."""


class RoomAlreadyFinalizedError(PrivateRoomError):
    """Raised when an operation targets a room that has already been resolved."""


class UnauthorizedRoomAction(PrivateRoomError):
    """Raised when a player attempts an action they are not permitted to take."""


class PrivateRoomManager:
    """
    Creates and tracks private challenge rooms.

    Each room has a unique :attr:`~PrivateRoom.room_code` that is handed
    to both players out-of-band so they can reference the same room.

    Parameters:
        max_code_attempts: How many times to retry code generation before
            raising ``RuntimeError`` (default 20, effectively unlimited
            for typical usage).
    """

    def __init__(self, max_code_attempts: int = 20) -> None:
        self._rooms: dict[str, PrivateRoom] = {}
        self._max_code_attempts = max_code_attempts

    def _unique_code(self) -> str:
        for _ in range(self._max_code_attempts):
            code = _generate_code()
            if code not in self._rooms:
                return code
        raise RuntimeError(
            "Could not generate a unique room code; too many active rooms."
        )

    def create_room(
        self,
        host_id: str,
        guest_id: str,
        ruleset: str = "default",
        format: str = "single",
    ) -> PrivateRoom:
        """
        Create a new private challenge room.

        Parameters:
            host_id:  Player ID of the room creator.
            guest_id: Player ID of the invited opponent.
            ruleset:  Battle ruleset slug.
            format:   ``"single"`` or ``"double"``.

        Returns:
            The newly created :class:`PrivateRoom` in ``PENDING`` state.

        Raises:
            ValueError: If ``host_id == guest_id`` or ``format`` is invalid.
        """
        code = self._unique_code()
        room = PrivateRoom(
            room_code=code,
            host_id=host_id,
            guest_id=guest_id,
            ruleset=ruleset,
            format=format,
        )
        self._rooms[code] = room
        logger.info(
            "Private room %s created: %s challenged %s",
            code,
            host_id,
            guest_id,
        )
        return room

    def get_room(self, room_code: str) -> PrivateRoom | None:
        """Return the room with the given code, or ``None`` if not found."""
        return self._rooms.get(room_code)

    def accept_room(self, room_code: str, player_id: str) -> PrivateRoom:
        """
        Accept a pending challenge as the guest player.

        Parameters:
            room_code: The room to accept.
            player_id: Must match ``room.guest_id``.

        Returns:
            The updated :class:`PrivateRoom` in ``CONFIRMED`` state.

        Raises:
            RoomNotFoundError: If the code does not exist.
            UnauthorizedRoomAction: If *player_id* is not the guest.
            RoomAlreadyFinalizedError: If the room is not in ``PENDING`` state.
        """
        room = self._require_room(room_code)
        self._require_pending(room)
        if player_id != room.guest_id:
            raise UnauthorizedRoomAction(
                f"Player {player_id!r} is not the invited guest for room {room_code!r}."
            )
        room.status = RoomStatus.CONFIRMED
        logger.info("Private room %s confirmed by %s", room_code, player_id)
        return room

    def decline_room(self, room_code: str, player_id: str) -> PrivateRoom:
        """
        Decline a pending challenge as the guest player.

        Parameters:
            room_code: The room to decline.
            player_id: Must match ``room.guest_id``.

        Returns:
            The updated :class:`PrivateRoom` in ``DECLINED`` state.

        Raises:
            RoomNotFoundError: If the code does not exist.
            UnauthorizedRoomAction: If *player_id* is not the guest.
            RoomAlreadyFinalizedError: If the room is not in ``PENDING`` state.
        """
        room = self._require_room(room_code)
        self._require_pending(room)
        if player_id != room.guest_id:
            raise UnauthorizedRoomAction(
                f"Player {player_id!r} is not the invited guest for room {room_code!r}."
            )
        room.status = RoomStatus.DECLINED
        logger.info("Private room %s declined by %s", room_code, player_id)
        return room

    def cancel_room(self, room_code: str, player_id: str) -> PrivateRoom:
        """
        Cancel a pending room as the host player.

        Parameters:
            room_code: The room to cancel.
            player_id: Must match ``room.host_id``.

        Returns:
            The updated :class:`PrivateRoom` in ``CANCELLED`` state.

        Raises:
            RoomNotFoundError: If the code does not exist.
            UnauthorizedRoomAction: If *player_id* is not the host.
            RoomAlreadyFinalizedError: If the room is not in ``PENDING`` state.
        """
        room = self._require_room(room_code)
        self._require_pending(room)
        if player_id != room.host_id:
            raise UnauthorizedRoomAction(
                f"Player {player_id!r} is not the host for room {room_code!r}."
            )
        room.status = RoomStatus.CANCELLED
        logger.info("Private room %s cancelled by %s", room_code, player_id)
        return room

    def list_rooms_for_player(self, player_id: str) -> list[PrivateRoom]:
        """Return all rooms (in any state) where *player_id* is host or guest."""
        return [
            r
            for r in self._rooms.values()
            if r.host_id == player_id or r.guest_id == player_id
        ]

    def active_room_count(self) -> int:
        """Return the number of rooms currently in ``PENDING`` state."""
        return sum(
            1 for r in self._rooms.values() if r.status == RoomStatus.PENDING
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_room(self, room_code: str) -> PrivateRoom:
        room = self._rooms.get(room_code)
        if room is None:
            raise RoomNotFoundError(f"No room found with code {room_code!r}.")
        return room

    def _require_pending(self, room: PrivateRoom) -> None:
        if room.status != RoomStatus.PENDING:
            raise RoomAlreadyFinalizedError(
                f"Room {room.room_code!r} is already {room.status.value}."
            )

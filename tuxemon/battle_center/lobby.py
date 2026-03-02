# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Battle Center public matchmaking lobby.

Phase 2.2 stub — all method signatures are final; full matchmaking logic and
WebSocket integration ship in Phase 2.2.  Downstream code may safely import
and call these methods; they return well-typed results and never raise.

Lobby flow:
    1. Player calls :meth:`LobbyManager.join_queue` with preferred options.
    2. The manager transitions them to ``SEARCHING``.
    3. A future matchmaker calls :meth:`LobbyManager.match` when two players
       are compatible; both transition to ``MATCHED``.
    4. Either player may call :meth:`LobbyManager.cancel` at any point before
       ``MATCHED`` is confirmed; they return to ``IDLE``.

Match filter dimensions (Phase 2.2):
    * ``ruleset`` — battle ruleset slug (e.g. ``"default"``, ``"no_items"``).
    * ``format``  — ``"single"`` or ``"double"``.
    * ``skill_band`` — open / beginner / intermediate / expert.
    * ``region``  — latency region tag or ``"any"``.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class LobbyStatus(Enum):
    """Current state of a player's lobby session."""

    IDLE = "idle"
    SEARCHING = "searching"
    MATCHED = "matched"
    CANCELLED = "cancelled"


@dataclass
class LobbyEntry:
    """
    A single player's position in the public matchmaking queue.

    All fields are validated on construction; invalid values raise
    ``ValueError`` to give the caller a clear error rather than silently
    producing a bad match.
    """

    player_id: str
    ruleset: str = "default"
    format: str = "single"
    skill_band: str = "open"
    region: str = "any"
    queued_at: datetime = field(default_factory=datetime.now)

    def __post_init__(self) -> None:
        if self.format not in {"single", "double"}:
            raise ValueError(
                f"Invalid format {self.format!r}; expected 'single' or 'double'."
            )

    def to_dict(self) -> dict[str, Any]:
        """Serialise for network transport."""
        return {
            "player_id": self.player_id,
            "ruleset": self.ruleset,
            "format": self.format,
            "skill_band": self.skill_band,
            "region": self.region,
            "queued_at": self.queued_at.isoformat(),
        }


class LobbyManager:
    """
    Battle Center public-queue and private-room manager.

    Tracks which players are searching for a match and exposes the interface
    that the Phase 2.2 matchmaker will use to pair and notify them.

    All methods are safe to call from any thread once Phase 2.2 replaces the
    in-memory store with a shared backend.
    """

    def __init__(self) -> None:
        self._queue: dict[str, LobbyEntry] = {}
        self._status: dict[str, LobbyStatus] = {}
        self._matches: dict[str, str] = {}

    # ------------------------------------------------------------------
    # Player-facing API
    # ------------------------------------------------------------------

    def join_queue(
        self,
        player_id: str,
        ruleset: str = "default",
        format: str = "single",
        skill_band: str = "open",
        region: str = "any",
    ) -> LobbyEntry:
        """
        Add *player_id* to the public matchmaking queue.

        If the player is already in the queue their entry is replaced with
        the new options (idempotent re-entry).

        Parameters:
            player_id:  Unique identifier for the queuing player.
            ruleset:    Battle ruleset slug.
            format:     ``"single"`` or ``"double"``.
            skill_band: Skill tier filter tag.
            region:     Latency region or ``"any"``.

        Returns:
            The created :class:`LobbyEntry`.
        """
        entry = LobbyEntry(
            player_id=player_id,
            ruleset=ruleset,
            format=format,
            skill_band=skill_band,
            region=region,
        )
        self._queue[player_id] = entry
        self._status[player_id] = LobbyStatus.SEARCHING
        logger.info("Player %s joined the battle-center queue", player_id)
        return entry

    def cancel(self, player_id: str) -> bool:
        """
        Remove *player_id* from the queue.

        Parameters:
            player_id: Player to remove.

        Returns:
            ``True`` if the player was in the queue and was removed;
            ``False`` if they were not in the queue.
        """
        if player_id not in self._queue:
            return False
        del self._queue[player_id]
        self._status[player_id] = LobbyStatus.CANCELLED
        self._matches.pop(player_id, None)
        logger.info("Player %s cancelled their battle-center queue", player_id)
        return True

    def get_status(self, player_id: str) -> LobbyStatus:
        """
        Return the current lobby status for *player_id*.

        Players who have never interacted with the lobby are ``IDLE``.
        """
        return self._status.get(player_id, LobbyStatus.IDLE)

    def get_entry(self, player_id: str) -> LobbyEntry | None:
        """Return the queue entry for *player_id*, or ``None`` if absent."""
        return self._queue.get(player_id)

    # ------------------------------------------------------------------
    # Matchmaker API (called by Phase 2.2 matchmaking service)
    # ------------------------------------------------------------------

    def match(self, player_a: str, player_b: str) -> bool:
        """
        Pair *player_a* and *player_b* as a confirmed match.

        Both players must currently be in ``SEARCHING`` state.

        Returns:
            ``True`` if both players were successfully matched;
            ``False`` if either player is no longer in the queue.
        """
        if player_a not in self._queue or player_b not in self._queue:
            logger.warning(
                "Cannot match %s and %s — one or both not in queue",
                player_a,
                player_b,
            )
            return False
        self._status[player_a] = LobbyStatus.MATCHED
        self._status[player_b] = LobbyStatus.MATCHED
        self._matches[player_a] = player_b
        self._matches[player_b] = player_a
        del self._queue[player_a]
        del self._queue[player_b]
        logger.info(
            "Battle-center match confirmed: %s vs %s", player_a, player_b
        )
        return True

    def get_match_opponent(self, player_id: str) -> str | None:
        """Return the opponent *player_id* was matched with, or ``None``."""
        return self._matches.get(player_id)

    # ------------------------------------------------------------------
    # Queue inspection
    # ------------------------------------------------------------------

    def queue_size(self) -> int:
        """Return the number of players currently searching for a match."""
        return len(self._queue)

    def queue_snapshot(self) -> list[LobbyEntry]:
        """Return a snapshot of all current queue entries (order unspecified)."""
        return list(self._queue.values())

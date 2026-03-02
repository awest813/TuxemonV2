# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Battle Center spectator system — Phase 2.2.

Provides read-only streams of active matches so that third-party observers
can watch ongoing battles without participating.

Design principles
-----------------
* Spectators have **no influence** on a match.  They may only join, leave,
  and read the event feed.
* Match state is modelled as an append-only ordered list of
  :class:`MatchEvent` records pushed by the match orchestrator.
* Any player (including match participants) may register as a spectator of
  any *active* match.
* When a match ends, :meth:`SpectatorManager.close_match` marks it
  closed; existing spectators may still read the full replay feed but no
  new spectators can join.

Usage::

    mgr = SpectatorManager()

    match_id = "match-001"
    mgr.open_match(match_id, player_a="alice", player_b="bob")

    mgr.register_spectator(match_id, "charlie")
    mgr.push_event(match_id, {"type": "turn", "turn": 1, "action": "tackle"})

    feed = mgr.get_feed(match_id)       # list of all MatchEvent so far
    mgr.close_match(match_id)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)


class MatchState(Enum):
    """Lifecycle state of a watched match."""

    ACTIVE = "active"
    CLOSED = "closed"


@dataclass
class MatchEvent:
    """
    A single read-only event pushed into a match's spectator feed.

    Attributes:
        sequence:    Monotonically increasing position in the feed (1-indexed).
        timestamp:   Wall-clock time when the event was pushed.
        payload:     Arbitrary dict describing the event (e.g. move, result).
    """

    sequence: int
    timestamp: datetime
    payload: dict[str, Any]


@dataclass
class WatchedMatch:
    """
    Internal record for a single match being tracked by :class:`SpectatorManager`.

    Attributes:
        match_id:    Unique identifier for the match.
        player_a:    Player ID of the first participant.
        player_b:    Player ID of the second participant.
        state:       Current match lifecycle state.
        spectators:  Set of player IDs currently watching.
        feed:        Ordered list of :class:`MatchEvent` records.
        opened_at:   Timestamp when the match was opened for spectation.
        closed_at:   Timestamp when the match was closed (``None`` if active).
    """

    match_id: str
    player_a: str
    player_b: str
    state: MatchState = MatchState.ACTIVE
    spectators: set[str] = field(default_factory=set)
    feed: list[MatchEvent] = field(default_factory=list)
    opened_at: datetime = field(default_factory=datetime.now)
    closed_at: datetime | None = None

    def summary(self) -> dict[str, Any]:
        """Return a lightweight dict suitable for a match browser listing."""
        return {
            "match_id": self.match_id,
            "player_a": self.player_a,
            "player_b": self.player_b,
            "state": self.state.value,
            "spectator_count": len(self.spectators),
            "event_count": len(self.feed),
            "opened_at": self.opened_at.isoformat(),
            "closed_at": (
                self.closed_at.isoformat() if self.closed_at else None
            ),
        }


class SpectatorError(Exception):
    """Base exception for spectator system violations."""


class MatchNotFoundError(SpectatorError):
    """Raised when an operation references a match_id that does not exist."""


class MatchClosedError(SpectatorError):
    """Raised when an operation requires the match to be active but it is closed."""


class SpectatorManager:
    """
    Manages spectator access to active and completed Battle Center matches.

    The manager owns the canonical list of open matches and their event feeds.
    Match orchestrators call :meth:`open_match`, :meth:`push_event`, and
    :meth:`close_match`; spectators call :meth:`register_spectator`,
    :meth:`unregister_spectator`, and :meth:`get_feed`.

    All operations are safe to call concurrently when protected by an
    external lock (Phase 2.2 will add asyncio-aware locking).
    """

    def __init__(self) -> None:
        self._matches: dict[str, WatchedMatch] = {}

    # ------------------------------------------------------------------
    # Match orchestrator API
    # ------------------------------------------------------------------

    def open_match(
        self, match_id: str, player_a: str, player_b: str
    ) -> WatchedMatch:
        """
        Register a new match as open for spectation.

        Parameters:
            match_id: Globally unique identifier for the match.
            player_a: Player ID of participant A.
            player_b: Player ID of participant B.

        Returns:
            The created :class:`WatchedMatch` in ``ACTIVE`` state.

        Raises:
            ValueError: If *match_id* is already registered.
        """
        if match_id in self._matches:
            raise ValueError(
                f"Match {match_id!r} is already registered with the SpectatorManager."
            )
        watched = WatchedMatch(
            match_id=match_id, player_a=player_a, player_b=player_b
        )
        self._matches[match_id] = watched
        logger.info(
            "SpectatorManager: match %s opened (%s vs %s)",
            match_id,
            player_a,
            player_b,
        )
        return watched

    def push_event(self, match_id: str, payload: dict[str, Any]) -> MatchEvent:
        """
        Append an event to the match's spectator feed.

        Parameters:
            match_id: The match to push the event to.
            payload:  Dict describing the event (contents are caller-defined).

        Returns:
            The created :class:`MatchEvent`.

        Raises:
            MatchNotFoundError: If *match_id* is unknown.
            MatchClosedError: If the match has already been closed.
        """
        match = self._require_match(match_id)
        self._require_active(match)

        seq = len(match.feed) + 1
        event = MatchEvent(
            sequence=seq, timestamp=datetime.now(), payload=payload
        )
        match.feed.append(event)
        logger.debug(
            "SpectatorManager: match %s event #%d pushed", match_id, seq
        )
        return event

    def close_match(self, match_id: str) -> WatchedMatch:
        """
        Mark a match as closed.

        Spectators can still read the full feed after closing; new
        spectators cannot join.

        Parameters:
            match_id: The match to close.

        Returns:
            The updated :class:`WatchedMatch` in ``CLOSED`` state.

        Raises:
            MatchNotFoundError: If *match_id* is unknown.
            MatchClosedError: If the match is already closed.
        """
        match = self._require_match(match_id)
        self._require_active(match)

        match.state = MatchState.CLOSED
        match.closed_at = datetime.now()
        logger.info(
            "SpectatorManager: match %s closed (%d events, %d spectators)",
            match_id,
            len(match.feed),
            len(match.spectators),
        )
        return match

    # ------------------------------------------------------------------
    # Spectator API
    # ------------------------------------------------------------------

    def register_spectator(
        self, match_id: str, spectator_id: str
    ) -> WatchedMatch:
        """
        Add *spectator_id* as a watcher of *match_id*.

        Registration is idempotent: re-registering has no effect.

        Parameters:
            match_id:     Match to watch.
            spectator_id: Player joining as a read-only observer.

        Returns:
            The :class:`WatchedMatch` being watched.

        Raises:
            MatchNotFoundError: If *match_id* is unknown.
            MatchClosedError: If the match is already closed.
        """
        match = self._require_match(match_id)
        self._require_active(match)

        match.spectators.add(spectator_id)
        logger.info(
            "SpectatorManager: %s joined match %s (%d spectators)",
            spectator_id,
            match_id,
            len(match.spectators),
        )
        return match

    def unregister_spectator(self, match_id: str, spectator_id: str) -> bool:
        """
        Remove *spectator_id* from the watcher list.

        Parameters:
            match_id:     Match to leave.
            spectator_id: Player leaving.

        Returns:
            ``True`` if the spectator was registered and has been removed;
            ``False`` if they were not registered.

        Raises:
            MatchNotFoundError: If *match_id* is unknown.
        """
        match = self._require_match(match_id)
        if spectator_id not in match.spectators:
            return False
        match.spectators.discard(spectator_id)
        logger.info(
            "SpectatorManager: %s left match %s", spectator_id, match_id
        )
        return True

    def get_feed(
        self, match_id: str, from_sequence: int = 0
    ) -> list[MatchEvent]:
        """
        Return the event feed for *match_id*, optionally starting from a
        given sequence number (exclusive, i.e. events *after* that sequence).

        Parameters:
            match_id:      The match whose feed to retrieve.
            from_sequence: Skip events with ``sequence <= from_sequence``.
                           Pass ``0`` (default) to get the full feed.

        Returns:
            Ordered list of :class:`MatchEvent`.

        Raises:
            MatchNotFoundError: If *match_id* is unknown.
        """
        match = self._require_match(match_id)
        return [e for e in match.feed if e.sequence > from_sequence]

    def spectator_count(self, match_id: str) -> int:
        """
        Return the number of registered spectators for *match_id*.

        Raises:
            MatchNotFoundError: If *match_id* is unknown.
        """
        return len(self._require_match(match_id).spectators)

    # ------------------------------------------------------------------
    # Match browser API
    # ------------------------------------------------------------------

    def list_active_matches(self) -> list[dict[str, Any]]:
        """
        Return summary dicts for all currently active matches.

        Suitable for populating a match browser UI.
        """
        return [
            m.summary()
            for m in self._matches.values()
            if m.state == MatchState.ACTIVE
        ]

    def match_count(self) -> int:
        """Return the total number of registered matches (active + closed)."""
        return len(self._matches)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _require_match(self, match_id: str) -> WatchedMatch:
        match = self._matches.get(match_id)
        if match is None:
            raise MatchNotFoundError(
                f"No match registered with id {match_id!r}."
            )
        return match

    def _require_active(self, match: WatchedMatch) -> None:
        if match.state != MatchState.ACTIVE:
            raise MatchClosedError(
                f"Match {match.match_id!r} is already {match.state.value}."
            )

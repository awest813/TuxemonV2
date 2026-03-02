# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Battle Center matchmaking engine — Phase 2.2.

Responsible for pairing queued players from :class:`LobbyManager` into
confirmed matches.  Compatibility is determined by comparing filter
dimensions (ruleset, format, skill_band, region) according to a
configurable policy.

Typical usage::

    from tuxemon.battle_center.lobby import LobbyManager
    from tuxemon.battle_center.matchmaking import MatchmakingEngine

    lobby = LobbyManager()
    engine = MatchmakingEngine(lobby)

    lobby.join_queue("alice", ruleset="default", format="single", skill_band="open")
    lobby.join_queue("bob",   ruleset="default", format="single", skill_band="open")

    matches = engine.run_cycle()
    # matches == [("alice", "bob")]

Compatibility rules
-------------------
* **ruleset** — must be identical.
* **format** — must be identical.
* **skill_band** — must be identical *or* either player set ``"open"``.
* **region** — must be identical *or* either player set ``"any"``.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from tuxemon.battle_center.lobby import LobbyEntry, LobbyManager

logger = logging.getLogger(__name__)

# Skill bands in ascending difficulty order (used for open/adjacent logic).
SKILL_BANDS = ["beginner", "intermediate", "expert"]


def _skill_compatible(a: str, b: str) -> bool:
    """Return True if the two skill bands can be matched."""
    if a == "open" or b == "open":
        return True
    return a == b


def _region_compatible(a: str, b: str) -> bool:
    """Return True if the two region tags can be matched."""
    if a == "any" or b == "any":
        return True
    return a == b


def entries_compatible(a: "LobbyEntry", b: "LobbyEntry") -> bool:
    """
    Return ``True`` if two :class:`~tuxemon.battle_center.lobby.LobbyEntry`
    objects can be paired.

    Two entries are compatible when:

    * Their ``ruleset`` values are equal.
    * Their ``format`` values are equal.
    * Their ``skill_band`` values are compatible (same or either is ``"open"``).
    * Their ``region`` values are compatible (same or either is ``"any"``).

    Parameters:
        a: First queue entry.
        b: Second queue entry.

    Returns:
        ``True`` if the entries can be paired, ``False`` otherwise.
    """
    if a.ruleset != b.ruleset:
        return False
    if a.format != b.format:
        return False
    if not _skill_compatible(a.skill_band, b.skill_band):
        return False
    if not _region_compatible(a.region, b.region):
        return False
    return True


class MatchmakingEngine:
    """
    Scans the :class:`~tuxemon.battle_center.lobby.LobbyManager` queue and
    pairs compatible players.

    Each call to :meth:`run_cycle` makes one pass through the queue,
    greedily matching the first compatible pair it finds and repeating until
    no more pairs remain in the current snapshot.

    The engine delegates the actual status update to :meth:`LobbyManager.match`
    so that the lobby remains the single source of truth.

    Parameters:
        lobby: The :class:`~tuxemon.battle_center.lobby.LobbyManager` to pull
            queue entries from and notify on match.
    """

    def __init__(self, lobby: "LobbyManager") -> None:
        self._lobby = lobby

    def run_cycle(self) -> list[tuple[str, str]]:
        """
        Perform one matchmaking pass over the current queue.

        Returns:
            A list of ``(player_a_id, player_b_id)`` tuples for every pair
            that was successfully matched in this cycle.  Players who could
            not be paired remain in the queue.
        """
        matched: list[tuple[str, str]] = []
        entries = self._lobby.queue_snapshot()

        # Track which player IDs we've already paired this cycle so we don't
        # try to pair the same player twice.
        paired: set[str] = set()

        for i, entry_a in enumerate(entries):
            if entry_a.player_id in paired:
                continue
            next_index = i + 1
            for entry_b in entries[next_index:]:
                if entry_b.player_id in paired:
                    continue
                if entries_compatible(entry_a, entry_b):
                    success = self._lobby.match(
                        entry_a.player_id, entry_b.player_id
                    )
                    if success:
                        paired.add(entry_a.player_id)
                        paired.add(entry_b.player_id)
                        matched.append((entry_a.player_id, entry_b.player_id))
                        logger.info(
                            "Matchmaking: paired %s vs %s",
                            entry_a.player_id,
                            entry_b.player_id,
                        )
                        break

        return matched

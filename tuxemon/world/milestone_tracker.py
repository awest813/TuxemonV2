# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Post-game milestone tracker.

Implements the milestone tier structure defined in
docs/gold_silver_blueprint.md §5 and fires Hook 4.9
(on_postgame_milestone_reached) when a player reaches each tier.

Tier definitions:
    0 - Story Complete   : credits roll after final boss.
    1 - Returner         : first rematch win against any trainer.
    2 - Battler          : 10 cumulative rematch wins.
    3 - Champion Challenger: win a tournament bracket (wired via Phase 2).
    4 - Completionist    : 80%+ monster journal completion.
    5 - Grand Champion   : clear the Battle Tower equivalent at max difficulty.

Tiers 3-5 require systems introduced in Phase 2/Phase 4; their detection
methods are stubs here that Phase 2+ systems can invoke directly.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from tuxemon.time_hooks import PostgameMilestonePayload, hooks

logger = logging.getLogger(__name__)

BATTLER_THRESHOLD = 10
COMPLETIONIST_DEX_PERCENT = 80.0
TOURNAMENT_UNLOCK_BATTLE_CENTER_WINS = 3


class PostgameMilestoneTracker:
    """
    Tracks post-game progression milestones for a single player and fires
    Hook 4.9 (``on_postgame_milestone_reached``) when each tier is first achieved.

    All milestone state is persisted through ``encode()`` / ``decode()`` so it
    survives save/load cycles.

    Tier 0 — ``story_complete`` — call :meth:`record_story_complete`.
    Tier 1 — ``returner``       — fires automatically on the first
                                   :meth:`record_rematch_win` call.
    Tier 2 — ``battler``        — fires when cumulative rematch wins reach
                                   ``BATTLER_THRESHOLD`` (default 10).
    Tier 3 — ``champion_challenger`` — call :meth:`record_tournament_win` or
                                        :meth:`record_ladder_threshold`.
    Tier 4 — ``completionist``  — call :meth:`record_dex_completion`.
    Tier 5 — ``grand_champion`` — call :meth:`record_battle_tower_cleared`.
    """

    def __init__(self, player_id: str) -> None:
        self.player_id = player_id
        self._achieved: set[str] = set()
        self._total_rematch_wins: int = 0
        self._story_complete: bool = False
        self._dex_completion_pct: float = 0.0
        self._battle_center_wins: int = 0
        self._battle_center_matches: int = 0
        self._tournament_unlocked: bool = False

    # ------------------------------------------------------------------
    # Milestone recording
    # ------------------------------------------------------------------

    def record_story_complete(self) -> None:
        """Mark the campaign story as finished; fires Tier 0 milestone."""
        self._story_complete = True
        self._try_fire("story_complete")

    def record_battle_center_match(self, *, won: bool) -> bool:
        """
        Record one post-credits Battle Center match.

        Returns:
            ``True`` when the result was accepted into progression state.
            ``False`` when the story has not been completed yet.
        """
        if not self._story_complete:
            return False
        self._battle_center_matches += 1
        if won:
            self._battle_center_wins += 1
            if (
                self._battle_center_wins
                >= TOURNAMENT_UNLOCK_BATTLE_CENTER_WINS
            ):
                self._tournament_unlocked = True
        return True

    def record_rematch_win(self) -> None:
        """
        Increment the cumulative rematch-win counter.

        Fires Tier 1 (``returner``) on the very first win.
        Fires Tier 2 (``battler``) when the running total reaches
        ``BATTLER_THRESHOLD``.
        """
        self._total_rematch_wins += 1
        self._try_fire("returner")
        if self._total_rematch_wins >= BATTLER_THRESHOLD:
            self._try_fire("battler")

    def record_tournament_win(self) -> bool:
        """
        Record a tournament bracket victory; fires Tier 3 milestone.

        Tournament progression is unlocked by completing the story and then
        winning enough Battle Center matches in the post-credits arc.
        """
        if not self._tournament_unlocked:
            return False
        self._try_fire("champion_challenger")
        return True

    def record_ladder_threshold(self) -> bool:
        """Record reaching the top-10 of the casual ladder; fires Tier 3."""
        if not self._tournament_unlocked:
            return False
        self._try_fire("champion_challenger")
        return True

    def record_dex_completion(self, completion_pct: float) -> None:
        """
        Update monster journal completion percentage.

        Fires Tier 4 (``completionist``) when *completion_pct* first reaches
        or exceeds ``COMPLETIONIST_DEX_PERCENT`` (default 80 %).

        Parameters:
            completion_pct: Current journal completion as a percentage [0, 100].
        """
        self._dex_completion_pct = completion_pct
        if completion_pct >= COMPLETIONIST_DEX_PERCENT:
            self._try_fire("completionist")

    def record_battle_tower_cleared(self) -> None:
        """Record clearing the Battle Tower equivalent; fires Tier 5 milestone."""
        self._try_fire("grand_champion")

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def is_achieved(self, milestone_id: str) -> bool:
        """Return True if *milestone_id* has already been reached."""
        return milestone_id in self._achieved

    @property
    def total_rematch_wins(self) -> int:
        """Total cumulative rematch wins recorded so far."""
        return self._total_rematch_wins

    @property
    def dex_completion_pct(self) -> float:
        """Last recorded monster journal completion percentage."""
        return self._dex_completion_pct

    @property
    def battle_center_wins(self) -> int:
        """Number of post-credits Battle Center wins."""
        return self._battle_center_wins

    @property
    def battle_center_matches(self) -> int:
        """Number of post-credits Battle Center matches played."""
        return self._battle_center_matches

    @property
    def tournament_unlocked(self) -> bool:
        """True when post-credits tournament progression is unlocked."""
        return self._tournament_unlocked

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _try_fire(self, milestone_id: str) -> None:
        """Fire the hook for *milestone_id* if not already achieved."""
        if milestone_id in self._achieved:
            return
        self._achieved.add(milestone_id)
        logger.info(
            "Post-game milestone reached: %s (player=%s)",
            milestone_id,
            self.player_id,
        )
        hooks.fire_postgame_milestone_reached(
            PostgameMilestonePayload(
                milestone_id=milestone_id,
                player_id=self.player_id,
                timestamp=datetime.now(),
            )
        )

    # ------------------------------------------------------------------
    # Save / load
    # ------------------------------------------------------------------

    def encode(self) -> dict[str, Any]:
        """Serialise milestone state for inclusion in the save file."""
        return {
            "achieved": sorted(self._achieved),
            "total_rematch_wins": self._total_rematch_wins,
            "story_complete": self._story_complete,
            "dex_completion_pct": self._dex_completion_pct,
            "battle_center_wins": self._battle_center_wins,
            "battle_center_matches": self._battle_center_matches,
            "tournament_unlocked": self._tournament_unlocked,
        }

    def decode(self, data: dict[str, Any]) -> None:
        """Restore milestone state from a previously encoded dict."""
        self._achieved = set(data.get("achieved", []))
        self._total_rematch_wins = int(data.get("total_rematch_wins", 0))
        self._story_complete = bool(data.get("story_complete", False))
        self._dex_completion_pct = float(data.get("dex_completion_pct", 0.0))
        self._battle_center_wins = int(data.get("battle_center_wins", 0))
        self._battle_center_matches = int(data.get("battle_center_matches", 0))
        self._tournament_unlocked = bool(
            data.get("tournament_unlocked", False)
        )

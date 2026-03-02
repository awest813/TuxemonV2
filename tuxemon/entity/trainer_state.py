# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Trainer state management for the rematch loop system.

Implements the trainer state model described in
docs/gold_silver_blueprint.md §3.1 and §3.2.
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from tuxemon.save_state import TIME_FORMAT, TrainerState
from tuxemon.time_hooks import RematchEligiblePayload, hooks

logger = logging.getLogger(__name__)

_REMATCH_COOLDOWN_HOURS = 24


class TrainerStateManager:
    """
    Manages the persistent state of all trainers encountered by a single NPC
    (typically the player character).

    Trainer state includes defeat status, rematch eligibility, and cooldowns,
    all of which are persisted in the save file under ``npc_state.trainer_states``.
    """

    def __init__(self) -> None:
        self._states: dict[str, TrainerState] = {}

    # ------------------------------------------------------------------
    # Read helpers
    # ------------------------------------------------------------------

    def get(self, trainer_id: str) -> TrainerState:
        """Return the state for *trainer_id*, creating it if absent."""
        if trainer_id not in self._states:
            self._states[trainer_id] = TrainerState(trainer_id=trainer_id)
        return self._states[trainer_id]

    def is_defeated(self, trainer_id: str) -> bool:
        return self.get(trainer_id).defeated

    def is_rematch_eligible(self, trainer_id: str) -> bool:
        return self.get(trainer_id).rematch_eligible

    def is_rematch_ready(
        self, trainer_id: str, cooldown_hours: int = _REMATCH_COOLDOWN_HOURS
    ) -> bool:
        """
        Return True when a rematch is immediately available.

        Conditions:
        1. Trainer is rematch-eligible.
        2. Cooldown since the last rematch has elapsed.
        """
        state = self.get(trainer_id)
        if not state.rematch_eligible:
            return False
        if state.last_rematch_at is None:
            return True
        try:
            last = datetime.strptime(state.last_rematch_at, TIME_FORMAT)
        except ValueError:
            logger.warning(
                "Unparseable last_rematch_at for trainer %s: %r",
                trainer_id,
                state.last_rematch_at,
            )
            return True
        elapsed_hours = (datetime.now() - last).total_seconds() / 3600
        return elapsed_hours >= cooldown_hours

    def trainer_ids(self) -> tuple[str, ...]:
        """Return all known trainer IDs tracked by this manager."""
        return tuple(self._states.keys())

    def evaluate_rematch_eligibility(
        self,
        trainer_id: str,
        *,
        badge_count: int = 0,
        required_badges: int = 0,
        required_milestones: tuple[str, ...] = (),
        milestone_checker: Any | None = None,
        player_id: str = "",
    ) -> bool:
        """
        Evaluate and persist rematch eligibility for one trainer.

        Eligibility requires all of the following:
        1. The trainer has been defeated at least once.
        2. The player has reached the badge threshold.
        3. Every required milestone is achieved.
        """
        state = self.get(trainer_id)
        milestones_met = True
        if required_milestones:
            if milestone_checker is None:
                milestones_met = False
            else:
                milestones_met = all(
                    bool(milestone_checker(mid))
                    for mid in required_milestones
                )

        eligible = (
            state.defeated
            and badge_count >= max(0, required_badges)
            and milestones_met
        )
        self.set_rematch_eligible(
            trainer_id=trainer_id,
            eligible=eligible,
            player_id=player_id,
        )
        return eligible

    # ------------------------------------------------------------------
    # Write helpers
    # ------------------------------------------------------------------

    def record_defeat(self, trainer_id: str) -> None:
        """Mark *trainer_id* as defeated (first encounter win)."""
        state = self.get(trainer_id)
        self._states[trainer_id] = TrainerState(
            trainer_id=trainer_id,
            defeated=True,
            last_rematch_at=state.last_rematch_at,
            rematch_count=state.rematch_count,
            rematch_eligible=state.rematch_eligible,
        )

    def set_rematch_eligible(
        self,
        trainer_id: str,
        eligible: bool,
        player_id: str = "",
    ) -> None:
        """
        Update rematch eligibility for *trainer_id*.

        When *eligible* is ``True`` and the trainer was not already eligible,
        fires Hook 4.6 (``on_rematch_eligible``) so content systems can add
        the trainer to the phone-contact call pool and enable rematch dialogue.

        Parameters:
            trainer_id: Stable identifier of the trainer NPC.
            eligible: New eligibility value.
            player_id: Slug of the owning player NPC (used in the hook payload).
        """
        state = self.get(trainer_id)
        was_eligible = state.rematch_eligible
        self._states[trainer_id] = TrainerState(
            trainer_id=trainer_id,
            defeated=state.defeated,
            last_rematch_at=state.last_rematch_at,
            rematch_count=state.rematch_count,
            rematch_eligible=eligible,
        )
        if eligible and not was_eligible:
            hooks.fire_rematch_eligible(
                RematchEligiblePayload(
                    trainer_id=trainer_id,
                    player_id=player_id,
                )
            )

    def record_rematch(self, trainer_id: str) -> None:
        """Increment the rematch counter and stamp the current time."""
        state = self.get(trainer_id)
        self._states[trainer_id] = TrainerState(
            trainer_id=trainer_id,
            defeated=state.defeated,
            last_rematch_at=datetime.now().strftime(TIME_FORMAT),
            rematch_count=state.rematch_count + 1,
            rematch_eligible=state.rematch_eligible,
        )

    # ------------------------------------------------------------------
    # Save / load
    # ------------------------------------------------------------------

    def encode(self) -> dict[str, Any]:
        """Serialise all trainer states for inclusion in the save file."""
        return {tid: s.model_dump() for tid, s in self._states.items()}

    def decode(self, data: dict[str, Any]) -> None:
        """Restore trainer states from a previously encoded dict."""
        self._states = {}
        for tid, raw in data.items():
            try:
                self._states[tid] = TrainerState(**raw)
            except Exception:
                logger.warning(
                    "Could not decode trainer state for %r: %r", tid, raw
                )

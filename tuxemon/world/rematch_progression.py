# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Progression-aware rematch eligibility coordinator.

This service re-evaluates trainer rematch eligibility whenever player
advancement changes (badges or milestone unlocks), so rematches react to
campaign progression instead of being permanently unlocked on first defeat.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Protocol

logger = logging.getLogger(__name__)

_BADGE_PROGRESS_KEY = "progress.badges"
_DEFAULT_BADGE_REQUIREMENT_KEY = "rematch.required_badges.default"
_DEFAULT_MILESTONE_REQUIREMENT_KEY = "rematch.required_milestones.default"


class _SupportsRematchProgression(Protocol):
    slug: str

    @property
    def variable_manager(self) -> Any: ...

    @property
    def trainer_state_manager(self) -> Any: ...

    @property
    def milestone_tracker(self) -> Any: ...


@dataclass(frozen=True)
class RematchRequirement:
    required_badges: int = 0
    required_milestones: tuple[str, ...] = ()


class RematchProgressionService:
    """
    Keeps rematch eligibility aligned with current player advancement.

    Variable contract (all optional):

    - ``progress.badges`` (player scope): integer badge count.
    - ``rematch.required_badges.default`` (world/player): default badge gate.
    - ``rematch.required_badges.<trainer_id>`` (world/player): per-trainer gate.
    - ``rematch.required_milestones.default`` (world/player): comma-separated
      milestone IDs required for all trainers.
    - ``rematch.required_milestones.<trainer_id>`` (world/player): per-trainer
      comma-separated milestone IDs.
    """

    def __init__(self, player: _SupportsRematchProgression) -> None:
        self.player = player
        self._last_signature: tuple[int, tuple[str, ...]] | None = None

    def tick(self) -> bool:
        """
        Refresh trainer eligibility when advancement inputs changed.

        Returns ``True`` when a refresh was performed; ``False`` otherwise.
        """
        signature = self._progress_signature()
        if signature == self._last_signature:
            return False
        self._last_signature = signature
        self.refresh_all()
        return True

    def refresh_all(self) -> None:
        """Re-evaluate rematch eligibility for all tracked trainers."""
        for trainer_id in self.player.trainer_state_manager.trainer_ids():
            self.evaluate_trainer(trainer_id)

    def evaluate_trainer(self, trainer_id: str) -> bool:
        """Re-evaluate eligibility for one trainer and persist the result."""
        req = self._requirements_for(trainer_id)
        return self.player.trainer_state_manager.evaluate_rematch_eligibility(
            trainer_id=trainer_id,
            badge_count=self._badge_count(),
            required_badges=req.required_badges,
            required_milestones=req.required_milestones,
            milestone_checker=self.player.milestone_tracker.is_achieved,
            player_id=self.player.slug,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _progress_signature(self) -> tuple[int, tuple[str, ...]]:
        milestones = tuple(
            sorted(
                self.player.milestone_tracker.encode().get("achieved", [])
            )
        )
        return self._badge_count(), milestones

    def _badge_count(self) -> int:
        value = self.player.variable_manager.player.get(_BADGE_PROGRESS_KEY, 0)
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            logger.warning("Invalid badge progress value: %r", value)
            return 0

    def _requirements_for(self, trainer_id: str) -> RematchRequirement:
        badge_default = self._coerce_int(
            self._get_var(_DEFAULT_BADGE_REQUIREMENT_KEY),
            default=0,
        )
        badge_specific = self._coerce_int(
            self._get_var(f"rematch.required_badges.{trainer_id}"),
            default=badge_default,
        )

        milestones_default = self._coerce_milestones(
            self._get_var(_DEFAULT_MILESTONE_REQUIREMENT_KEY)
        )
        milestones_specific_raw = self._get_var(
            f"rematch.required_milestones.{trainer_id}"
        )
        milestones_specific = (
            self._coerce_milestones(milestones_specific_raw)
            if milestones_specific_raw is not None
            else milestones_default
        )

        return RematchRequirement(
            required_badges=badge_specific,
            required_milestones=milestones_specific,
        )

    def _get_var(self, key: str) -> Any | None:
        world_value = self.player.variable_manager.world.get(key)
        if world_value is not None:
            return world_value
        return self.player.variable_manager.player.get(key)

    @staticmethod
    def _coerce_int(value: Any, default: int) -> int:
        if value is None:
            return default
        try:
            return max(0, int(value))
        except (TypeError, ValueError):
            return default

    @staticmethod
    def _coerce_milestones(value: Any) -> tuple[str, ...]:
        if value is None:
            return ()
        if isinstance(value, str):
            tokens = [token.strip() for token in value.split(",")]
            return tuple(token for token in tokens if token)
        if isinstance(value, (list, tuple, set)):
            tokens = [str(token).strip() for token in value]
            return tuple(token for token in tokens if token)
        return ()

# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Trainer rematch system with scaling difficulty and cooldown tracking.

Trainers can be rematched after a configurable cooldown period.
Each rematch increases the trainer's level scaling and may improve
their roster with stronger monsters.  Rematch state is persisted
through save/load.

Integration points:
- BattlesHandler: checks whether a trainer was defeated
- Relationships: trainers registered as contacts can notify via phone
- Save/load: rematch state is persisted via get_state()/set_state()
"""
from __future__ import annotations

import logging
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_COOLDOWN_SECONDS = 300
DEFAULT_LEVEL_SCALING_PER_REMATCH = 3
DEFAULT_MAX_REMATCH_LEVEL_BONUS = 30


@dataclass
class TrainerRematchEntry:
    """Tracks rematch state for a single trainer."""

    trainer_slug: str
    rematch_count: int = 0
    last_defeated_at: float = 0.0
    cooldown_seconds: float = DEFAULT_COOLDOWN_SECONDS

    def to_dict(self) -> dict[str, Any]:
        return {
            "trainer_slug": self.trainer_slug,
            "rematch_count": self.rematch_count,
            "last_defeated_at": self.last_defeated_at,
            "cooldown_seconds": self.cooldown_seconds,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> TrainerRematchEntry:
        return cls(
            trainer_slug=str(data.get("trainer_slug", "")),
            rematch_count=int(data.get("rematch_count", 0)),
            last_defeated_at=float(data.get("last_defeated_at", 0.0)),
            cooldown_seconds=float(
                data.get("cooldown_seconds", DEFAULT_COOLDOWN_SECONDS)
            ),
        )


class TrainerRematchManager:
    """Manages trainer rematch availability, cooldowns, and level scaling."""

    def __init__(
        self,
        level_scaling: int = DEFAULT_LEVEL_SCALING_PER_REMATCH,
        max_level_bonus: int = DEFAULT_MAX_REMATCH_LEVEL_BONUS,
        default_cooldown: float = DEFAULT_COOLDOWN_SECONDS,
    ) -> None:
        self._entries: dict[str, TrainerRematchEntry] = {}
        self.level_scaling = level_scaling
        self.max_level_bonus = max_level_bonus
        self.default_cooldown = default_cooldown

    def record_defeat(
        self,
        trainer_slug: str,
        now: float | None = None,
    ) -> TrainerRematchEntry:
        """Record that a trainer was defeated, advancing their rematch state."""
        current_time = now if now is not None else time.time()
        entry = self._entries.get(trainer_slug)
        if entry is None:
            entry = TrainerRematchEntry(
                trainer_slug=trainer_slug,
                cooldown_seconds=self.default_cooldown,
            )
            self._entries[trainer_slug] = entry

        entry.rematch_count += 1
        entry.last_defeated_at = current_time
        logger.info(
            f"Trainer '{trainer_slug}' defeated (rematch #{entry.rematch_count})"
        )
        return entry

    def is_rematch_available(
        self,
        trainer_slug: str,
        now: float | None = None,
    ) -> bool:
        """Check if a trainer is available for rematch (cooldown expired)."""
        entry = self._entries.get(trainer_slug)
        if entry is None:
            return False
        current_time = now if now is not None else time.time()
        elapsed = current_time - entry.last_defeated_at
        return elapsed >= entry.cooldown_seconds

    def get_rematch_count(self, trainer_slug: str) -> int:
        entry = self._entries.get(trainer_slug)
        return entry.rematch_count if entry is not None else 0

    def get_level_bonus(self, trainer_slug: str) -> int:
        """Calculate the level bonus for a trainer based on rematch count."""
        count = self.get_rematch_count(trainer_slug)
        bonus = count * self.level_scaling
        return min(bonus, self.max_level_bonus)

    def get_rematch_level(
        self, trainer_slug: str, base_level: int
    ) -> int:
        """Calculate the effective level for a rematch opponent."""
        bonus = self.get_level_bonus(trainer_slug)
        return base_level + bonus

    def get_available_rematches(
        self, now: float | None = None
    ) -> list[str]:
        """Return slugs of all trainers available for rematch."""
        current_time = now if now is not None else time.time()
        return [
            slug
            for slug, entry in self._entries.items()
            if current_time - entry.last_defeated_at >= entry.cooldown_seconds
        ]

    def get_cooldown_remaining(
        self, trainer_slug: str, now: float | None = None
    ) -> float:
        """Return seconds remaining on a trainer's cooldown, or 0 if ready."""
        entry = self._entries.get(trainer_slug)
        if entry is None:
            return 0.0
        current_time = now if now is not None else time.time()
        elapsed = current_time - entry.last_defeated_at
        remaining = entry.cooldown_seconds - elapsed
        return max(0.0, remaining)

    def get_state(self) -> dict[str, Any]:
        return {
            "trainer_rematches": {
                slug: entry.to_dict()
                for slug, entry in self._entries.items()
            },
            "level_scaling": self.level_scaling,
            "max_level_bonus": self.max_level_bonus,
            "default_cooldown": self.default_cooldown,
        }

    def set_state(self, data: Mapping[str, Any]) -> None:
        raw_entries = data.get("trainer_rematches", {})
        if isinstance(raw_entries, Mapping):
            entries: dict[str, TrainerRematchEntry] = {}
            for slug, entry_data in raw_entries.items():
                if isinstance(entry_data, Mapping):
                    try:
                        entries[str(slug)] = TrainerRematchEntry.from_dict(
                            entry_data
                        )
                    except (KeyError, TypeError, ValueError):
                        continue
            self._entries = entries

        if "level_scaling" in data:
            self.level_scaling = int(data["level_scaling"])
        if "max_level_bonus" in data:
            self.max_level_bonus = int(data["max_level_bonus"])
        if "default_cooldown" in data:
            self.default_cooldown = float(data["default_cooldown"])

    def get_summary(self) -> dict[str, Any]:
        """Return a summary of all tracked trainers."""
        return {
            "total_trainers": len(self._entries),
            "available_rematches": len(self.get_available_rematches()),
            "trainers": {
                slug: {
                    "rematch_count": entry.rematch_count,
                    "level_bonus": self.get_level_bonus(slug),
                    "available": self.is_rematch_available(slug),
                }
                for slug, entry in self._entries.items()
            },
        }

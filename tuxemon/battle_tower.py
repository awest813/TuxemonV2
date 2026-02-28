# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Battle Tower — a repeatable challenge facility with scaling difficulty.

Players face a series of NPC opponents with procedurally generated teams.
Difficulty scales with the player's current rank. Wins advance the rank,
losses reset the current streak. Rewards scale with consecutive wins.

Integration points:
- Save/load: rank and streak are persisted via get_state()/set_state()
- Combat: opponents are generated as NPC-like objects with monster parties
- Economy: rewards are granted after each victory
"""
from __future__ import annotations

import logging
import random
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class BattleTowerRules:
    """Configurable rules for a Battle Tower challenge."""

    level_cap: int = 50
    party_size: int = 3
    allow_items: bool = False
    allow_duplicates: bool = False


@dataclass
class BattleTowerOpponent:
    """A generated opponent for a Battle Tower round."""

    name: str
    monster_slugs: list[str]
    monster_level: int
    difficulty_rank: int


@dataclass
class BattleTowerState:
    """Persistent state for a player's Battle Tower progress."""

    current_rank: int = 0
    current_streak: int = 0
    best_streak: int = 0
    total_wins: int = 0
    total_losses: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "current_rank": self.current_rank,
            "current_streak": self.current_streak,
            "best_streak": self.best_streak,
            "total_wins": self.total_wins,
            "total_losses": self.total_losses,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> BattleTowerState:
        return cls(
            current_rank=int(data.get("current_rank", 0)),
            current_streak=int(data.get("current_streak", 0)),
            best_streak=int(data.get("best_streak", 0)),
            total_wins=int(data.get("total_wins", 0)),
            total_losses=int(data.get("total_losses", 0)),
        )


TRAINER_NAME_POOL = [
    "Ace Trainer",
    "Battle Expert",
    "Tower Guardian",
    "Challenge Master",
    "Sparring Partner",
    "Arena Champion",
    "Tower Veteran",
    "Rising Star",
]


class BattleTowerManager:
    """Manages Battle Tower challenge sessions with scaling difficulty."""

    def __init__(
        self,
        monster_pool: Sequence[str] | None = None,
        rules: BattleTowerRules | None = None,
    ) -> None:
        self.state = BattleTowerState()
        self.rules = rules or BattleTowerRules()
        self._monster_pool: list[str] = list(monster_pool or [])

    def set_monster_pool(self, slugs: Sequence[str]) -> None:
        self._monster_pool = list(slugs)

    def _calculate_opponent_level(self) -> int:
        """Scale opponent level based on rank, capped by rules."""
        base = 10 + (self.state.current_rank * 5)
        return min(base, self.rules.level_cap)

    def _calculate_party_size(self) -> int:
        """Scale party size based on rank, capped by rules."""
        if self.state.current_rank < 3:
            return min(1, self.rules.party_size)
        if self.state.current_rank < 6:
            return min(2, self.rules.party_size)
        return self.rules.party_size

    def _pick_trainer_name(self) -> str:
        return random.choice(TRAINER_NAME_POOL)

    def _pick_monsters(self, count: int) -> list[str]:
        """Select monsters for an opponent's party."""
        if not self._monster_pool:
            return []
        pool = list(self._monster_pool)
        if self.rules.allow_duplicates:
            return [random.choice(pool) for _ in range(count)]
        random.shuffle(pool)
        return pool[:count]

    def generate_opponent(self) -> BattleTowerOpponent:
        """Generate the next opponent based on current rank."""
        party_size = self._calculate_party_size()
        level = self._calculate_opponent_level()
        monsters = self._pick_monsters(party_size)
        name = self._pick_trainer_name()
        return BattleTowerOpponent(
            name=name,
            monster_slugs=monsters,
            monster_level=level,
            difficulty_rank=self.state.current_rank,
        )

    def record_win(self) -> dict[str, int]:
        """Record a victory and return reward info."""
        self.state.current_streak += 1
        self.state.total_wins += 1
        if self.state.current_streak > self.state.best_streak:
            self.state.best_streak = self.state.current_streak

        old_rank = self.state.current_rank
        if self.state.current_streak % 7 == 0:
            self.state.current_rank += 1
            logger.info(
                f"Battle Tower rank up: {old_rank} -> {self.state.current_rank}"
            )

        reward_money = self._calculate_reward()
        return {
            "money": reward_money,
            "streak": self.state.current_streak,
            "rank": self.state.current_rank,
            "rank_up": int(self.state.current_rank > old_rank),
        }

    def record_loss(self) -> dict[str, int]:
        """Record a loss and reset streak."""
        self.state.current_streak = 0
        self.state.total_losses += 1
        return {
            "streak": 0,
            "rank": self.state.current_rank,
        }

    def _calculate_reward(self) -> int:
        """Scale rewards with streak and rank."""
        base = 100
        streak_bonus = self.state.current_streak * 25
        rank_bonus = self.state.current_rank * 50
        return base + streak_bonus + rank_bonus

    def get_state(self) -> dict[str, Any]:
        return {"battle_tower": self.state.to_dict()}

    def set_state(self, data: Mapping[str, Any]) -> None:
        tower_data = data.get("battle_tower")
        if isinstance(tower_data, Mapping):
            self.state = BattleTowerState.from_dict(tower_data)

    def get_summary(self) -> dict[str, Any]:
        """Return a summary of the player's Battle Tower progress."""
        return {
            "rank": self.state.current_rank,
            "current_streak": self.state.current_streak,
            "best_streak": self.state.best_streak,
            "total_wins": self.state.total_wins,
            "total_losses": self.state.total_losses,
            "next_opponent_level": self._calculate_opponent_level(),
            "rules": {
                "level_cap": self.rules.level_cap,
                "party_size": self.rules.party_size,
                "allow_items": self.rules.allow_items,
            },
        }

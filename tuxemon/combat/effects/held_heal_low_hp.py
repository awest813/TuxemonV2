# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from tuxemon.core.core_effect import CoreEffect

if TYPE_CHECKING:
    from tuxemon.session import Session

logger = logging.getLogger(__name__)


@dataclass
class HeldHealLowHp(CoreEffect):
    """
    Heals the holder when their HP drops below a certain threshold.
    """

    name = "held_heal_low_hp"
    threshold: float = 0.5
    heal_amount: int | float = 20

    def apply(self, session: "Session", context: dict[str, Any]) -> None:
        """
        Check conditions and heal the user if applicable.
        """
        user = context.get("user")
        if not user:
            return

        # Check HP threshold
        if user.hp_ratio > self.threshold or user.is_fainted:
            return

        # Check if item exists and is consumable
        item = user.held_item
        if not item:
            return

        # Calculate healing
        amount = 0
        if isinstance(self.heal_amount, float) and self.heal_amount < 1.0:
            amount = int(user.hp * self.heal_amount)
        else:
            amount = int(self.heal_amount)

        logger.info(f"{user.name} consumes {item.name} to heal {amount} HP!")

        # Apply healing
        user.current_hp = min(user.hp, user.current_hp + amount)

        # Consume item
        user.item_handler.take_item()

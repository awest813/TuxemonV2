# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from tuxemon.core.core_effect import CoreEffect
from tuxemon.db import EffectPhase

if TYPE_CHECKING:
    from tuxemon.session import Session

logger = logging.getLogger(__name__)


class HeldHealLowHp(CoreEffect):
    """
    Heals the holder when their HP drops below a certain threshold.
    Effect parameters:
        threshold: float (0.0 to 1.0, default 0.5)
        heal_amount: int (flat HP) or float (percentage if < 1.0)
    """

    name = "held_heal_low_hp"

    def apply(self, session: "Session", context: dict[str, Any]) -> None:
        """
        Check conditions and heal the user if applicable.
        """
        user = context.get("user")
        if not user:
            return

        threshold = float(self.parameters.get("threshold", 0.5))
        heal_value = self.parameters.get("heal_amount", 20)

        # Check HP threshold
        if user.hp_ratio > threshold or user.is_fainted:
            return

        # Check if item exists and is consumable
        item = user.held_item
        if not item:
            return

        # Calculate healing
        amount = 0
        if isinstance(heal_value, float) and heal_value < 1.0:
            amount = int(user.hp * heal_value)
        else:
            amount = int(heal_value)

        logger.info(f"{user.name} consumes {item.name} to heal {amount} HP!")

        # Apply healing
        user.current_hp = min(user.hp, user.current_hp + amount)

        # Consume item
        user.item_handler.take_item()

        # Log/Notify (This part depends on how combat messages are handled)
        # For now, we assume this effect is called within a combat loop

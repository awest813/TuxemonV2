# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from tuxemon.core.core_effect import CoreEffect, ItemEffectResult
from tuxemon.formula import set_health

if TYPE_CHECKING:
    from tuxemon.item.item import Item
    from tuxemon.monster.monster import Monster
    from tuxemon.session import Session


@dataclass
class HeldHealLowHpEffect(CoreEffect):
    """
    Applies a healing effect if the monster's HP is below a certain threshold.
    This is typically used for held items like berries.

    **Parameters**

    - ``threshold``: Float value (0.0 to 1.0) representing the HP ratio
      threshold below which the healing triggers.
    - ``amount``: Integer or float value.
      - If integer: constant HP to heal.
      - If float: percentage of total HP to heal (e.g. ``0.5`` for 50%).
    - ``heal_type``: Indicates whether the amount is ``fixed`` or
      ``percentage``.

    **Example**

    .. code-block:: json

        "effects": [
            "held_heal_low_hp 0.5 20 fixed"
        ]
    """

    name = "held_heal_low_hp"
    threshold: float
    amount: int | float
    heal_type: str

    def apply_item_target(
        self, session: Session, item: Item, target: Monster
    ) -> ItemEffectResult:
        # Check if HP is below or equal to threshold
        if target.hp_ratio > self.threshold:
            return ItemEffectResult(name=item.name, success=False)

        # Don't heal if already at full health (though ratio check covers
        # most cases, but threshold could be 1.0)
        if target.missing_hp <= 0:
            return ItemEffectResult(name=item.name, success=False)

        value: int | float
        if self.heal_type == "fixed":
            value = int(self.amount)
        elif self.heal_type == "percentage":
            value = int(target.hp * float(self.amount))
        else:
            raise ValueError(
                f"Invalid heal type '{self.heal_type}'. "
                "Must be either 'fixed' or 'percentage'."
            )

        set_health(target, value, adjust=True)

        return ItemEffectResult(name=item.name, success=True)

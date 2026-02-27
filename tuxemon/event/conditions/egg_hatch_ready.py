# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from dataclasses import dataclass

from tuxemon.db import SpatialCondition
from tuxemon.event.eventcondition import EventCondition
from tuxemon.session import Session


@dataclass
class EggHatchReadyCondition(EventCondition):
    """
    Check if any egg in the player's party is ready to hatch.

    Script usage:
        .. code-block::

            is egg_hatch_ready
    """

    name = "egg_hatch_ready"

    def test(self, session: Session, condition: SpatialCondition) -> bool:
        player = session.player
        for monster in player.monsters:
            if monster.is_egg and monster.hatch_steps <= 0:
                return True
        return False

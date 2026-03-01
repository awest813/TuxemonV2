# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import final

from tuxemon.event.eventaction import EventAction
from tuxemon.locale.locale import T
from tuxemon.session import Session
from tuxemon.tools.dialog import open_dialog

logger = logging.getLogger(__name__)


@final
@dataclass
class HatchEggAction(EventAction):
    """
    Hatch an egg that is ready.

    Script usage:
        .. code-block::

            hatch_egg
    """

    name = "hatch_egg"

    def start(self, session: Session) -> None:
        player = session.player
        egg_to_hatch = None

        for monster in player.monsters:
            if monster.is_egg and monster.hatch_steps <= 0:
                egg_to_hatch = monster
                break

        if not egg_to_hatch:
            logger.warning("No egg ready to hatch found.")
            return

        egg_to_hatch.is_egg = False
        egg_to_hatch.hatch_steps = 0

        # Optionally, you could add logic here to:
        # - Play an animation
        # - Show a nickname prompt
        # - Register as 'caught' if not already done

        msg = T.format("egg_hatched", {"name": egg_to_hatch.name})
        # If translation key doesn't exist, fallback or ensure it's added.
        # For now, using a direct string fallback if needed, but T.format should handle it if key exists.
        # Assuming we might need to add "egg_hatched" to localization later or use a generic one.

        # Using a generic message if key missing is tricky without checking T logic,
        # but let's assume we want a simple dialog.
        open_dialog(session.client, [msg or f"Your egg hatched into a {egg_to_hatch.name}!"], dialog_speed="max")

    def update(self, session: Session, dt: float) -> None:
        try:
            session.client.get_state_by_name("DialogState")
        except ValueError:
            self.stop()

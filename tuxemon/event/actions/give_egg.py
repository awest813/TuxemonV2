# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from dataclasses import dataclass
from typing import final

from tuxemon.database.runtime import db
from tuxemon.event.eventaction import EventAction
from tuxemon.monster.monster import Monster
from tuxemon.session import Session


@final
@dataclass
class GiveEggAction(EventAction):
    """
    Give an egg to the player.

    Script usage:
        .. code-block::

            give_egg <mon_slug>[,steps]

    Script parameters:
        mon_slug: Monster slug to look up in the monster database.
        steps: Number of steps to hatch the egg. Defaults to 2000.
    """

    name = "give_egg"
    monster_slug: str
    steps: int | None = None

    def start(self, session: Session) -> None:
        player = session.player

        if self.monster_slug not in db.database["monster"]:
            if player.game_variables.has(self.monster_slug):
                monster_slug = player.game_variables.get(self.monster_slug)
            else:
                raise ValueError(
                    f"{self.monster_slug} doesn't exist (monster or variable)"
                )
        else:
            monster_slug = self.monster_slug

        # Spawn as egg
        monster = Monster.spawn_base(monster_slug, 1, as_egg=True)

        if self.steps is not None:
            monster.hatch_steps = self.steps

        # Use add_monster action logic (or similar) to add to party
        player.party.add_monster(monster, len(player.monsters))
        player.tuxepedia.register_seen(monster.slug)

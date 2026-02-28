# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from typing import TYPE_CHECKING, Any, ClassVar

from tuxemon.menu.menu import PygameMenuState
from tuxemon.platform.const import buttons
from tuxemon.platform.events import PlayerInput
from tuxemon.prepare import SCREEN_SIZE
from tuxemon.states.world_menus import add_menu_items_to_pygame_menu

if TYPE_CHECKING:
    from tuxemon.base_client import BaseClient
    from tuxemon.world.manager import WorldMenuManager


class WorldSystemMenuState(PygameMenuState):
    """Secondary world menu with save/load/options/quit actions."""

    name: ClassVar[str] = "WorldSystemMenuState"

    def __init__(
        self,
        client: BaseClient,
        menu_manager: WorldMenuManager,
        **kwargs: Any,
    ) -> None:
        super().__init__(client=client, height=SCREEN_SIZE[1], **kwargs)
        self.menu_manager = menu_manager
        add_menu_items_to_pygame_menu(
            self.menu, self.menu_manager.build_system_menu_items()
        )

    def process_event(self, event: PlayerInput) -> PlayerInput | None:
        if (
            event.button in (buttons.START, buttons.B, buttons.BACK)
            and event.pressed
        ):
            self.client.pop_state()
            return None
        return super().process_event(event)

# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from unittest.mock import MagicMock

from tuxemon.computer import PCMenuBuilder


class MockStorage:
    def __init__(self, visible: bool) -> None:
        self._visible = visible

    def get_all_monsters_visible(self) -> bool:
        return self._visible

    def get_all_items_visible(self) -> bool:
        return self._visible


class MockCharacter:
    def __init__(self) -> None:
        self.monster_boxes = MockStorage(True)
        self.item_boxes = MockStorage(True)
        self.monsters = [object()]
        self.items = [object()]


def test_pc_menu_includes_multiplayer_option() -> None:
    client = MagicMock()
    character = MockCharacter()
    builder = PCMenuBuilder(client, character)

    menu = builder.build_menu_items()
    menu_keys = [key for key, _ in menu]

    assert "menu_multiplayer" in menu_keys


def test_multiplayer_option_pushes_multiplayer_state() -> None:
    client = MagicMock()
    character = MockCharacter()
    builder = PCMenuBuilder(client, character)

    menu = dict(builder.build_menu_items())
    menu["menu_multiplayer"]()

    client.push_state.assert_called_once_with("MultiplayerMenu")

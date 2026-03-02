# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from unittest.mock import patch

from tuxemon.world.manager import MenuItem, WorldMenuManager


class DummyMissionController:
    def get_missions_with_met_prerequisites(self):
        return []


class DummyPlayer:
    def __init__(self):
        self.monsters = [object()]
        self.items = [type("Item", (), {"dynamic_menu": None})()]
        self.mission_controller = DummyMissionController()


class DummyClient:
    def push_state(self, *args, **kwargs):
        return None

    class event_engine:
        @staticmethod
        def execute_action(*args, **kwargs):
            return None


class TestWorldMenuManager(unittest.TestCase):
    @patch("tuxemon.world.manager.T.translate", side_effect=lambda key: key)
    def test_world_menu_contains_system_entry(self, _mock_translate):
        manager = WorldMenuManager(DummyClient())
        manager.menu_renderer = type(
            "Renderer", (), {"open_monster_menu": lambda self: None}
        )()

        items = manager.build_current_menu_items(DummyPlayer())
        keys = [item.key for item in items]

        self.assertIn("menu_options", keys)
        self.assertNotIn("menu_save", keys)
        self.assertNotIn("menu_load", keys)
        self.assertNotIn("exit", keys)

    @patch("tuxemon.world.manager.T.translate")
    def test_merge_persistent_items_avoids_duplicate_key(self, mock_translate):
        translations = {
            "menu_options": "Options",
            "menu_monster": "Monster",
            "menu_bag": "Bag",
            "menu_player": "Player",
        }
        mock_translate.side_effect = lambda key: translations.get(key, key)

        manager = WorldMenuManager(DummyClient())
        manager.menu_renderer = type(
            "Renderer", (), {"open_monster_menu": lambda self: None}
        )()

        manager.menu_items.append(
            MenuItem("menu_options", "OPTIONS", lambda: None)
        )

        items = manager.build_current_menu_items(DummyPlayer())
        keys = [item.key for item in items]

        self.assertEqual(keys.count("menu_options"), 1)

    @patch("tuxemon.world.manager.T.translate", side_effect=lambda key: key)
    def test_system_menu_contains_system_actions(self, _mock_translate):
        manager = WorldMenuManager(DummyClient())

        items = manager.build_system_menu_items()
        keys = [item.key for item in items]

        self.assertEqual(
            keys, ["menu_save", "menu_load", "menu_options", "exit"]
        )


if __name__ == "__main__":
    unittest.main()

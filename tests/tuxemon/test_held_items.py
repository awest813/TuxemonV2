# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from unittest.mock import MagicMock

from tuxemon.monster.held_item import MonsterItemHandler


class TestHeldItems(unittest.TestCase):
    def setUp(self):
        self.item_handler = MonsterItemHandler()
        self.mock_item = MagicMock()
        self.mock_item.name = "Test Berry"
        self.mock_item.behaviors.holdable = True
        self.mock_item.conditions = []
        self.mock_item.effects = []

    def test_set_holdable_item(self):
        """Test setting a holdable item."""
        result = self.item_handler.set_item(self.mock_item)
        self.assertTrue(result)
        self.assertEqual(self.item_handler.held_item, self.mock_item)

    def test_set_non_holdable_item(self):
        """Test setting a non-holdable item."""
        self.mock_item.behaviors.holdable = False
        result = self.item_handler.set_item(self.mock_item)
        self.assertFalse(result)
        self.assertIsNone(self.item_handler.held_item)

    def test_check_trigger_placeholder(self):
        """Test the placeholder check_trigger method."""
        self.item_handler.set_item(self.mock_item)
        result = self.item_handler.check_trigger("turn_end", {})
        self.assertFalse(result)  # Currently always returns False as it's a placeholder

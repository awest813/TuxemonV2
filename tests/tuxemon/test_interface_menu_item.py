# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from unittest.mock import MagicMock, patch

import pygame
from pygame import Surface

from tuxemon.menu.interface import MenuItem


class TestMenuItem(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()
        pygame.display.set_mode((1, 1))

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.image = Surface((10, 10))
        self.game_object = MagicMock()

    def test_init_default(self):
        menu_item = MenuItem(
            self.image, "Test Label", "Test Description", self.game_object
        )
        self.assertEqual(menu_item.label, "Test Label")
        self.assertEqual(menu_item.description, "Test Description")
        self.assertEqual(menu_item.enabled, True)

    def test_init_custom(self):
        menu_item = MenuItem(
            self.image,
            "Test Label",
            "Test Description",
            self.game_object,
            enabled=False,
            position=(100, 100),
        )
        self.assertEqual(menu_item.label, "Test Label")
        self.assertEqual(menu_item.description, "Test Description")
        self.assertEqual(menu_item.enabled, False)

    def test_update_image_focus(self):
        menu_item = MenuItem(
            self.image, "Test Label", "Test Description", self.game_object
        )
        menu_item._in_focus = True
        menu_item.update_image = MagicMock()
        menu_item.update_image()

    def test_update_image_enabled(self):
        menu_item = MenuItem(
            self.image, "Test Label", "Test Description", self.game_object
        )
        menu_item.enabled = False
        menu_item.update_image = MagicMock()
        menu_item.update_image()

    def test_enabled_setter_triggers_update_image(self):
        menu_item = MenuItem(
            self.image, "Test Label", "Test Description", self.game_object
        )
        with patch.object(menu_item, "update_image") as mock_update:
            menu_item.enabled = False
            mock_update.assert_called_once()

    def test_enabled_setter_no_call_when_unchanged(self):
        menu_item = MenuItem(
            self.image, "Test Label", "Test Description", self.game_object
        )
        with patch.object(menu_item, "update_image") as mock_update:
            menu_item.enabled = True  # already True, no change
            mock_update.assert_not_called()

    def test_disabled_item_has_reduced_alpha(self):
        menu_item = MenuItem(
            self.image, "Test Label", "Test Description", self.game_object
        )
        menu_item.enabled = False
        self.assertEqual(menu_item.image.get_alpha(), 128)

    def test_enabled_item_has_full_alpha(self):
        menu_item = MenuItem(
            self.image,
            "Test Label",
            "Test Description",
            self.game_object,
            enabled=False,
        )
        menu_item.enabled = True
        self.assertEqual(menu_item.image.get_alpha(), 255)

    def test_enabled_property(self):
        menu_item = MenuItem(
            self.image, "Test Label", "Test Description", self.game_object
        )
        self.assertTrue(menu_item.enabled)
        menu_item.enabled = False
        self.assertFalse(menu_item.enabled)

    def test_in_focus_property(self):
        menu_item = MenuItem(
            self.image, "Test Label", "Test Description", self.game_object
        )
        self.assertFalse(menu_item.in_focus)
        menu_item.in_focus = True
        self.assertTrue(menu_item.in_focus)

    def test_repr(self):
        menu_item = MenuItem(
            self.image, "Test Label", "Test Description", self.game_object
        )
        self.assertIn("Test Label", str(menu_item))
        self.assertIn("enabled=True", str(menu_item))

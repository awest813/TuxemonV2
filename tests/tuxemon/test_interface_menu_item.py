# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from unittest.mock import MagicMock, patch

import pygame
from pygame import Surface

from tuxemon.menu.interface import MenuItem


class TestMenuItem(unittest.TestCase):

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

    def test_enabled_setter_triggers_update_image(self):
        """Changing enabled calls update_image() immediately."""
        menu_item = MenuItem(
            self.image, "Label", None, self.game_object, enabled=True
        )
        with patch.object(menu_item, "update_image") as mock_update:
            menu_item.enabled = False
            mock_update.assert_called_once()

    def test_enabled_setter_no_call_when_value_unchanged(self):
        """Setting enabled to its current value does not call update_image()."""
        menu_item = MenuItem(
            self.image, "Label", None, self.game_object, enabled=True
        )
        with patch.object(menu_item, "update_image") as mock_update:
            menu_item.enabled = True  # same value — no change expected
            mock_update.assert_not_called()

    def test_disabled_item_image_differs_from_enabled(self):
        """Disabling an item visually dims its image."""
        colored = Surface((20, 20))
        colored.fill((200, 100, 50))

        item = MenuItem(colored, "Label", None, self.game_object, enabled=True)
        # Access image to force update and capture original pixel
        original_pixel = item.image.get_at((10, 10))

        item.enabled = False
        disabled_pixel = item.image.get_at((10, 10))

        # The dimmed image must have lower RGB values than the original.
        self.assertNotEqual(
            original_pixel[:3],
            disabled_pixel[:3],
            "Disabled image should have different RGB than enabled image",
        )
        for original_ch, disabled_ch in zip(original_pixel[:3], disabled_pixel[:3]):
            if original_ch > 0:
                self.assertLess(
                    disabled_ch,
                    original_ch,
                    "Each colour channel should be dimmer when disabled",
                )

    def test_reenabling_item_restores_original_appearance(self):
        """Re-enabling an item restores the original (non-dimmed) image."""
        colored = Surface((20, 20))
        colored.fill((180, 90, 40))

        item = MenuItem(colored, "Label", None, self.game_object, enabled=True)
        original_pixel = item.image.get_at((10, 10))

        item.enabled = False
        item.enabled = True  # restore

        restored_pixel = item.image.get_at((10, 10))
        self.assertEqual(
            original_pixel[:3],
            restored_pixel[:3],
            "Re-enabled item should show the original pixel colour",
        )

    def test_update_image_called_on_init(self):
        """update_image is called during construction so the initial state is correct."""
        with patch.object(MenuItem, "update_image") as mock_update:
            MenuItem(self.image, "L", None, self.game_object, enabled=False)
            mock_update.assert_called()

    def test_none_image_does_not_crash_update_image(self):
        """MenuItem with a None image handles update_image() without error."""
        item = MenuItem(None, "L", None, self.game_object)
        item.enabled = False  # Should not raise
        item.enabled = True   # Should not raise

    def test_metadata_dict_starts_empty(self):
        item = MenuItem(self.image, "L", None, self.game_object)
        self.assertEqual(item.metadata, {})

    def test_metadata_is_per_instance(self):
        """Each MenuItem instance owns its own metadata dict."""
        item_a = MenuItem(self.image, "A", None, self.game_object)
        item_b = MenuItem(self.image, "B", None, self.game_object)
        item_a.metadata["key"] = "value"
        self.assertNotIn("key", item_b.metadata)

# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from unittest.mock import MagicMock

import pygame

from tuxemon.menu.events import playerinput_to_event
from tuxemon.platform.const import buttons


class TestPlayerInputToEvent(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def _make_input(self, button):
        pi = MagicMock()
        pi.button = button
        return pi

    def test_up_maps_to_key_up(self):
        event = playerinput_to_event(self._make_input(buttons.UP))
        self.assertIsNotNone(event)
        self.assertEqual(event.type, pygame.KEYDOWN)
        self.assertEqual(event.key, pygame.K_UP)

    def test_down_maps_to_key_down(self):
        event = playerinput_to_event(self._make_input(buttons.DOWN))
        self.assertIsNotNone(event)
        self.assertEqual(event.key, pygame.K_DOWN)

    def test_left_maps_to_key_left(self):
        event = playerinput_to_event(self._make_input(buttons.LEFT))
        self.assertIsNotNone(event)
        self.assertEqual(event.key, pygame.K_LEFT)

    def test_right_maps_to_key_right(self):
        event = playerinput_to_event(self._make_input(buttons.RIGHT))
        self.assertIsNotNone(event)
        self.assertEqual(event.key, pygame.K_RIGHT)

    def test_a_maps_to_return(self):
        event = playerinput_to_event(self._make_input(buttons.A))
        self.assertIsNotNone(event)
        self.assertEqual(event.key, pygame.K_RETURN)

    def test_b_maps_to_escape(self):
        event = playerinput_to_event(self._make_input(buttons.B))
        self.assertIsNotNone(event)
        self.assertEqual(event.key, pygame.K_ESCAPE)

    def test_back_maps_to_escape(self):
        event = playerinput_to_event(self._make_input(buttons.BACK))
        self.assertIsNotNone(event)
        self.assertEqual(event.key, pygame.K_ESCAPE)

    def test_unmapped_button_returns_none(self):
        event = playerinput_to_event(self._make_input(99999))
        self.assertIsNone(event)

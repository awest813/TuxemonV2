# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest

from pygame.rect import Rect

from tuxemon.ui.combat_zone import CombatZone
from tuxemon.ui.text_alignment import HorizontalAlignment, VerticalAlignment


class TestCombatZone(unittest.TestCase):
    def setUp(self):
        self.screen = Rect(0, 0, 800, 600)
        self.zone = CombatZone(self.screen)

    def test_center_zone(self):
        rect = Rect(350, 250, 100, 100)
        v, h = self.zone.get_zone(rect)
        self.assertEqual(v, VerticalAlignment.CENTER)
        self.assertEqual(h, HorizontalAlignment.CENTER)

    def test_top_left_zone(self):
        rect = Rect(0, 0, 50, 50)
        v, h = self.zone.get_zone(rect)
        self.assertEqual(v, VerticalAlignment.TOP)
        self.assertEqual(h, HorizontalAlignment.LEFT)

    def test_bottom_right_zone(self):
        rect = Rect(750, 550, 50, 50)
        v, h = self.zone.get_zone(rect)
        self.assertEqual(v, VerticalAlignment.BOTTOM)
        self.assertEqual(h, HorizontalAlignment.RIGHT)

    def test_horizontal_offset_left_zone(self):
        rect = Rect(0, 250, 50, 50)
        offset = self.zone.get_horizontal_offset(rect, distance=10)
        self.assertEqual(offset, 10)

    def test_horizontal_offset_right_zone(self):
        rect = Rect(750, 250, 50, 50)
        offset = self.zone.get_horizontal_offset(rect, distance=10)
        self.assertEqual(offset, -10)

    def test_horizontal_offset_center_zone(self):
        rect = Rect(375, 250, 50, 50)
        offset = self.zone.get_horizontal_offset(rect, distance=10)
        self.assertEqual(offset, 0)

    def test_vertical_offset_top_zone(self):
        rect = Rect(350, 0, 50, 50)
        offset = self.zone.get_vertical_offset(rect, distance=10)
        self.assertEqual(offset, -10)

    def test_vertical_offset_bottom_zone(self):
        rect = Rect(350, 550, 50, 50)
        offset = self.zone.get_vertical_offset(rect, distance=10)
        self.assertEqual(offset, 10)

    def test_vertical_offset_center_zone(self):
        rect = Rect(350, 280, 50, 50)
        offset = self.zone.get_vertical_offset(rect, distance=10)
        self.assertEqual(offset, 0)

    def test_custom_margin(self):
        zone = CombatZone(self.screen, margin=200)
        rect = Rect(250, 200, 50, 50)
        v, h = zone.get_zone(rect)
        self.assertEqual(h, HorizontalAlignment.CENTER)
        self.assertEqual(v, VerticalAlignment.CENTER)

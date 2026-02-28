# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest

import pygame
from pygame.surface import Surface

from tuxemon.scaling import DefaultScaling
from tuxemon.ui.text_renderer import TextRenderer, load_font_with_fallback


class TestTextRenderer(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        pygame.init()

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        self.text_renderer = TextRenderer(DefaultScaling(1), (255, 255, 255))

    def test_init(self):
        self.assertEqual(self.text_renderer.font_color, (255, 255, 255))

    def test_shadow_text(self):
        surface = self.text_renderer.shadow_text("Hello, World!")
        self.assertIsInstance(surface, Surface)

    def test_shadow_text_default_colors(self):
        surface = self.text_renderer.shadow_text("Hello, World!")
        self.assertGreater(surface.get_size()[0], 0)
        self.assertGreater(surface.get_size()[1], 0)

    def test_shadow_text_custom_colors(self):
        surface = self.text_renderer.shadow_text(
            "Hello, World!", fg=(0, 0, 255), bg=(255, 0, 0)
        )
        self.assertGreater(surface.get_size()[0], 0)
        self.assertGreater(surface.get_size()[1], 0)

    def test_shadow_text_offset(self):
        surface = self.text_renderer.shadow_text(
            "Hello, World!", offset=(1, 1)
        )
        self.assertGreater(surface.get_size()[0], 0)
        self.assertGreater(surface.get_size()[1], 0)

    def test_shadow_text_invalid_offset(self):
        with self.assertRaises(TypeError):
            self.text_renderer.shadow_text("Hello, World!", offset="invalid")

    def test_shadow_text_invalid_fg_color(self):
        with self.assertRaises(ValueError):
            self.text_renderer.shadow_text("Hello, World!", fg="invalid")

    def test_shadow_text_invalid_bg_color(self):
        with self.assertRaises(ValueError):
            self.text_renderer.shadow_text("Hello, World!", bg="invalid")

    def test_shadow_text_surface_size(self):
        surface = self.text_renderer.shadow_text("Hello, World!")
        self.assertGreater(surface.get_width(), 0)
        self.assertGreater(surface.get_height(), 0)

    def test_shadow_text_surface_alpha(self):
        surface = self.text_renderer.shadow_text("Hello, World!")
        self.assertEqual(
            surface.get_flags() & pygame.SRCALPHA, pygame.SRCALPHA
        )
        self.assertEqual(surface.get_alpha(), 255)

    def test_load_font_with_fallback_when_file_missing(self):
        missing_font = "/tmp/definitely_missing_font_file.ttf"
        font = load_font_with_fallback(missing_font, 14)
        self.assertGreater(font.get_height(), 0)

    def test_text_renderer_uses_font_fallback_when_file_missing(self):
        renderer = TextRenderer(
            DefaultScaling(1),
            (255, 255, 255),
            font_filename="/tmp/also_missing_font.ttf",
        )
        surface = renderer.shadow_text("Fallback works")
        self.assertIsInstance(surface, Surface)

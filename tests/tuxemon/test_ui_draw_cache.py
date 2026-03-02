# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest

import pygame
from pygame.font import Font

from tuxemon.ui.draw import (
    _FONT_SIZE_CACHE_MAX,
    font_size_cache,
    get_font_height,
    get_text_size,
)


class TestFontSizeCache(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.font = Font(None, 16)

    @classmethod
    def tearDownClass(cls):
        pygame.quit()

    def setUp(self):
        font_size_cache.clear()

    def test_cache_stores_result(self):
        result1 = get_text_size("hello", self.font)
        result2 = get_text_size("hello", self.font)
        self.assertEqual(result1, result2)
        self.assertIn("hello", font_size_cache)

    def test_cache_different_strings(self):
        get_text_size("aaa", self.font)
        get_text_size("bbb", self.font)
        self.assertIn("aaa", font_size_cache)
        self.assertIn("bbb", font_size_cache)

    def test_cache_clears_when_full(self):
        for i in range(_FONT_SIZE_CACHE_MAX):
            get_text_size(f"str_{i}", self.font)
        self.assertEqual(len(font_size_cache), _FONT_SIZE_CACHE_MAX)

        get_text_size("overflow_entry", self.font)
        self.assertIn("overflow_entry", font_size_cache)
        self.assertLessEqual(len(font_size_cache), _FONT_SIZE_CACHE_MAX)

    def test_get_font_height_positive(self):
        h = get_font_height(self.font)
        self.assertGreater(h, 0)

    def test_get_text_size_returns_tuple(self):
        result = get_text_size("test", self.font)
        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        self.assertGreater(result[0], 0)
        self.assertGreater(result[1], 0)

    def test_empty_string_size(self):
        result = get_text_size("", self.font)
        self.assertEqual(result[0], 0)
        self.assertGreater(result[1], 0)

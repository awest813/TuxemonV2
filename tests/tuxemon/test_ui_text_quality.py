# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for Phase 1.3 text rendering quality:
  - TextOverflow.SHRINK implementation
  - TextRenderer.outline_text rendering
  - LRU cache eviction (oldest entry displaced, not full clear)
"""
import unittest
from unittest.mock import MagicMock

import pygame
import pytest
from pygame.font import Font
from pygame.rect import Rect

from tuxemon.ui.draw import (
    TextOverflow,
    _FONT_SIZE_CACHE_MAX,
    _find_shrink_font,
    font_size_cache,
    get_text_size,
    iter_render_text,
)
from tuxemon.ui.text_renderer import TextRenderer


# ---------------------------------------------------------------------------
# Module-level pygame init (shared for all tests)
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module", autouse=True)
def pygame_env():
    pygame.init()
    pygame.display.set_mode((1, 1))
    yield
    pygame.quit()


@pytest.fixture(autouse=True)
def clear_cache():
    font_size_cache.clear()
    yield
    font_size_cache.clear()


@pytest.fixture
def small_font():
    return Font(None, 20)


@pytest.fixture
def scaling():
    m = MagicMock()
    m.scale_int = lambda x: int(x)
    m.scale_sequence = lambda t: tuple(float(v) for v in t)
    return m


# ---------------------------------------------------------------------------
# LRU cache: oldest entry evicted first (not a full clear)
# ---------------------------------------------------------------------------


class TestLRUCache(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        pygame.init()
        cls.font = Font(None, 16)

    def setUp(self):
        font_size_cache.clear()

    def test_lru_evicts_oldest_when_full(self):
        """When the cache is at capacity, adding a new entry evicts the oldest."""
        self.font = Font(None, 16)
        # Fill cache up to the max
        for i in range(_FONT_SIZE_CACHE_MAX):
            get_text_size(f"lru_{i}", self.font)

        # The first entry should still be present (we haven't added one more yet)
        self.assertIn("lru_0", font_size_cache)

        # Now add one more to trigger LRU eviction
        get_text_size("overflow_lru", self.font)

        # The oldest entry (lru_0) should have been evicted
        self.assertNotIn("lru_0", font_size_cache)
        # The new entry must be present
        self.assertIn("overflow_lru", font_size_cache)
        # Cache size must not exceed max
        self.assertLessEqual(len(font_size_cache), _FONT_SIZE_CACHE_MAX)

    def test_recently_accessed_not_evicted(self):
        """Accessing an entry promotes it; it should NOT be evicted first."""
        self.font = Font(None, 16)
        # Add two entries
        get_text_size("early_entry", self.font)
        for i in range(_FONT_SIZE_CACHE_MAX - 1):
            get_text_size(f"fill_{i}", self.font)

        # Re-access the first entry (promotes it to most-recently-used)
        get_text_size("early_entry", self.font)

        # Add one more to force eviction of the ACTUAL oldest (fill_0)
        get_text_size("last_entry", self.font)

        self.assertIn("early_entry", font_size_cache)
        self.assertNotIn("fill_0", font_size_cache)


# ---------------------------------------------------------------------------
# TextOverflow.SHRINK
# ---------------------------------------------------------------------------


class TestTextOverflowShrink:
    def test_find_shrink_font_returns_font_when_fits(self, small_font):
        rect = Rect(0, 0, 1000, 100)
        result = _find_shrink_font("Hi", small_font, rect)
        assert isinstance(result, Font)

    def test_find_shrink_font_reduces_size_for_overflow(self, small_font):
        """When text overflows the rect, a smaller font should be returned."""
        text = "A very long string that definitely overflows a tiny rect area"
        rect = Rect(0, 0, 20, 20)
        result = _find_shrink_font(text, small_font, rect)
        assert isinstance(result, Font)
        w, h = result.size(text)
        # The result may still overflow at min_font_size, but it should be ≤ original
        assert result.get_height() <= small_font.get_height()

    def test_iter_render_text_shrink_yields_chars(self, small_font, scaling):
        """iter_render_text with SHRINK should yield RenderedChar objects."""
        rect = Rect(0, 0, 200, 50)
        chars = list(
            iter_render_text(
                "Hello",
                small_font,
                fg=(255, 255, 255),
                bg=(0, 0, 0),
                rect=rect,
                scaling=scaling,
                overflow_behavior=TextOverflow.SHRINK,
            )
        )
        assert len(chars) > 0


# ---------------------------------------------------------------------------
# TextRenderer.outline_text
# ---------------------------------------------------------------------------


class TestOutlineText:
    def test_outline_text_returns_surface(self, small_font, scaling):
        renderer = TextRenderer(
            scaling=scaling,
            font_color=(255, 255, 255),
            font_shadow_color=(0, 0, 0),
            font=small_font,
        )
        surface = renderer.outline_text("Test")
        assert isinstance(surface, pygame.Surface)

    def test_outline_text_wider_than_plain(self, small_font, scaling):
        """Outlined text should be wider than plain text due to padding."""
        renderer = TextRenderer(
            scaling=scaling,
            font_color=(255, 255, 255),
            font=small_font,
        )
        plain = small_font.render("Hi", True, (255, 255, 255))
        outlined = renderer.outline_text("Hi", outline_width=2)
        assert outlined.get_width() > plain.get_width()

    def test_outline_text_with_explicit_colors(self, small_font, scaling):
        renderer = TextRenderer(
            scaling=scaling,
            font_color=(200, 200, 200),
            font=small_font,
        )
        surface = renderer.outline_text(
            "X", fg=(255, 0, 0), outline_color=(0, 0, 255), outline_width=1
        )
        assert surface is not None

    def test_outline_text_larger_width_produces_bigger_surface(self, small_font, scaling):
        renderer = TextRenderer(
            scaling=scaling,
            font_color=(255, 255, 255),
            font=small_font,
        )
        s1 = renderer.outline_text("A", outline_width=1)
        s2 = renderer.outline_text("A", outline_width=3)
        assert s2.get_width() > s1.get_width()

    def test_shadow_text_still_works_after_outline_added(self, small_font, scaling):
        """Ensure the new outline_text method doesn't break shadow_text."""
        renderer = TextRenderer(
            scaling=scaling,
            font_color=(255, 255, 255),
            font=small_font,
        )
        shadow = renderer.shadow_text("Test")
        assert isinstance(shadow, pygame.Surface)

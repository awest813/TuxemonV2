# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for UI theme constants, color palette, and font configuration.

Ensures visual constants stay within expected ranges and maintain
proper contrast ratios for readability.
"""
from __future__ import annotations

import pytest

from tuxemon.constants.dialog_speed import (
    DEFAULT_DIALOG_SPEED,
    DIALOG_SPEED_PROFILES,
    resolve_character_delay,
)
from tuxemon.platform.const.graphics import (
    BACKGROUND_COLOR,
    BAR_GLOSS_ALPHA,
    BAR_HIGHLIGHT_ALPHA,
    DEFAULT_LINE_SPACING,
    FONT_COLOR,
    FONT_SHADOW_COLOR,
    FONT_SIZE,
    FONT_SIZE_BIG,
    FONT_SIZE_BIGGER,
    FONT_SIZE_BIGGEST,
    FONT_SIZE_SMALL,
    FONT_SIZE_SMALLER,
    HP_COLOR_BG,
    HP_COLOR_FG,
    HP_TIER_HIGH,
    HP_TIER_LOW,
    HP_TIER_MID,
    MENU_WIDGET_PADDING,
    SCROLLBAR_COLOR,
    SCROLLBAR_SLIDER_COLOR,
    UNAVAILABLE_COLOR,
    XP_COLOR_FG,
    XP_FILL_COLOR,
)


def _luminance(rgb: tuple[int, ...]) -> float:
    """Approximate relative luminance (0=black, 1=white)."""
    r, g, b = rgb[0] / 255, rgb[1] / 255, rgb[2] / 255
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def _contrast_ratio(fg: tuple[int, ...], bg: tuple[int, ...]) -> float:
    """WCAG contrast ratio between two colors."""
    l1 = _luminance(fg) + 0.05
    l2 = _luminance(bg) + 0.05
    return max(l1, l2) / min(l1, l2)


class TestColorPalette:
    def test_font_on_background_has_sufficient_contrast(self):
        ratio = _contrast_ratio(FONT_COLOR, BACKGROUND_COLOR)
        assert ratio >= 4.5, (
            f"Font-on-background contrast {ratio:.1f} is below WCAG AA (4.5)"
        )

    def test_shadow_is_lighter_than_font(self):
        assert _luminance(FONT_SHADOW_COLOR) > _luminance(FONT_COLOR)

    def test_background_is_light(self):
        assert _luminance(BACKGROUND_COLOR) > 0.8

    def test_hp_foreground_is_green(self):
        r, g, b = HP_COLOR_FG
        assert g > r and g > b

    def test_hp_background_is_red(self):
        r, g, b = HP_COLOR_BG
        assert r > g and r > b

    def test_xp_foreground_is_blue(self):
        r, g, b = XP_COLOR_FG
        assert b > r

    def test_hp_tier_colors_are_distinct(self):
        colors = [HP_TIER_HIGH, HP_TIER_MID, HP_TIER_LOW]
        for i, c1 in enumerate(colors):
            for j, c2 in enumerate(colors):
                if i != j:
                    diff = sum(abs(a - b) for a, b in zip(c1, c2))
                    assert diff > 100, (
                        f"HP tier colors {c1} and {c2} are too similar"
                    )

    def test_unavailable_is_lighter_than_font(self):
        assert _luminance(UNAVAILABLE_COLOR) > _luminance(FONT_COLOR)

    def test_scrollbar_colors_are_light(self):
        assert _luminance(SCROLLBAR_COLOR) > 0.8
        assert _luminance(SCROLLBAR_SLIDER_COLOR) > 0.5


class TestFontSizes:
    def test_sizes_are_monotonically_increasing(self):
        sizes = [
            FONT_SIZE_SMALLER,
            FONT_SIZE_SMALL,
            FONT_SIZE,
            FONT_SIZE_BIG,
            FONT_SIZE_BIGGER,
            FONT_SIZE_BIGGEST,
        ]
        for i in range(1, len(sizes)):
            assert sizes[i] > sizes[i - 1], (
                f"Font size at index {i} ({sizes[i]}) is not larger "
                f"than index {i-1} ({sizes[i-1]})"
            )

    def test_default_size_is_readable(self):
        assert FONT_SIZE >= 4

    def test_smallest_is_still_positive(self):
        assert FONT_SIZE_SMALLER >= 2

    def test_biggest_is_not_absurd(self):
        assert FONT_SIZE_BIGGEST <= 12


class TestLayoutConstants:
    def test_line_spacing_is_positive(self):
        assert DEFAULT_LINE_SPACING > 0

    def test_widget_padding_has_two_components(self):
        assert len(MENU_WIDGET_PADDING) == 2
        assert all(p > 0 for p in MENU_WIDGET_PADDING)

    def test_bar_alpha_in_valid_range(self):
        assert 0 < BAR_GLOSS_ALPHA <= 128
        assert 0 < BAR_HIGHLIGHT_ALPHA <= 128
        assert BAR_HIGHLIGHT_ALPHA >= BAR_GLOSS_ALPHA


class TestDialogSpeed:
    def test_all_profiles_are_non_negative(self):
        for name, delay in DIALOG_SPEED_PROFILES.items():
            assert delay >= 0.0, f"Profile '{name}' has negative delay"

    def test_max_is_instant(self):
        assert DIALOG_SPEED_PROFILES["max"] == 0.0

    def test_slow_is_slowest_standard(self):
        assert DIALOG_SPEED_PROFILES["slow"] >= DIALOG_SPEED_PROFILES["fast"]

    def test_medium_is_between_slow_and_fast(self):
        assert (
            DIALOG_SPEED_PROFILES["fast"]
            < DIALOG_SPEED_PROFILES["medium"]
            < DIALOG_SPEED_PROFILES["slow"]
        )

    def test_default_speed_exists(self):
        assert DEFAULT_DIALOG_SPEED in DIALOG_SPEED_PROFILES

    def test_resolve_unknown_returns_default(self):
        delay = resolve_character_delay("nonexistent")
        assert delay == DIALOG_SPEED_PROFILES[DEFAULT_DIALOG_SPEED]

    def test_resolve_known_profile(self):
        delay = resolve_character_delay("fast")
        assert delay == DIALOG_SPEED_PROFILES["fast"]

    def test_dramatic_is_slower_than_slow(self):
        assert DIALOG_SPEED_PROFILES["dramatic"] > DIALOG_SPEED_PROFILES["slow"]


class TestBarColors:
    def test_xp_fill_color_matches_foreground_family(self):
        _, _, fb = XP_COLOR_FG
        _, _, fc = XP_FILL_COLOR
        assert fb > 100 and fc > 100

    def test_hp_tier_high_is_greenish(self):
        r, g, b = HP_TIER_HIGH
        assert g > r and g > b

    def test_hp_tier_mid_is_yellowish(self):
        r, g, b = HP_TIER_MID
        assert r > b and g > b

    def test_hp_tier_low_is_reddish(self):
        r, g, b = HP_TIER_LOW
        assert r > g and r > b

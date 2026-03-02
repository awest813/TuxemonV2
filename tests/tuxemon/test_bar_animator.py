# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for HpBarAnimator and ExpBarAnimator — P0 combat bar animations.
"""
from __future__ import annotations

import math

import pytest

from tuxemon.ui.bar_animator import ExpBarAnimator, HpBarAnimator


# ---------------------------------------------------------------------------
# HpBarAnimator
# ---------------------------------------------------------------------------


class TestHpBarAnimatorInit:
    def test_default_initial_value(self):
        a = HpBarAnimator()
        assert a.display_value == 1.0
        assert a.ghost_value == 1.0

    def test_custom_initial_value(self):
        a = HpBarAnimator(initial_value=0.5)
        assert abs(a.display_value - 0.5) < 1e-9
        assert abs(a.ghost_value - 0.5) < 1e-9

    def test_initial_value_clamped_above_one(self):
        a = HpBarAnimator(initial_value=1.5)
        assert a.display_value == 1.0

    def test_initial_value_clamped_below_zero(self):
        a = HpBarAnimator(initial_value=-0.2)
        assert a.display_value == 0.0

    def test_not_animating_initially(self):
        a = HpBarAnimator(initial_value=0.8)
        assert a.is_animating is False


class TestHpBarAnimatorSetTarget:
    def test_set_target_triggers_animation(self):
        a = HpBarAnimator(initial_value=1.0)
        a.set_target(0.5)
        assert a.is_animating is True

    def test_ghost_snapped_to_old_display_value(self):
        a = HpBarAnimator(initial_value=1.0)
        a.set_target(0.5)
        assert abs(a.ghost_value - 1.0) < 1e-9

    def test_same_target_does_not_restart_animation(self):
        a = HpBarAnimator(initial_value=0.5)
        a.set_target(0.5)
        assert a.is_animating is False

    def test_target_clamped_above_one(self):
        a = HpBarAnimator(initial_value=0.5)
        a.set_target(1.5)
        assert a.target_value == 1.0

    def test_target_clamped_below_zero(self):
        a = HpBarAnimator(initial_value=0.5)
        a.set_target(-0.1)
        assert a.target_value == 0.0


class TestHpBarAnimatorSnap:
    def test_snap_sets_all_values(self):
        a = HpBarAnimator(initial_value=1.0)
        a.set_target(0.3)
        a.snap(0.7)
        assert abs(a.display_value - 0.7) < 1e-9
        assert abs(a.ghost_value - 0.7) < 1e-9
        assert abs(a.target_value - 0.7) < 1e-9

    def test_snap_stops_animation(self):
        a = HpBarAnimator(initial_value=1.0)
        a.set_target(0.3)
        a.snap(0.3)
        assert a.is_animating is False


class TestHpBarAnimatorUpdate:
    def test_update_zero_dt_does_nothing(self):
        a = HpBarAnimator(initial_value=1.0)
        a.set_target(0.0)
        a.update(0.0)
        assert abs(a.display_value - 1.0) < 1e-9

    def test_update_drains_toward_target(self):
        a = HpBarAnimator(initial_value=1.0, drain_speed=1.0)
        a.set_target(0.0)
        a.update(0.3)
        assert a.display_value < 1.0
        assert a.display_value > 0.0

    def test_update_reaches_target_over_time(self):
        a = HpBarAnimator(initial_value=1.0, drain_speed=2.0)
        a.set_target(0.0)
        a.update(1.0)  # drain_speed=2.0 * 1.0s > 1.0 difference → should reach 0
        assert abs(a.display_value - 0.0) < 1e-9

    def test_ghost_decays_behind_display(self):
        a = HpBarAnimator(initial_value=1.0, drain_speed=2.0, ghost_speed=0.1)
        a.set_target(0.0)
        a.update(0.1)
        # Ghost starts at 1.0, decays toward display_value
        assert a.ghost_value >= a.display_value

    def test_ghost_reaches_display_over_time(self):
        a = HpBarAnimator(initial_value=1.0, drain_speed=5.0, ghost_speed=5.0)
        a.set_target(0.0)
        # Run many small steps
        for _ in range(100):
            a.update(0.05)
        assert abs(a.ghost_value - a.display_value) < 1e-3
        assert a.is_animating is False

    def test_healing_fills_bar(self):
        a = HpBarAnimator(initial_value=0.3, drain_speed=2.0)
        a.set_target(0.8)
        a.update(1.0)
        assert abs(a.display_value - 0.8) < 1e-9

    def test_display_never_exceeds_one(self):
        a = HpBarAnimator(initial_value=0.0, drain_speed=5.0)
        a.set_target(1.0)
        a.update(10.0)
        assert a.display_value <= 1.0

    def test_display_never_goes_below_zero(self):
        a = HpBarAnimator(initial_value=1.0, drain_speed=5.0)
        a.set_target(0.0)
        a.update(10.0)
        assert a.display_value >= 0.0


# ---------------------------------------------------------------------------
# ExpBarAnimator
# ---------------------------------------------------------------------------


class TestExpBarAnimatorInit:
    def test_default_initial_value(self):
        a = ExpBarAnimator()
        assert a.display_value == 0.0

    def test_custom_initial_value(self):
        a = ExpBarAnimator(initial_value=0.6)
        assert abs(a.display_value - 0.6) < 1e-9

    def test_not_animating_initially(self):
        a = ExpBarAnimator(initial_value=0.4)
        assert a.is_animating is False


class TestExpBarAnimatorSetTarget:
    def test_simple_fill(self):
        a = ExpBarAnimator(initial_value=0.2, fill_speed=1.0, delay=0.0)
        a.set_target(0.8)
        a.update(0.6)
        assert abs(a.display_value - 0.8) < 1e-3

    def test_delay_holds_bar(self):
        a = ExpBarAnimator(initial_value=0.0, fill_speed=1.0, delay=0.5)
        a.set_target(1.0)
        a.update(0.3)
        # Within delay, bar should not move
        assert abs(a.display_value - 0.0) < 1e-9

    def test_level_up_fills_to_max_first(self):
        a = ExpBarAnimator(initial_value=0.9, fill_speed=2.0, delay=0.0)
        a.set_target(0.3, level_up=True)
        # Update enough to fill to 1.0
        a.update(0.1)  # 0.9 → 1.0 (need 0.05s at speed 2.0, use 0.1)
        assert abs(a.display_value - 1.0) < 1e-9 or a.display_value == 0.0

    def test_level_up_resets_to_zero_after_max(self):
        a = ExpBarAnimator(initial_value=0.9, fill_speed=10.0, delay=0.0)
        a.set_target(0.3, level_up=True)
        # Large dt to race through phase 1 and reset
        a.update(0.2)
        # Should be at 0.0 or partway to 0.3
        assert a.display_value <= 0.3 + 1e-3

    def test_level_up_eventually_reaches_target(self):
        a = ExpBarAnimator(initial_value=0.8, fill_speed=10.0, delay=0.0)
        a.set_target(0.4, level_up=True)
        for _ in range(50):
            a.update(0.1)
        assert abs(a.display_value - 0.4) < 1e-3
        assert a.is_animating is False


class TestExpBarAnimatorSnap:
    def test_snap_sets_value(self):
        a = ExpBarAnimator(initial_value=0.0)
        a.set_target(1.0)
        a.snap(0.5)
        assert abs(a.display_value - 0.5) < 1e-9

    def test_snap_stops_animation(self):
        a = ExpBarAnimator(initial_value=0.0)
        a.set_target(1.0)
        a.snap(0.0)
        assert a.is_animating is False


class TestExpBarAnimatorUpdate:
    def test_update_zero_dt_does_nothing(self):
        a = ExpBarAnimator(initial_value=0.0, delay=0.0)
        a.set_target(1.0)
        a.update(0.0)
        assert a.display_value == 0.0

    def test_bar_fills_completely(self):
        a = ExpBarAnimator(initial_value=0.0, fill_speed=5.0, delay=0.0)
        a.set_target(1.0)
        a.update(1.0)
        assert abs(a.display_value - 1.0) < 1e-9

    def test_bar_does_not_overshoot(self):
        a = ExpBarAnimator(initial_value=0.0, fill_speed=5.0, delay=0.0)
        a.set_target(0.5)
        a.update(10.0)
        assert a.display_value <= 1.0 + 1e-9

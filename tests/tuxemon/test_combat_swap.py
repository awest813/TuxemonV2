# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from unittest.mock import MagicMock

from tuxemon.ui.combat_swap import SwapTracker


class TestSwapTracker(unittest.TestCase):
    def setUp(self):
        self.tracker = SwapTracker()
        self.monster_a = MagicMock(name="MonsterA")
        self.monster_b = MagicMock(name="MonsterB")

    def test_initial_state(self):
        self.assertTrue(self.tracker.can_swap(self.monster_a))

    def test_register_blocks_swap_this_turn(self):
        self.tracker.register(self.monster_a)
        self.assertFalse(self.tracker.can_swap(self.monster_a))
        self.assertTrue(self.tracker.can_swap(self.monster_b))

    def test_clear_resets_turn_state(self):
        self.tracker.register(self.monster_a)
        self.tracker.block_swap(self.monster_b, reason="test")
        self.tracker.clear()
        self.assertTrue(self.tracker.can_swap(self.monster_a))
        self.assertTrue(self.tracker.can_swap(self.monster_b))

    def test_temp_block(self):
        self.tracker.block_swap(self.monster_a, reason="confused")
        self.assertFalse(self.tracker.can_swap(self.monster_a))

    def test_persistent_block(self):
        self.tracker.block_swap(
            self.monster_a, reason="trapped", persistent=True
        )
        self.assertFalse(self.tracker.can_swap(self.monster_a))
        self.tracker.clear()
        self.assertFalse(self.tracker.can_swap(self.monster_a))

    def test_unblock_removes_temp(self):
        self.tracker.block_swap(self.monster_a, reason="test")
        self.tracker.unblock_swap(self.monster_a)
        self.assertTrue(self.tracker.can_swap(self.monster_a))

    def test_unblock_removes_persistent(self):
        self.tracker.block_swap(
            self.monster_a, reason="trapped", persistent=True
        )
        self.tracker.unblock_swap(self.monster_a)
        self.assertTrue(self.tracker.can_swap(self.monster_a))

    def test_reset_all_clears_everything(self):
        self.tracker.register(self.monster_a)
        self.tracker.block_swap(self.monster_b, reason="test")
        self.tracker.block_swap(
            self.monster_a, reason="trapped", persistent=True
        )
        self.tracker.reset_all()
        self.assertTrue(self.tracker.can_swap(self.monster_a))
        self.assertTrue(self.tracker.can_swap(self.monster_b))

    def test_multiple_monsters(self):
        self.tracker.register(self.monster_a)
        self.tracker.block_swap(self.monster_b, reason="effect")
        self.assertFalse(self.tracker.can_swap(self.monster_a))
        self.assertFalse(self.tracker.can_swap(self.monster_b))

    def test_unblock_nonexistent_is_safe(self):
        self.tracker.unblock_swap(self.monster_a)
        self.assertTrue(self.tracker.can_swap(self.monster_a))

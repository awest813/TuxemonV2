# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest

from tuxemon.menu.input import (
    CharacterSetManager,
    InputController,
)


class TestInputController(unittest.TestCase):
    def test_initial_string(self):
        ctrl = InputController("hello")
        self.assertEqual(ctrl.current_string, "hello")
        self.assertEqual(ctrl.initial_string, "hello")

    def test_add_char(self):
        ctrl = InputController("", char_limit=5)
        self.assertTrue(ctrl.add_char("a"))
        self.assertEqual(ctrl.current_string, "a")

    def test_add_char_at_limit(self):
        ctrl = InputController("abc", char_limit=3)
        self.assertFalse(ctrl.add_char("d"))
        self.assertEqual(ctrl.current_string, "abc")

    def test_backspace(self):
        ctrl = InputController("abc")
        ctrl.backspace()
        self.assertEqual(ctrl.current_string, "ab")

    def test_backspace_empty(self):
        ctrl = InputController("")
        ctrl.backspace()
        self.assertEqual(ctrl.current_string, "")

    def test_set_string(self):
        ctrl = InputController("", char_limit=5)
        ctrl.set_string("test")
        self.assertEqual(ctrl.current_string, "test")

    def test_set_string_truncates_at_limit(self):
        ctrl = InputController("", char_limit=3)
        ctrl.set_string("abcdef")
        self.assertEqual(ctrl.current_string, "abc")

    def test_clear_resets_to_initial(self):
        ctrl = InputController("initial")
        ctrl.set_string("changed")
        ctrl.clear()
        self.assertEqual(ctrl.current_string, "initial")

    def test_remaining_chars(self):
        ctrl = InputController("ab", char_limit=5)
        self.assertEqual(ctrl.remaining_chars, 3)

    def test_char_limit_property(self):
        ctrl = InputController("", char_limit=10)
        self.assertEqual(ctrl.char_limit, 10)


class TestCharacterSetManager(unittest.TestCase):
    def test_default_init(self):
        mgr = CharacterSetManager(chars="ABCDEF")
        self.assertEqual(mgr.chars, "ABCDEF")

    def test_get_char_variants_none(self):
        mgr = CharacterSetManager(chars="ABC", char_variants="")
        self.assertEqual(mgr.get_char_variants("A"), "")

    def test_get_char_variants_with_data(self):
        mgr = CharacterSetManager(chars="A", char_variants="Aàáâ")
        self.assertEqual(mgr.get_char_variants("A"), "àáâ")

    def test_is_valid_input_char(self):
        mgr = CharacterSetManager(chars="ABC")
        self.assertTrue(mgr.is_valid_input_char("A"))
        self.assertFalse(mgr.is_valid_input_char("Z"))

    def test_space_is_always_valid(self):
        mgr = CharacterSetManager(chars="ABC")
        self.assertTrue(mgr.is_valid_input_char(" "))

    def test_get_layout_grid(self):
        mgr = CharacterSetManager(chars="ABCDEF")
        grid = mgr.get_layout_grid(3)
        self.assertEqual(len(grid), 2)
        self.assertEqual(grid[0], ["A", "B", "C"])
        self.assertEqual(grid[1], ["D", "E", "F"])

    def test_get_layout_grid_partial_row(self):
        mgr = CharacterSetManager(chars="ABCDE")
        grid = mgr.get_layout_grid(3)
        self.assertEqual(len(grid), 2)
        self.assertEqual(grid[1], ["D", "E"])

    def test_parse_char_variants_untranslated(self):
        mgr = CharacterSetManager(
            chars="A", char_variants="menu_char_variants"
        )
        self.assertEqual(mgr.char_variants, {})

# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest

from tuxemon.menu.controller import MenuController, MenuState


class TestMenuController(unittest.TestCase):
    def setUp(self):
        self.ctrl = MenuController()

    def test_initial_state_is_closed(self):
        self.assertEqual(self.ctrl.state, MenuState.CLOSED)
        self.assertTrue(self.ctrl.is_closed())

    def test_open_from_closed(self):
        self.ctrl.open()
        self.assertEqual(self.ctrl.state, MenuState.OPENING)
        self.assertTrue(self.ctrl.is_opening())

    def test_open_when_already_opening(self):
        self.ctrl.open()
        self.ctrl.open()
        self.assertEqual(self.ctrl.state, MenuState.OPENING)

    def test_open_when_already_normal(self):
        self.ctrl.open()
        self.ctrl.set_normal()
        self.ctrl.open()
        self.assertEqual(self.ctrl.state, MenuState.NORMAL)

    def test_set_normal_from_opening(self):
        self.ctrl.open()
        self.ctrl.set_normal()
        self.assertEqual(self.ctrl.state, MenuState.NORMAL)
        self.assertTrue(self.ctrl.is_enabled())

    def test_set_normal_from_disabled(self):
        self.ctrl.open()
        self.ctrl.set_normal()
        self.ctrl.disable()
        self.ctrl.set_normal()
        self.assertEqual(self.ctrl.state, MenuState.NORMAL)

    def test_set_normal_when_already_normal(self):
        self.ctrl.open()
        self.ctrl.set_normal()
        self.ctrl.set_normal()
        self.assertEqual(self.ctrl.state, MenuState.NORMAL)

    def test_set_normal_from_closed_is_ignored(self):
        self.ctrl.set_normal()
        self.assertEqual(self.ctrl.state, MenuState.CLOSED)

    def test_disable_from_normal(self):
        self.ctrl.open()
        self.ctrl.set_normal()
        self.ctrl.disable()
        self.assertEqual(self.ctrl.state, MenuState.DISABLED)
        self.assertTrue(self.ctrl.is_disabled())

    def test_disable_when_already_disabled(self):
        self.ctrl.open()
        self.ctrl.set_normal()
        self.ctrl.disable()
        self.ctrl.disable()
        self.assertEqual(self.ctrl.state, MenuState.DISABLED)

    def test_disable_from_closed_is_ignored(self):
        self.ctrl.disable()
        self.assertEqual(self.ctrl.state, MenuState.CLOSED)

    def test_enable_from_disabled(self):
        self.ctrl.open()
        self.ctrl.set_normal()
        self.ctrl.disable()
        self.ctrl.enable()
        self.assertEqual(self.ctrl.state, MenuState.NORMAL)

    def test_enable_when_already_normal(self):
        self.ctrl.open()
        self.ctrl.set_normal()
        self.ctrl.enable()
        self.assertEqual(self.ctrl.state, MenuState.NORMAL)

    def test_close_from_normal(self):
        self.ctrl.open()
        self.ctrl.set_normal()
        self.ctrl.close()
        self.assertEqual(self.ctrl.state, MenuState.CLOSING)
        self.assertTrue(self.ctrl.is_closing())

    def test_close_from_disabled(self):
        self.ctrl.open()
        self.ctrl.set_normal()
        self.ctrl.disable()
        self.ctrl.close()
        self.assertEqual(self.ctrl.state, MenuState.CLOSING)

    def test_close_when_already_closing(self):
        self.ctrl.open()
        self.ctrl.set_normal()
        self.ctrl.close()
        self.ctrl.close()
        self.assertEqual(self.ctrl.state, MenuState.CLOSING)

    def test_close_from_closed_is_ignored(self):
        self.ctrl.close()
        self.assertEqual(self.ctrl.state, MenuState.CLOSED)

    def test_reset(self):
        self.ctrl.open()
        self.ctrl.set_normal()
        self.ctrl.reset()
        self.assertEqual(self.ctrl.state, MenuState.CLOSED)
        self.assertTrue(self.ctrl.is_closed())

    def test_is_interactive_when_normal(self):
        self.ctrl.open()
        self.ctrl.set_normal()
        self.assertTrue(self.ctrl.is_interactive())

    def test_is_interactive_when_opening(self):
        self.ctrl.open()
        self.assertTrue(self.ctrl.is_interactive())

    def test_is_interactive_when_disabled(self):
        self.ctrl.open()
        self.ctrl.set_normal()
        self.ctrl.disable()
        self.assertFalse(self.ctrl.is_interactive())

    def test_is_interactive_when_closed(self):
        self.assertFalse(self.ctrl.is_interactive())

    def test_full_lifecycle(self):
        self.assertTrue(self.ctrl.is_closed())
        self.ctrl.open()
        self.assertTrue(self.ctrl.is_opening())
        self.ctrl.set_normal()
        self.assertTrue(self.ctrl.is_enabled())
        self.ctrl.disable()
        self.assertTrue(self.ctrl.is_disabled())
        self.ctrl.enable()
        self.assertTrue(self.ctrl.is_enabled())
        self.ctrl.close()
        self.assertTrue(self.ctrl.is_closing())
        self.ctrl.reset()
        self.assertTrue(self.ctrl.is_closed())

    def test_open_from_closing_is_ignored(self):
        self.ctrl.open()
        self.ctrl.set_normal()
        self.ctrl.close()
        self.ctrl.open()
        self.assertEqual(self.ctrl.state, MenuState.CLOSING)

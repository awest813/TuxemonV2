# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import unittest
from unittest.mock import MagicMock, patch

from tuxemon.ui.combat_notifier import TextAnimationManager


class TestTextAnimationManager(unittest.TestCase):
    def setUp(self):
        self.manager = TextAnimationManager()

    def test_initial_state(self):
        self.assertEqual(len(self.manager.text_queue), 0)
        self.assertIsNone(self.manager.pending_xp_duration)

    @patch("tuxemon.ui.combat_notifier.config_combat")
    def test_compute_text_anim_time(self, mock_config):
        mock_config.action_time = 1.0
        mock_config.letter_time = 0.05
        result = TextAnimationManager.compute_text_anim_time("Hello")
        self.assertAlmostEqual(result, 1.25)

    def test_add_text_animation(self):
        callback = MagicMock()
        self.manager.add_text_animation(callback, 2.0)
        self.assertEqual(len(self.manager.text_queue), 1)

    def test_update_text_animation_triggers_next(self):
        callback = MagicMock()
        self.manager.add_text_animation(callback, 1.0)
        self.manager._text_time_left = 0
        self.manager.update_text_animation(0.01)
        callback.assert_called_once()

    def test_update_text_animation_no_trigger_when_time_remains(self):
        callback = MagicMock()
        self.manager.add_text_animation(callback, 1.0)
        self.manager._text_time_left = 5.0
        self.manager.update_text_animation(1.0)
        callback.assert_not_called()

    def test_add_xp_message(self):
        self.manager.add_xp_message("Gained 50 XP!")
        self.assertEqual(len(self.manager._xp_messages), 1)

    @patch("tuxemon.ui.combat_notifier.config_combat")
    def test_trigger_xp_animation(self, mock_config):
        mock_config.action_time = 0.5
        mock_config.letter_time = 0.01
        self.manager.add_xp_message("Gained XP!")
        alert_func = MagicMock()
        text_area = MagicMock()
        self.manager.trigger_xp_animation(alert_func, text_area)
        self.assertEqual(len(self.manager.text_queue), 1)
        self.assertIsNotNone(self.manager.pending_xp_duration)

    def test_consume_pending_xp_duration(self):
        self.manager._pending_xp_duration = 2.5
        duration = self.manager.consume_pending_xp_duration()
        self.assertEqual(duration, 2.5)
        self.assertIsNone(self.manager.pending_xp_duration)

    def test_consume_pending_xp_duration_when_none(self):
        duration = self.manager.consume_pending_xp_duration()
        self.assertIsNone(duration)

    def test_get_text_animation_time_left(self):
        self.manager._text_time_left = 3.14
        self.assertAlmostEqual(
            self.manager.get_text_animation_time_left(), 3.14
        )

    def test_multiple_animations_in_sequence(self):
        cb1 = MagicMock()
        cb2 = MagicMock()
        self.manager.add_text_animation(cb1, 1.0)
        self.manager.add_text_animation(cb2, 2.0)

        self.manager._text_time_left = 0
        self.manager.update_text_animation(0.01)
        cb1.assert_called_once()
        cb2.assert_not_called()

        self.manager.update_text_animation(1.1)
        cb2.assert_called_once()

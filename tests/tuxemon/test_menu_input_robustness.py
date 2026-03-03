# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for Phase 1.1 input handling robustness:
  - Configurable repeat delay / interval
  - Single-press-only accessibility mode
  - Analog dead-zone filtering
  - Cursor wrapping (first ↔ last item navigation)
"""
from unittest.mock import Mock

import pytest

from tuxemon.menu.input_handler import MenuInputHandler, PygameMenuInputHandler
from tuxemon.platform.const import buttons
from tuxemon.platform.events import PlayerInput


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def real_event(button, value=1, hold_time=1, hold_duration=0.0, previous_value=0):
    e = PlayerInput(button, value=value)
    e.hold_time = hold_time
    e.hold_duration = hold_duration
    e.previous_value = previous_value
    return e


def fake_menu_items(items):
    menu_items = Mock()
    menu_items.__iter__ = lambda self=menu_items: iter(items)
    menu_items.__getitem__ = lambda self, i: items[i]
    menu_items.__len__ = lambda self: len(items)
    menu_items.rect = Mock()
    menu_items.rect.left = 0
    menu_items.rect.top = 0
    menu_items.rect.collidepoint.return_value = False
    menu_items.update_rect_from_parent = Mock()
    return menu_items


@pytest.fixture
def menu():
    m = Mock()
    m.state_controller.is_enabled.return_value = True
    m.escape_key_exits = True
    m.touch_aware = False
    item1 = Mock(enabled=True)
    item1.rect.collidepoint.return_value = False
    item2 = Mock(enabled=True)
    item2.rect.collidepoint.return_value = False
    m.menu_items = fake_menu_items([item1, item2])
    m.selected_index = 0
    m.get_selected_item.return_value = item1
    return m


# ---------------------------------------------------------------------------
# Configurable repeat delay / interval
# ---------------------------------------------------------------------------


def test_custom_repeat_delay_accepted(menu):
    handler = MenuInputHandler(menu, repeat_delay=1.0, repeat_interval=0.2)
    assert handler._repeat_delay == 1.0
    assert handler._repeat_interval == 0.2


def test_default_repeat_delay_used_when_none(menu):
    handler = MenuInputHandler(menu)
    assert handler._repeat_delay == MenuInputHandler.REPEAT_DELAY
    assert handler._repeat_interval == MenuInputHandler.REPEAT_INTERVAL


def test_held_event_not_repeated_before_custom_delay(menu):
    handler = MenuInputHandler(menu, repeat_delay=2.0)
    event = real_event(
        buttons.DOWN, hold_time=10, hold_duration=1.5, previous_value=1
    )
    # event is held but below custom delay of 2.0 s
    assert not handler._repeat_due(buttons.DOWN, event)


def test_held_event_repeated_after_custom_delay(menu):
    import time

    handler = MenuInputHandler(menu, repeat_delay=0.1, repeat_interval=0.05)
    event = real_event(
        buttons.DOWN, hold_time=10, hold_duration=0.2, previous_value=1
    )
    # Prime the timer to far past
    handler._repeat_timers[buttons.DOWN] = time.time() - 1.0
    assert handler._repeat_due(buttons.DOWN, event)


# ---------------------------------------------------------------------------
# Single-press-only (accessibility) mode
# ---------------------------------------------------------------------------


def test_single_press_only_disables_repeat(menu):
    handler = MenuInputHandler(menu, single_press_only=True)
    event = real_event(
        buttons.DOWN, hold_time=10, hold_duration=5.0, previous_value=1
    )
    # Even after a long hold, _repeat_due must return False
    assert not handler._repeat_due(buttons.DOWN, event)


def test_single_press_only_false_allows_repeat(menu):
    import time

    handler = MenuInputHandler(menu, single_press_only=False, repeat_delay=0.05)
    event = real_event(
        buttons.DOWN, hold_time=10, hold_duration=0.2, previous_value=1
    )
    handler._repeat_timers[buttons.DOWN] = time.time() - 1.0
    assert handler._repeat_due(buttons.DOWN, event)


# ---------------------------------------------------------------------------
# Analog dead-zone
# ---------------------------------------------------------------------------


def test_analog_value_below_deadzone_is_filtered(menu):
    handler = MenuInputHandler(menu)
    event = real_event(buttons.A, value=0.1)
    assert handler._is_analog_deadzone(event) is True


def test_analog_value_above_deadzone_not_filtered(menu):
    handler = MenuInputHandler(menu)
    event = real_event(buttons.A, value=0.5)
    assert handler._is_analog_deadzone(event) is False


def test_non_float_value_not_filtered(menu):
    handler = MenuInputHandler(menu)
    event = real_event(buttons.A, value=1)
    assert handler._is_analog_deadzone(event) is False


def test_analog_negative_below_deadzone_filtered(menu):
    handler = MenuInputHandler(menu)
    event = real_event(buttons.A, value=-0.1)
    assert handler._is_analog_deadzone(event) is True


def test_analog_negative_above_deadzone_not_filtered(menu):
    handler = MenuInputHandler(menu)
    event = real_event(buttons.A, value=-0.5)
    assert handler._is_analog_deadzone(event) is False


# ---------------------------------------------------------------------------
# Cursor wrap-around
# ---------------------------------------------------------------------------


def test_cursor_move_calls_change_selection(menu):
    handler = MenuInputHandler(menu)
    new_index = 1
    menu.menu_items.determine_cursor_movement.return_value = new_index
    event = real_event(buttons.DOWN, value=1, hold_time=1)
    handler._cursor_move(event)
    menu.change_selection.assert_called_once_with(new_index)


def test_cursor_no_change_when_same_index(menu):
    handler = MenuInputHandler(menu)
    menu.menu_items.determine_cursor_movement.return_value = 0
    event = real_event(buttons.DOWN, value=1, hold_time=1)
    handler._cursor_move(event)
    menu.change_selection.assert_not_called()


def test_cursor_wraps_from_last_to_first(menu):
    """determine_cursor_movement returning 0 from index 1 simulates wrap."""
    handler = MenuInputHandler(menu)
    menu.selected_index = 1
    menu.menu_items.determine_cursor_movement.return_value = 0
    event = real_event(buttons.DOWN, value=1, hold_time=1)
    handler._cursor_move(event)
    menu.change_selection.assert_called_once_with(0)


def test_cursor_wraps_from_first_to_last(menu):
    """determine_cursor_movement returning last index from 0 simulates wrap."""
    handler = MenuInputHandler(menu)
    menu.selected_index = 0
    last_index = len(list(menu.menu_items)) - 1
    menu.menu_items.determine_cursor_movement.return_value = last_index
    event = real_event(buttons.UP, value=1, hold_time=1)
    handler._cursor_move(event)
    menu.change_selection.assert_called_once_with(last_index)


# ---------------------------------------------------------------------------
# PygameMenuInputHandler — single_press_only and custom repeat_delay
# ---------------------------------------------------------------------------


@pytest.fixture
def pygame_state():
    s = Mock()
    s.state_controller.is_interactive.return_value = True
    s.menu.is_enabled.return_value = True
    s.menu.update = Mock()
    s.menu.get_selected_widget.return_value = "w"
    s.escape_key_exits = True
    s.open = True
    s.selected_widget = None
    return s


def test_pygame_handler_custom_repeat_delay(pygame_state):
    handler = PygameMenuInputHandler(pygame_state, repeat_delay=2.0)
    assert handler._repeat_delay == 2.0


def test_pygame_handler_single_press_only_ignores_held(pygame_state):
    """With single_press_only, held directional buttons should not update menu."""
    handler = PygameMenuInputHandler(pygame_state, single_press_only=True)
    pygame_event = Mock()
    handler._convert_event = Mock(return_value=pygame_event)
    handler._is_press = Mock(return_value=True)

    event = Mock()
    event.button = buttons.DOWN
    event.pressed = False  # held, not just pressed
    result = handler.handle_event(event)

    assert result is None
    pygame_state.menu.update.assert_not_called()


def test_pygame_handler_single_press_only_accepts_press(pygame_state):
    """With single_press_only, a fresh press should still trigger update."""
    handler = PygameMenuInputHandler(pygame_state, single_press_only=True)
    pygame_event = Mock()
    handler._convert_event = Mock(return_value=pygame_event)

    event = Mock()
    event.button = buttons.DOWN
    event.pressed = True
    result = handler.handle_event(event)

    assert result is None
    pygame_state.menu.update.assert_called_once_with([pygame_event])

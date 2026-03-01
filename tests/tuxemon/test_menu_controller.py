# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for MenuController state machine transitions and helper predicates.
"""
import pytest

from tuxemon.menu.controller import MenuController, MenuState


@pytest.fixture
def ctrl():
    return MenuController()


# ---------------------------------------------------------------------------
# Initial state
# ---------------------------------------------------------------------------


def test_initial_state_is_closed(ctrl):
    assert ctrl.state == MenuState.CLOSED
    assert ctrl.is_closed()


# ---------------------------------------------------------------------------
# open()
# ---------------------------------------------------------------------------


def test_open_from_closed_transitions_to_opening(ctrl):
    ctrl.open()
    assert ctrl.state == MenuState.OPENING
    assert ctrl.is_opening()


def test_open_from_opening_is_idempotent(ctrl):
    ctrl.open()
    ctrl.open()  # second call is a no-op
    assert ctrl.state == MenuState.OPENING


def test_open_from_normal_is_ignored(ctrl):
    ctrl.open()
    ctrl.set_normal()
    ctrl.open()  # should be ignored; menu is already open
    assert ctrl.state == MenuState.NORMAL


def test_open_from_disabled_logs_warning(ctrl, caplog):
    ctrl.open()
    ctrl.set_normal()
    ctrl.disable()
    with caplog.at_level("WARNING"):
        ctrl.open()
    assert ctrl.state == MenuState.DISABLED


def test_open_from_closing_logs_warning(ctrl, caplog):
    ctrl.open()
    ctrl.set_normal()
    ctrl.close()
    with caplog.at_level("WARNING"):
        ctrl.open()
    assert ctrl.state == MenuState.CLOSING


# ---------------------------------------------------------------------------
# set_normal()
# ---------------------------------------------------------------------------


def test_set_normal_from_opening(ctrl):
    ctrl.open()
    ctrl.set_normal()
    assert ctrl.state == MenuState.NORMAL
    assert ctrl.is_enabled()


def test_set_normal_from_disabled(ctrl):
    ctrl.open()
    ctrl.set_normal()
    ctrl.disable()
    ctrl.set_normal()
    assert ctrl.state == MenuState.NORMAL


def test_set_normal_from_normal_is_idempotent(ctrl):
    ctrl.open()
    ctrl.set_normal()
    ctrl.set_normal()  # second call is a no-op
    assert ctrl.state == MenuState.NORMAL


def test_set_normal_from_closed_logs_warning(ctrl, caplog):
    with caplog.at_level("WARNING"):
        ctrl.set_normal()
    assert ctrl.state == MenuState.CLOSED


# ---------------------------------------------------------------------------
# disable() / enable()
# ---------------------------------------------------------------------------


def test_disable_from_normal(ctrl):
    ctrl.open()
    ctrl.set_normal()
    ctrl.disable()
    assert ctrl.state == MenuState.DISABLED
    assert ctrl.is_disabled()


def test_disable_from_disabled_is_idempotent(ctrl):
    ctrl.open()
    ctrl.set_normal()
    ctrl.disable()
    ctrl.disable()  # second call is a no-op
    assert ctrl.state == MenuState.DISABLED


def test_enable_from_disabled(ctrl):
    ctrl.open()
    ctrl.set_normal()
    ctrl.disable()
    ctrl.enable()
    assert ctrl.state == MenuState.NORMAL


def test_enable_from_normal_is_idempotent(ctrl):
    ctrl.open()
    ctrl.set_normal()
    ctrl.enable()  # already enabled — no-op
    assert ctrl.state == MenuState.NORMAL


def test_enable_from_closed_logs_warning(ctrl, caplog):
    with caplog.at_level("WARNING"):
        ctrl.enable()
    assert ctrl.state == MenuState.CLOSED


# ---------------------------------------------------------------------------
# close()
# ---------------------------------------------------------------------------


def test_close_from_normal(ctrl):
    ctrl.open()
    ctrl.set_normal()
    ctrl.close()
    assert ctrl.state == MenuState.CLOSING
    assert ctrl.is_closing()


def test_close_from_disabled(ctrl):
    ctrl.open()
    ctrl.set_normal()
    ctrl.disable()
    ctrl.close()
    assert ctrl.state == MenuState.CLOSING


def test_close_from_opening(ctrl):
    """Closing during the opening animation must be supported.

    Without this, pressing Back while the open animation plays would
    leave the MenuController stuck in OPENING forever.
    """
    ctrl.open()
    assert ctrl.is_opening()
    ctrl.close()
    assert ctrl.state == MenuState.CLOSING


def test_close_from_closing_is_idempotent(ctrl):
    ctrl.open()
    ctrl.set_normal()
    ctrl.close()
    ctrl.close()  # second call is a no-op
    assert ctrl.state == MenuState.CLOSING


def test_close_from_closed_logs_warning(ctrl, caplog):
    with caplog.at_level("WARNING"):
        ctrl.close()
    assert ctrl.state == MenuState.CLOSED


# ---------------------------------------------------------------------------
# reset()
# ---------------------------------------------------------------------------


def test_reset_from_any_state_returns_to_closed(ctrl):
    for transition in [
        lambda c: None,                         # CLOSED
        lambda c: c.open(),                      # OPENING
        lambda c: (c.open(), c.set_normal()),    # NORMAL
        lambda c: (c.open(), c.set_normal(), c.disable()),  # DISABLED
        lambda c: (c.open(), c.set_normal(), c.close()),    # CLOSING
    ]:
        c = MenuController()
        transition(c)
        c.reset()
        assert c.state == MenuState.CLOSED


# ---------------------------------------------------------------------------
# Predicate helpers
# ---------------------------------------------------------------------------


def test_is_interactive_true_for_normal_and_opening(ctrl):
    ctrl.open()
    assert ctrl.is_interactive()  # OPENING
    ctrl.set_normal()
    assert ctrl.is_interactive()  # NORMAL


def test_is_interactive_false_for_other_states(ctrl):
    assert not ctrl.is_interactive()  # CLOSED
    ctrl.open()
    ctrl.set_normal()
    ctrl.disable()
    assert not ctrl.is_interactive()  # DISABLED
    ctrl.close()
    assert not ctrl.is_interactive()  # CLOSING


def test_is_opening_helper(ctrl):
    assert not ctrl.is_opening()
    ctrl.open()
    assert ctrl.is_opening()
    ctrl.set_normal()
    assert not ctrl.is_opening()


def test_is_closing_helper(ctrl):
    assert not ctrl.is_closing()
    ctrl.open()
    ctrl.set_normal()
    ctrl.close()
    assert ctrl.is_closing()
    ctrl.reset()
    assert not ctrl.is_closing()


# ---------------------------------------------------------------------------
# Full lifecycle round-trip
# ---------------------------------------------------------------------------


def test_full_open_close_cycle(ctrl):
    assert ctrl.is_closed()
    ctrl.open()
    assert ctrl.is_opening()
    ctrl.set_normal()
    assert ctrl.is_enabled()
    ctrl.close()
    assert ctrl.is_closing()
    ctrl.reset()
    assert ctrl.is_closed()


def test_disable_enable_cycle(ctrl):
    ctrl.open()
    ctrl.set_normal()
    ctrl.disable()
    assert ctrl.is_disabled()
    ctrl.enable()
    assert ctrl.is_enabled()

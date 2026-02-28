from __future__ import annotations

from unittest.mock import Mock

from tuxemon.states.phone_banking import NuPhoneBanking


def _build_state() -> NuPhoneBanking:
    state = NuPhoneBanking.__new__(NuPhoneBanking)
    state.client = Mock()
    return state


def test_open_amount_picker_uses_minimum_of_one_for_small_amounts() -> None:
    state = _build_state()
    callback = Mock()

    state._open_amount_picker(max_value=50, callback=callback, title="Deposit")

    state.client.push_state.assert_called_once_with(
        "NumberPickerState",
        min_value=1,
        max_value=50,
        callback=callback,
        title="Deposit",
        step=1,
        escape_key_exits=True,
    )


def test_open_amount_picker_keeps_large_amount_step() -> None:
    state = _build_state()
    callback = Mock()

    state._open_amount_picker(max_value=500, callback=callback, title="Withdraw")

    state.client.push_state.assert_called_once_with(
        "NumberPickerState",
        min_value=1,
        max_value=500,
        callback=callback,
        title="Withdraw",
        step=100,
        escape_key_exits=True,
    )

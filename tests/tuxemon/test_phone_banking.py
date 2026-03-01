from __future__ import annotations

from unittest.mock import Mock

import pytest

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


def test_select_bill_amount_builds_pay_callback() -> None:
    state = _build_state()
    money_manager = Mock()
    money_manager.get_money.return_value = 123
    state.char = Mock()
    state.char.money_controller.money_manager = money_manager
    state._open_amount_picker = Mock()
    state._pay = Mock()

    state._select_bill_amount("pay", "internet_bill")

    state._open_amount_picker.assert_called_once()
    callback = state._open_amount_picker.call_args.kwargs["callback"]
    callback(20)
    state._pay.assert_called_once_with(20, "internet_bill")


def test_select_bill_amount_rejects_unknown_operation() -> None:
    state = _build_state()
    state.char = Mock()
    state.char.money_controller.money_manager = Mock()

    with pytest.raises(ValueError, match="Unsupported bill operation"):
        state._select_bill_amount("unknown_op", "internet_bill")

# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for CoinWallet — Phase 2 in-game casino economy.

Verifies the earn-only, daily-cap, and no-real-money design constraints.
"""

from __future__ import annotations

import pytest

from tuxemon.economy.coin_wallet import (
    DEFAULT_DAILY_EARN_CAP,
    CoinWallet,
    InsufficientCoinsError,
)


@pytest.fixture
def wallet() -> CoinWallet:
    return CoinWallet()


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


def test_default_initial_state(wallet: CoinWallet):
    assert wallet.balance == 0
    assert wallet.daily_earned == 0
    assert wallet.daily_earn_cap == DEFAULT_DAILY_EARN_CAP


def test_custom_daily_earn_cap():
    w = CoinWallet(daily_earn_cap=500)
    assert w.daily_earn_cap == 500


def test_invalid_daily_earn_cap_raises():
    with pytest.raises(ValueError):
        CoinWallet(daily_earn_cap=0)

    with pytest.raises(ValueError):
        CoinWallet(daily_earn_cap=-1)


# ---------------------------------------------------------------------------
# earn()
# ---------------------------------------------------------------------------


def test_earn_increases_balance(wallet: CoinWallet):
    wallet.earn(100)
    assert wallet.balance == 100


def test_earn_returns_actual_amount(wallet: CoinWallet):
    actual = wallet.earn(200)
    assert actual == 200


def test_earn_increases_daily_earned(wallet: CoinWallet):
    wallet.earn(300)
    assert wallet.daily_earned == 300


def test_earn_zero_raises(wallet: CoinWallet):
    with pytest.raises(ValueError):
        wallet.earn(0)


def test_earn_negative_raises(wallet: CoinWallet):
    with pytest.raises(ValueError):
        wallet.earn(-50)


def test_earn_capped_at_daily_limit():
    w = CoinWallet(daily_earn_cap=1000)
    w.earn(900)
    actual = w.earn(200)
    assert actual == 100
    assert w.balance == 1000
    assert w.daily_earned == 1000


def test_earn_returns_zero_when_cap_already_reached():
    w = CoinWallet(daily_earn_cap=100)
    w.earn(100)
    actual = w.earn(50)
    assert actual == 0
    assert w.balance == 100


def test_daily_earn_remaining_decreases(wallet: CoinWallet):
    wallet.earn(500)
    assert wallet.daily_earn_remaining == DEFAULT_DAILY_EARN_CAP - 500


def test_daily_earn_remaining_zero_when_cap_hit():
    w = CoinWallet(daily_earn_cap=100)
    w.earn(100)
    assert w.daily_earn_remaining == 0


# ---------------------------------------------------------------------------
# spend()
# ---------------------------------------------------------------------------


def test_spend_decreases_balance(wallet: CoinWallet):
    wallet.earn(500)
    wallet.spend(200)
    assert wallet.balance == 300


def test_spend_exact_balance(wallet: CoinWallet):
    wallet.earn(100)
    wallet.spend(100)
    assert wallet.balance == 0


def test_spend_more_than_balance_raises(wallet: CoinWallet):
    wallet.earn(50)
    with pytest.raises(InsufficientCoinsError):
        wallet.spend(100)


def test_spend_zero_raises(wallet: CoinWallet):
    with pytest.raises(ValueError):
        wallet.spend(0)


def test_spend_negative_raises(wallet: CoinWallet):
    with pytest.raises(ValueError):
        wallet.spend(-10)


def test_balance_never_goes_negative(wallet: CoinWallet):
    with pytest.raises(InsufficientCoinsError):
        wallet.spend(1)
    assert wallet.balance == 0


# ---------------------------------------------------------------------------
# reset_daily()
# ---------------------------------------------------------------------------


def test_reset_daily_clears_daily_earned(wallet: CoinWallet):
    wallet.earn(200)
    wallet.reset_daily()
    assert wallet.daily_earned == 0


def test_reset_daily_does_not_affect_balance(wallet: CoinWallet):
    wallet.earn(200)
    wallet.reset_daily()
    assert wallet.balance == 200


def test_earn_after_daily_reset_uses_full_cap():
    w = CoinWallet(daily_earn_cap=100)
    w.earn(100)
    w.reset_daily()
    actual = w.earn(100)
    assert actual == 100
    assert w.balance == 200


# ---------------------------------------------------------------------------
# encode() / decode()
# ---------------------------------------------------------------------------


def test_encode_decode_round_trip(wallet: CoinWallet):
    wallet.earn(750)
    wallet.spend(250)
    data = wallet.encode()

    wallet2 = CoinWallet()
    wallet2.decode(data)

    assert wallet2.balance == 500
    assert wallet2.daily_earned == 750
    assert wallet2.daily_earn_cap == DEFAULT_DAILY_EARN_CAP


def test_encode_produces_dict(wallet: CoinWallet):
    wallet.earn(100)
    data = wallet.encode()
    assert isinstance(data, dict)
    assert "balance" in data
    assert "daily_earned" in data
    assert "daily_earn_cap" in data


def test_decode_empty_dict_gives_zero_state(wallet: CoinWallet):
    wallet.earn(500)
    wallet.decode({})
    assert wallet.balance == 0
    assert wallet.daily_earned == 0


def test_custom_cap_survives_round_trip():
    w = CoinWallet(daily_earn_cap=2000)
    w.earn(500)
    data = w.encode()

    w2 = CoinWallet()
    w2.decode(data)
    assert w2.daily_earn_cap == 2000

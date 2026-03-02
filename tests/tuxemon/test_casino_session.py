# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for CasinoSession — Phase 2.3 orchestrator.
"""
from __future__ import annotations

import random

import pytest

from tuxemon.casino.catalog import GameCatalog, GameDefinition, Outcome
from tuxemon.casino.session import (
    CasinoSession,
    GameNotFoundError,
    InsufficientFundsError,
    WagerOutOfRangeError,
)
from tuxemon.economy.coin_wallet import CoinWallet


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


def _deterministic_rng(wins: bool) -> random.Random:
    """Return a seeded RNG whose first sample is always a win or loss outcome."""
    rng = random.Random()
    rng.seed(0 if wins else 1)
    return rng


@pytest.fixture
def catalog() -> GameCatalog:
    cat = GameCatalog()
    cat.register(
        GameDefinition(
            slug="coin_flip",
            display_name="Coin Flip",
            min_wager=10,
            max_wager=200,
            outcomes=[
                Outcome("heads", probability=0.49, multiplier=2.0),
                Outcome("tails", probability=0.51, multiplier=0.0),
            ],
        )
    )
    return cat


@pytest.fixture
def wallet() -> CoinWallet:
    w = CoinWallet()
    w.earn(1000)
    return w


@pytest.fixture
def session(wallet, catalog) -> CasinoSession:
    return CasinoSession(
        player_id="alice",
        wallet=wallet,
        catalog=catalog,
        rng=random.Random(42),
    )


# ---------------------------------------------------------------------------
# play() — basic flow
# ---------------------------------------------------------------------------


class TestCasinoSessionPlay:
    def test_play_returns_round_result(self, session):
        result = session.play("coin_flip", wager=50)
        assert result.game_slug == "coin_flip"
        assert result.wager == 50

    def test_play_deducts_wager(self, wallet, session):
        initial = wallet.balance
        result = session.play("coin_flip", wager=50)
        # Balance = initial - wager + payout
        assert wallet.balance == initial - 50 + result.payout

    def test_play_result_has_currency_notice(self, session):
        result = session.play("coin_flip", wager=50)
        assert len(result.currency_notice) > 0
        assert "real money" in result.currency_notice.lower() or "in-game" in result.currency_notice.lower()

    def test_play_result_wallet_balance_matches(self, wallet, session):
        result = session.play("coin_flip", wager=50)
        assert result.wallet_balance == wallet.balance

    def test_play_result_net_is_payout_minus_wager(self, session):
        result = session.play("coin_flip", wager=50)
        assert result.net == result.payout - result.wager

    def test_play_unknown_game_raises(self, session):
        with pytest.raises(GameNotFoundError):
            session.play("ghost_game", wager=10)

    def test_play_wager_below_min_raises(self, session):
        with pytest.raises(WagerOutOfRangeError):
            session.play("coin_flip", wager=5)  # min_wager=10

    def test_play_wager_above_max_raises(self, session):
        with pytest.raises(WagerOutOfRangeError):
            session.play("coin_flip", wager=500)  # max_wager=200

    def test_play_insufficient_funds_raises(self, catalog):
        poor_wallet = CoinWallet()
        poor_wallet.earn(5)
        sess = CasinoSession(
            player_id="pauper", wallet=poor_wallet, catalog=catalog
        )
        with pytest.raises(InsufficientFundsError):
            sess.play("coin_flip", wager=10)

    def test_multiplier_outcome_in_result(self, session):
        result = session.play("coin_flip", wager=50)
        assert result.multiplier in {0.0, 2.0}

    def test_payout_is_floor_of_wager_times_multiplier(self, session):
        result = session.play("coin_flip", wager=50)
        expected = int(50 * result.multiplier)
        assert result.payout == expected


# ---------------------------------------------------------------------------
# Ledger accumulation
# ---------------------------------------------------------------------------


class TestCasinoSessionLedger:
    def test_ledger_none_before_play(self, session):
        assert session.ledger_for("coin_flip") is None

    def test_ledger_created_after_play(self, session):
        session.play("coin_flip", wager=10)
        assert session.ledger_for("coin_flip") is not None

    def test_ledger_accumulates_rounds(self, session):
        for _ in range(5):
            session.play("coin_flip", wager=10)
        assert session.ledger_for("coin_flip").round_count() == 5


# ---------------------------------------------------------------------------
# session_summary
# ---------------------------------------------------------------------------


class TestCasinoSessionSummary:
    def test_summary_has_player_id(self, session):
        s = session.session_summary()
        assert s["player_id"] == "alice"

    def test_summary_has_wallet_balance(self, wallet, session):
        session.play("coin_flip", wager=10)
        s = session.session_summary()
        assert s["wallet_balance"] == wallet.balance

    def test_summary_has_currency_notice(self, session):
        s = session.session_summary()
        assert "currency_notice" in s

    def test_summary_games_empty_before_play(self, session):
        s = session.session_summary()
        assert s["games"] == {}

    def test_summary_games_populated_after_play(self, session):
        session.play("coin_flip", wager=10)
        s = session.session_summary()
        assert "coin_flip" in s["games"]

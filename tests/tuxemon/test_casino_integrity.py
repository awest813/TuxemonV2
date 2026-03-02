# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for IntegrityLedger and ModerationController — Phase 2.3.
"""
from __future__ import annotations

import pytest

from tuxemon.casino.integrity import (
    IntegrityLedger,
    ModerationController,
    ModerationFlag,
    RoundRecord,
)


@pytest.fixture
def ledger() -> IntegrityLedger:
    return IntegrityLedger(player_id="alice", game_slug="coin_flip")


# ---------------------------------------------------------------------------
# IntegrityLedger — record_round
# ---------------------------------------------------------------------------


class TestIntegrityLedgerRecord:
    def test_record_win_round(self, ledger):
        r = ledger.record_round(wager=50, payout=100, win=True, outcome_label="heads")
        assert r.wager == 50
        assert r.payout == 100
        assert r.win is True
        assert r.outcome_label == "heads"

    def test_record_loss_round(self, ledger):
        r = ledger.record_round(wager=50, payout=0, win=False, outcome_label="tails")
        assert r.win is False
        assert r.net() == -50

    def test_sequence_increments(self, ledger):
        r1 = ledger.record_round(50, 0, False)
        r2 = ledger.record_round(50, 0, False)
        assert r1.sequence == 1
        assert r2.sequence == 2

    def test_invalid_wager_raises(self, ledger):
        with pytest.raises(ValueError):
            ledger.record_round(wager=0, payout=0, win=False)

    def test_negative_wager_raises(self, ledger):
        with pytest.raises(ValueError):
            ledger.record_round(wager=-10, payout=0, win=False)

    def test_negative_payout_raises(self, ledger):
        with pytest.raises(ValueError):
            ledger.record_round(wager=10, payout=-5, win=False)

    def test_round_count(self, ledger):
        for _ in range(5):
            ledger.record_round(10, 0, False)
        assert ledger.round_count() == 5

    def test_get_rounds_returns_copy(self, ledger):
        ledger.record_round(10, 0, False)
        rounds = ledger.get_rounds()
        rounds.clear()
        assert ledger.round_count() == 1


# ---------------------------------------------------------------------------
# IntegrityLedger — report()
# ---------------------------------------------------------------------------


class TestIntegrityLedgerReport:
    def test_empty_report(self, ledger):
        r = ledger.report()
        assert r.round_count == 0
        assert r.total_wagered == 0
        assert r.observed_win_rate == 0.0
        assert r.current_loss_streak == 0

    def test_report_totals(self, ledger):
        ledger.record_round(100, 200, True)
        ledger.record_round(50, 0, False)
        r = ledger.report()
        assert r.total_wagered == 150
        assert r.total_returned == 200
        assert r.net_coins == 50

    def test_win_rate_all_wins(self, ledger):
        for _ in range(4):
            ledger.record_round(10, 20, True)
        assert ledger.report().observed_win_rate == 1.0

    def test_win_rate_no_wins(self, ledger):
        for _ in range(4):
            ledger.record_round(10, 0, False)
        assert ledger.report().observed_win_rate == 0.0

    def test_win_rate_mixed(self, ledger):
        ledger.record_round(10, 20, True)
        ledger.record_round(10, 0, False)
        assert abs(ledger.report().observed_win_rate - 0.5) < 1e-9

    def test_loss_streak_resets_on_win(self, ledger):
        for _ in range(5):
            ledger.record_round(10, 0, False)
        ledger.record_round(10, 20, True)
        assert ledger.report().current_loss_streak == 0

    def test_loss_streak_accumulates(self, ledger):
        for _ in range(8):
            ledger.record_round(10, 0, False)
        assert ledger.report().current_loss_streak == 8


# ---------------------------------------------------------------------------
# IntegrityLedger — rounds_in_last_seconds
# ---------------------------------------------------------------------------


class TestRoundsInLastSeconds:
    def test_returns_zero_for_empty_ledger(self, ledger):
        assert ledger.rounds_in_last_seconds(60) == 0

    def test_counts_all_recent_rounds(self, ledger):
        for _ in range(10):
            ledger.record_round(10, 0, False)
        assert ledger.rounds_in_last_seconds(60) == 10


# ---------------------------------------------------------------------------
# ModerationController
# ---------------------------------------------------------------------------


class TestModerationController:
    def test_no_flags_for_normal_play(self, ledger):
        for i in range(10):
            win = i % 3 == 0
            ledger.record_round(50, 100 if win else 0, win)
        ctrl = ModerationController(ledger, expected_win_rate=0.33)
        assert ctrl.evaluate() == []

    def test_loss_streak_flag(self, ledger):
        for _ in range(20):
            ledger.record_round(50, 0, False)
        ctrl = ModerationController(ledger, max_loss_streak=15)
        flags = ctrl.evaluate()
        assert any(f.flag == ModerationFlag.LOSS_STREAK for f in flags)

    def test_no_loss_streak_flag_below_threshold(self, ledger):
        for _ in range(10):
            ledger.record_round(50, 0, False)
        ctrl = ModerationController(ledger, max_loss_streak=15)
        flags = ctrl.evaluate()
        assert not any(f.flag == ModerationFlag.LOSS_STREAK for f in flags)

    def test_win_rate_anomaly_needs_min_rounds(self, ledger):
        ledger.record_round(10, 20, True)
        ctrl = ModerationController(
            ledger, expected_win_rate=0.5, win_rate_deviation=0.10, min_rounds_for_stats=30
        )
        flags = ctrl.evaluate()
        assert not any(f.flag == ModerationFlag.WIN_RATE_ANOMALY for f in flags)

    def test_win_rate_anomaly_detected_with_enough_rounds(self, ledger):
        for _ in range(35):
            ledger.record_round(10, 0, False)
        ctrl = ModerationController(
            ledger,
            expected_win_rate=0.5,
            win_rate_deviation=0.10,
            min_rounds_for_stats=30,
        )
        flags = ctrl.evaluate()
        assert any(f.flag == ModerationFlag.WIN_RATE_ANOMALY for f in flags)

    def test_no_anomaly_when_expected_win_rate_is_none(self, ledger):
        for _ in range(50):
            ledger.record_round(10, 0, False)
        ctrl = ModerationController(ledger, expected_win_rate=None)
        flags = ctrl.evaluate()
        assert not any(f.flag == ModerationFlag.WIN_RATE_ANOMALY for f in flags)

    def test_rapid_play_flag(self, ledger):
        for _ in range(80):
            ledger.record_round(10, 0, False)
        ctrl = ModerationController(ledger, max_rounds_per_minute=60)
        flags = ctrl.evaluate()
        assert any(f.flag == ModerationFlag.RAPID_PLAY for f in flags)

    def test_flag_to_dict(self, ledger):
        for _ in range(20):
            ledger.record_round(10, 0, False)
        ctrl = ModerationController(ledger, max_loss_streak=15)
        flags = ctrl.evaluate()
        assert len(flags) > 0
        d = flags[0].to_dict()
        assert "flag" in d
        assert "detail" in d

# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Casino integrity telemetry and moderation controls — Phase 2.3.

**Currency policy:** All amounts tracked here are in-game coins only.
No real-money amounts, payment identifiers, or external currency references
are stored or transmitted.

The :class:`IntegrityLedger` records every casino round outcome for a
single player and exposes statistical analysis to detect abuse patterns:

* **Loss-streak detection** — flags when a player loses too many rounds in
  a row (possible RNG exploit testing or emotional distress signal).
* **Win-rate anomaly detection** — flags when a player's observed win rate
  deviates significantly from the game's expected value (possible
  exploit or statistical anomaly).
* **Rapid-play detection** — flags when a player plays more rounds per
  minute than the configured threshold (bot activity signal).

The :class:`ModerationController` wraps the ledger and exposes a simple
API for game sessions to check whether a player should be paused, warned,
or blocked.

Usage::

    ledger = IntegrityLedger(player_id="alice", game_slug="slot_basic")
    ledger.record_round(wager=50, payout=0, win=False)
    ledger.record_round(wager=50, payout=0, win=False)
    ...

    ctrl = ModerationController(ledger, max_loss_streak=10)
    flags = ctrl.evaluate()
    if flags:
        # send warning to player or pause session
        ...
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any

logger = logging.getLogger(__name__)

_DEFAULT_MAX_LOSS_STREAK = 15
_DEFAULT_WIN_RATE_DEVIATION_THRESHOLD = 0.30
_DEFAULT_MAX_ROUNDS_PER_MINUTE = 60


class ModerationFlag(Enum):
    """A signal raised by the moderation controller."""

    LOSS_STREAK = "loss_streak"
    WIN_RATE_ANOMALY = "win_rate_anomaly"
    RAPID_PLAY = "rapid_play"


@dataclass
class RoundRecord:
    """
    Immutable record of a single casino round outcome.

    Attributes:
        sequence:    Round number within this session (1-indexed).
        played_at:   Wall-clock timestamp of the round.
        wager:       Coins wagered (positive integer).
        payout:      Coins returned to the player (0 = full loss).
        win:         ``True`` if the player received any payout.
        outcome_label: The :attr:`~tuxemon.casino.catalog.Outcome.label` of
                       the result that occurred.
    """

    sequence: int
    played_at: datetime
    wager: int
    payout: int
    win: bool
    outcome_label: str = ""

    def net(self) -> int:
        """Signed coin change for this round (negative = loss)."""
        return self.payout - self.wager


@dataclass
class IntegrityReport:
    """
    Statistical summary produced by :class:`IntegrityLedger`.

    Attributes:
        round_count:       Total rounds played.
        total_wagered:     Total coins wagered.
        total_returned:    Total coins returned as payouts.
        observed_win_rate: Fraction of rounds the player won.
        current_loss_streak: Consecutive losing rounds at the end of the feed.
        net_coins:         ``total_returned - total_wagered``.
    """

    round_count: int
    total_wagered: int
    total_returned: int
    observed_win_rate: float
    current_loss_streak: int
    net_coins: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "round_count": self.round_count,
            "total_wagered": self.total_wagered,
            "total_returned": self.total_returned,
            "observed_win_rate": round(self.observed_win_rate, 6),
            "current_loss_streak": self.current_loss_streak,
            "net_coins": self.net_coins,
        }


class IntegrityLedger:
    """
    Append-only round log for a single player's casino session.

    Tracks every round played and computes running statistics used by
    :class:`ModerationController` to detect abuse signals.

    Parameters:
        player_id: Unique player identifier (for logging context).
        game_slug: Slug of the casino game being played.
    """

    def __init__(self, player_id: str, game_slug: str) -> None:
        self.player_id = player_id
        self.game_slug = game_slug
        self._rounds: list[RoundRecord] = []
        self._total_wagered: int = 0
        self._total_returned: int = 0
        self._win_count: int = 0
        self._current_loss_streak: int = 0

    def record_round(
        self,
        wager: int,
        payout: int,
        win: bool,
        outcome_label: str = "",
    ) -> RoundRecord:
        """
        Append a completed round to the ledger.

        Parameters:
            wager:         Coins wagered this round (must be > 0).
            payout:        Coins returned to the player (≥ 0).
            win:           Whether the player won any payout.
            outcome_label: Optional label from the game's outcome table.

        Returns:
            The created :class:`RoundRecord`.

        Raises:
            ValueError: If *wager* ≤ 0 or *payout* < 0.
        """
        if wager <= 0:
            raise ValueError(f"wager must be positive, got {wager}.")
        if payout < 0:
            raise ValueError(f"payout must be ≥ 0, got {payout}.")

        seq = len(self._rounds) + 1
        record = RoundRecord(
            sequence=seq,
            played_at=datetime.now(),
            wager=wager,
            payout=payout,
            win=win,
            outcome_label=outcome_label,
        )
        self._rounds.append(record)
        self._total_wagered += wager
        self._total_returned += payout

        if win:
            self._win_count += 1
            self._current_loss_streak = 0
        else:
            self._current_loss_streak += 1

        logger.debug(
            "IntegrityLedger [%s/%s] round %d: wager=%d payout=%d win=%s streak=%d",
            self.player_id,
            self.game_slug,
            seq,
            wager,
            payout,
            win,
            self._current_loss_streak,
        )
        return record

    def report(self) -> IntegrityReport:
        """Compute and return a :class:`IntegrityReport` from the current ledger."""
        n = len(self._rounds)
        win_rate = self._win_count / n if n > 0 else 0.0
        return IntegrityReport(
            round_count=n,
            total_wagered=self._total_wagered,
            total_returned=self._total_returned,
            observed_win_rate=win_rate,
            current_loss_streak=self._current_loss_streak,
            net_coins=self._total_returned - self._total_wagered,
        )

    def rounds_in_last_seconds(self, seconds: float) -> int:
        """Return the count of rounds played in the last *seconds* seconds."""
        if not self._rounds:
            return 0
        cutoff = self._rounds[-1].played_at.timestamp() - seconds
        return sum(
            1 for r in self._rounds if r.played_at.timestamp() >= cutoff
        )

    def round_count(self) -> int:
        """Return the total number of rounds recorded."""
        return len(self._rounds)

    def get_rounds(self) -> list[RoundRecord]:
        """Return a copy of all recorded rounds."""
        return list(self._rounds)


@dataclass
class ModerationFlag_Result:
    """A raised flag with contextual details."""

    flag: ModerationFlag
    detail: str

    def to_dict(self) -> dict[str, Any]:
        return {"flag": self.flag.value, "detail": self.detail}


class ModerationController:
    """
    Evaluates an :class:`IntegrityLedger` against configurable thresholds
    and returns a list of :class:`ModerationFlag_Result` objects describing
    any signals detected.

    Parameters:
        ledger:                  The ledger to evaluate.
        max_loss_streak:         Flag ``LOSS_STREAK`` when the current losing
            streak reaches this length (default 15).
        win_rate_deviation:      Flag ``WIN_RATE_ANOMALY`` when the absolute
            difference between the player's observed win rate and
            *expected_win_rate* exceeds this fraction (default 0.30).
        expected_win_rate:       The game's theoretical win rate (e.g. 0.15 for
            a 15% win probability).  If ``None``, anomaly detection is skipped.
        max_rounds_per_minute:   Flag ``RAPID_PLAY`` when the player completes
            more than this many rounds per minute (default 60).
        min_rounds_for_stats:    Minimum rounds before statistical flags are
            evaluated (default 30, avoids false positives in small samples).
    """

    def __init__(
        self,
        ledger: IntegrityLedger,
        max_loss_streak: int = _DEFAULT_MAX_LOSS_STREAK,
        win_rate_deviation: float = _DEFAULT_WIN_RATE_DEVIATION_THRESHOLD,
        expected_win_rate: float | None = None,
        max_rounds_per_minute: int = _DEFAULT_MAX_ROUNDS_PER_MINUTE,
        min_rounds_for_stats: int = 30,
    ) -> None:
        self._ledger = ledger
        self._max_loss_streak = max_loss_streak
        self._win_rate_deviation = win_rate_deviation
        self._expected_win_rate = expected_win_rate
        self._max_rounds_per_minute = max_rounds_per_minute
        self._min_rounds_for_stats = min_rounds_for_stats

    def evaluate(self) -> list[ModerationFlag_Result]:
        """
        Run all enabled checks and return any raised flags.

        Returns:
            List of :class:`ModerationFlag_Result` (empty if no signals).
        """
        flags: list[ModerationFlag_Result] = []
        report = self._ledger.report()

        # 1. Loss streak check.
        if report.current_loss_streak >= self._max_loss_streak:
            flags.append(
                ModerationFlag_Result(
                    flag=ModerationFlag.LOSS_STREAK,
                    detail=(
                        f"Player {self._ledger.player_id!r} has lost "
                        f"{report.current_loss_streak} rounds in a row "
                        f"(threshold: {self._max_loss_streak})."
                    ),
                )
            )

        # 2. Win-rate anomaly check (only with sufficient data).
        if (
            self._expected_win_rate is not None
            and report.round_count >= self._min_rounds_for_stats
        ):
            deviation = abs(report.observed_win_rate - self._expected_win_rate)
            if deviation > self._win_rate_deviation:
                flags.append(
                    ModerationFlag_Result(
                        flag=ModerationFlag.WIN_RATE_ANOMALY,
                        detail=(
                            f"Player {self._ledger.player_id!r} win rate "
                            f"{report.observed_win_rate:.4f} deviates from "
                            f"expected {self._expected_win_rate:.4f} by "
                            f"{deviation:.4f} (threshold: {self._win_rate_deviation})."
                        ),
                    )
                )

        # 3. Rapid-play check (rounds in the last 60 seconds).
        recent = self._ledger.rounds_in_last_seconds(60.0)
        if recent > self._max_rounds_per_minute:
            flags.append(
                ModerationFlag_Result(
                    flag=ModerationFlag.RAPID_PLAY,
                    detail=(
                        f"Player {self._ledger.player_id!r} played {recent} rounds "
                        f"in the last minute (threshold: {self._max_rounds_per_minute})."
                    ),
                )
            )

        if flags:
            logger.warning(
                "ModerationController: %d flag(s) for player %r game %r: %s",
                len(flags),
                self._ledger.player_id,
                self._ledger.game_slug,
                [f.flag.value for f in flags],
            )

        return flags

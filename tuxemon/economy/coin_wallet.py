# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
In-game coin wallet for the casino and battle-center economy.

**Currency policy:** All coins are earned exclusively through gameplay.
There is no mechanism to purchase, sell, or convert in-game coins using
real money or any external currency.  This constraint is enforced at the
data-model level: ``CoinWallet`` has no concept of payment, purchase, or
external currency conversion.  Any contribution that introduces such a path
will be rejected.

Usage::

    wallet = CoinWallet(daily_earn_cap=9_999)

    # Player earns coins from a battle:
    earned = wallet.earn(500)          # returns actual amount (≤ cap)

    # Player spends coins at the casino:
    wallet.spend(200)

    # Day rollover — reset the daily earn counter:
    wallet.reset_daily()

    # Save / restore:
    data = wallet.encode()
    wallet2 = CoinWallet()
    wallet2.decode(data)
"""

from __future__ import annotations

import logging
from typing import Any

logger = logging.getLogger(__name__)

DEFAULT_DAILY_EARN_CAP: int = 9_999


class InsufficientCoinsError(Exception):
    """Raised when a spend request exceeds the current wallet balance."""


class DailyCapReachedError(Exception):
    """Raised (informally) when earn() is called but the daily cap is already hit."""


class CoinWallet:
    """
    In-game coin wallet with a daily earn cap and no real-money pathway.

    Attributes:
        DEFAULT_DAILY_EARN_CAP: Default maximum coins earnable per calendar
            day (9,999).  Configurable per-wallet; overridden by server/host
            settings in Phase 2.

    Design invariants:
        * ``balance`` never goes negative.
        * ``daily_earned`` never exceeds ``daily_earn_cap``.
        * There is no method to set the balance directly — coins arrive only
          through :meth:`earn` and leave only through :meth:`spend`.
    """

    DEFAULT_DAILY_EARN_CAP: int = DEFAULT_DAILY_EARN_CAP

    def __init__(self, daily_earn_cap: int = DEFAULT_DAILY_EARN_CAP) -> None:
        if daily_earn_cap <= 0:
            raise ValueError(
                f"daily_earn_cap must be positive, got {daily_earn_cap}"
            )
        self._balance: int = 0
        self._daily_earned: int = 0
        self._daily_earn_cap: int = daily_earn_cap

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def balance(self) -> int:
        """Current coin balance."""
        return self._balance

    @property
    def daily_earned(self) -> int:
        """Coins earned today (resets at day rollover)."""
        return self._daily_earned

    @property
    def daily_earn_cap(self) -> int:
        """Maximum coins earnable per calendar day."""
        return self._daily_earn_cap

    @property
    def daily_earn_remaining(self) -> int:
        """Coins still earnable today before the cap is hit."""
        return max(0, self._daily_earn_cap - self._daily_earned)

    # ------------------------------------------------------------------
    # Mutations
    # ------------------------------------------------------------------

    def earn(self, amount: int) -> int:
        """
        Credit *amount* coins to the wallet, honouring the daily earn cap.

        If the full *amount* would exceed today's cap, only the remaining
        allowance is credited.  The actual amount credited is returned.

        Parameters:
            amount: Positive integer number of coins to earn.

        Returns:
            The actual number of coins added (may be less than *amount*).

        Raises:
            ValueError: If *amount* is not a positive integer.
        """
        if amount <= 0:
            raise ValueError(f"earn amount must be positive, got {amount}")

        remaining_cap = self._daily_earn_cap - self._daily_earned
        actual = min(amount, remaining_cap)

        if actual == 0:
            logger.debug(
                "CoinWallet: daily earn cap (%d) reached; earn of %d ignored",
                self._daily_earn_cap,
                amount,
            )
        else:
            self._balance += actual
            self._daily_earned += actual
            logger.debug(
                "CoinWallet: earned %d coins (requested %d); balance=%d",
                actual,
                amount,
                self._balance,
            )
        return actual

    def spend(self, amount: int) -> None:
        """
        Debit *amount* coins from the wallet.

        Parameters:
            amount: Positive integer number of coins to spend.

        Raises:
            ValueError: If *amount* is not a positive integer.
            InsufficientCoinsError: If *amount* exceeds the current balance.
        """
        if amount <= 0:
            raise ValueError(f"spend amount must be positive, got {amount}")
        if amount > self._balance:
            raise InsufficientCoinsError(
                f"Cannot spend {amount} coins; current balance is {self._balance}"
            )
        self._balance -= amount
        logger.debug(
            "CoinWallet: spent %d coins; balance=%d", amount, self._balance
        )

    def reset_daily(self) -> None:
        """
        Reset the daily earned counter.

        Must be called at each day rollover (Hook 4.2 — ``on_day_change``).
        The balance is unaffected; only the daily tracking is reset.
        """
        self._daily_earned = 0
        logger.debug("CoinWallet: daily earn counter reset")

    # ------------------------------------------------------------------
    # Save / load
    # ------------------------------------------------------------------

    def encode(self) -> dict[str, Any]:
        """Serialise the wallet for inclusion in the player's save file."""
        return {
            "balance": self._balance,
            "daily_earned": self._daily_earned,
            "daily_earn_cap": self._daily_earn_cap,
        }

    def decode(self, data: dict[str, Any]) -> None:
        """Restore wallet state from a previously encoded dict."""
        self._balance = int(data.get("balance", 0))
        self._daily_earned = int(data.get("daily_earned", 0))
        self._daily_earn_cap = int(
            data.get("daily_earn_cap", self.DEFAULT_DAILY_EARN_CAP)
        )

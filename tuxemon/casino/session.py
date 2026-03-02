# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Casino session orchestrator — Phase 2.3.

**Currency policy:** This module uses :class:`~tuxemon.economy.coin_wallet.CoinWallet`
exclusively.  All amounts are in-game coins earned through gameplay.  There
is no payment, purchase, or conversion pathway to real money anywhere in
this module.

:class:`CasinoSession` is the single entry point for playing a casino
mini-game round.  It:

1. Validates the player's wager against the game's ``[min_wager, max_wager]``
   range.
2. Draws the coins from the player's :class:`~tuxemon.economy.coin_wallet.CoinWallet`.
3. Samples an :class:`~tuxemon.casino.catalog.Outcome` using its probability
   distribution.
4. Computes the payout and credits it back to the wallet.
5. Records the round in the :class:`~tuxemon.casino.integrity.IntegrityLedger`.
6. Returns a :class:`RoundResult` describing the outcome.

UI messaging
~~~~~~~~~~~~
Every :class:`RoundResult` carries a ``currency_notice`` string that must be
displayed on the result screen.  This implements the ROADMAP requirement for
"explicit UI messaging on every casino screen confirming in-game-only currency
use."

Usage::

    from tuxemon.economy.coin_wallet import CoinWallet
    from tuxemon.casino.catalog import GameCatalog, GameDefinition, Outcome
    from tuxemon.casino.session import CasinoSession

    wallet = CoinWallet()
    wallet.earn(1000)

    game = GameDefinition(
        slug="coin_flip",
        display_name="Coin Flip",
        min_wager=10,
        max_wager=200,
        outcomes=[
            Outcome("heads", probability=0.49, multiplier=2.0),
            Outcome("tails", probability=0.51, multiplier=0.0),
        ],
    )
    catalog = GameCatalog()
    catalog.register(game)

    session = CasinoSession(player_id="alice", wallet=wallet, catalog=catalog)
    result = session.play("coin_flip", wager=50)
    print(result.outcome_label, result.payout, result.net)
"""
from __future__ import annotations

import logging
import random
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from tuxemon.casino.integrity import IntegrityLedger, ModerationController

if TYPE_CHECKING:
    from tuxemon.casino.catalog import GameCatalog, GameDefinition, Outcome
    from tuxemon.economy.coin_wallet import CoinWallet

logger = logging.getLogger(__name__)

_CURRENCY_NOTICE = (
    "All coins used here are earned through gameplay. "
    "No real money is involved."
)


@dataclass(frozen=True)
class RoundResult:
    """
    The result of a single casino round.

    Attributes:
        game_slug:       Slug of the game played.
        wager:           Coins wagered.
        outcome_label:   Label of the outcome that occurred.
        multiplier:      Multiplier applied to the wager.
        payout:          Coins returned (``floor(wager * multiplier)``).
        net:             Signed coin change (``payout - wager``).
        wallet_balance:  Player's coin balance *after* this round.
        currency_notice: Fixed disclaimer confirming in-game-only currency.
        moderation_flags: List of moderation flag dicts (empty if clean).
    """

    game_slug: str
    wager: int
    outcome_label: str
    multiplier: float
    payout: int
    net: int
    wallet_balance: int
    currency_notice: str
    moderation_flags: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "game_slug": self.game_slug,
            "wager": self.wager,
            "outcome_label": self.outcome_label,
            "multiplier": self.multiplier,
            "payout": self.payout,
            "net": self.net,
            "wallet_balance": self.wallet_balance,
            "currency_notice": self.currency_notice,
            "moderation_flags": list(self.moderation_flags),
        }


class SessionError(Exception):
    """Base exception for casino session errors."""


class GameNotFoundError(SessionError):
    """Raised when a slug does not match any registered game."""


class WagerOutOfRangeError(SessionError):
    """Raised when the requested wager is outside ``[min_wager, max_wager]``."""


class InsufficientFundsError(SessionError):
    """Raised when the player's wallet cannot cover the wager."""


def _sample_outcome(game: "GameDefinition", rng: random.Random) -> "Outcome":
    """
    Sample one outcome from *game*'s outcome table using its probability weights.

    Uses :func:`random.Random.choices` for a single weighted draw.
    """
    outcomes = game.outcomes
    weights = [o.probability for o in outcomes]
    return rng.choices(outcomes, weights=weights, k=1)[0]


class CasinoSession:
    """
    Orchestrates casino mini-game rounds for a single player.

    Parameters:
        player_id: Unique identifier for the playing player.
        wallet:    :class:`~tuxemon.economy.coin_wallet.CoinWallet` used for
                   wager/payout transactions.
        catalog:   :class:`~tuxemon.casino.catalog.GameCatalog` to look up
                   game definitions.
        rng:       Optional :class:`random.Random` instance for reproducible
                   tests.  Defaults to the module-level RNG.
        moderation_config: Optional dict of kwargs forwarded to
            :class:`~tuxemon.casino.integrity.ModerationController`.
    """

    def __init__(
        self,
        player_id: str,
        wallet: "CoinWallet",
        catalog: "GameCatalog",
        rng: random.Random | None = None,
        moderation_config: dict[str, Any] | None = None,
    ) -> None:
        self._player_id = player_id
        self._wallet = wallet
        self._catalog = catalog
        self._rng = rng or random.Random()
        self._moderation_config: dict[str, Any] = moderation_config or {}
        self._ledgers: dict[str, IntegrityLedger] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def play(self, game_slug: str, wager: int) -> RoundResult:
        """
        Play one round of *game_slug* by wagering *wager* coins.

        The method:

        1. Looks up the game definition.
        2. Validates that *wager* is within the game's allowed range.
        3. Deducts *wager* from the wallet (raises if insufficient).
        4. Samples an outcome and computes the payout.
        5. Credits the payout to the wallet.
        6. Records the round in the integrity ledger and runs moderation checks.
        7. Returns a :class:`RoundResult`.

        Parameters:
            game_slug: Slug of the game to play.
            wager:     Number of coins to wager (must be in
                       ``[game.min_wager, game.max_wager]``).

        Returns:
            A :class:`RoundResult` describing the round.

        Raises:
            GameNotFoundError: If *game_slug* is not in the catalog.
            WagerOutOfRangeError: If *wager* is outside the game's limits.
            InsufficientFundsError: If the wallet balance < *wager*.
        """
        game = self._catalog.get(game_slug)
        if game is None:
            raise GameNotFoundError(
                f"No casino game with slug {game_slug!r} is registered."
            )

        if wager < game.min_wager or wager > game.max_wager:
            raise WagerOutOfRangeError(
                f"Wager {wager} is outside [{game.min_wager}, {game.max_wager}] "
                f"for game {game_slug!r}."
            )

        from tuxemon.economy.coin_wallet import InsufficientCoinsError

        try:
            self._wallet.spend(wager)
        except InsufficientCoinsError as exc:
            raise InsufficientFundsError(
                f"Player {self._player_id!r} cannot afford wager {wager} "
                f"(balance: {self._wallet.balance})."
            ) from exc

        outcome = _sample_outcome(game, self._rng)
        payout = int(wager * outcome.multiplier)
        if payout > 0:
            self._wallet.earn(payout)

        net = payout - wager

        ledger = self._get_ledger(game_slug)
        ledger.record_round(
            wager=wager,
            payout=payout,
            win=outcome.multiplier > 0.0,
            outcome_label=outcome.label,
        )

        flags = self._run_moderation(game_slug, ledger, game)

        logger.info(
            "CasinoSession [%s/%s] round %d: wager=%d outcome=%r payout=%d net=%+d balance=%d",
            self._player_id,
            game_slug,
            ledger.round_count(),
            wager,
            outcome.label,
            payout,
            net,
            self._wallet.balance,
        )

        return RoundResult(
            game_slug=game_slug,
            wager=wager,
            outcome_label=outcome.label,
            multiplier=outcome.multiplier,
            payout=payout,
            net=net,
            wallet_balance=self._wallet.balance,
            currency_notice=_CURRENCY_NOTICE,
            moderation_flags=tuple(f.to_dict() for f in flags),
        )

    def ledger_for(self, game_slug: str) -> IntegrityLedger | None:
        """Return the integrity ledger for *game_slug*, or ``None`` if not played yet."""
        return self._ledgers.get(game_slug)

    def session_summary(self) -> dict[str, Any]:
        """Return a summary dict of all games played this session."""
        return {
            "player_id": self._player_id,
            "wallet_balance": self._wallet.balance,
            "games": {
                slug: ledger.report().to_dict()
                for slug, ledger in self._ledgers.items()
            },
            "currency_notice": _CURRENCY_NOTICE,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _get_ledger(self, game_slug: str) -> IntegrityLedger:
        if game_slug not in self._ledgers:
            self._ledgers[game_slug] = IntegrityLedger(
                player_id=self._player_id, game_slug=game_slug
            )
        return self._ledgers[game_slug]

    def _run_moderation(
        self,
        game_slug: str,
        ledger: IntegrityLedger,
        game: "GameDefinition",
    ) -> list:
        expected_win_rate = sum(
            o.probability for o in game.outcomes if o.multiplier > 0.0
        )
        ctrl = ModerationController(
            ledger=ledger,
            expected_win_rate=expected_win_rate,
            **self._moderation_config,
        )
        return ctrl.evaluate()

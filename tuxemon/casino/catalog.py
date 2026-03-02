# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Online Casino game catalog with fairness audits — Phase 2.3.

**Currency policy:** All casino wagers and payouts are denominated exclusively
in in-game coins earned through gameplay.  There is no real-money pathway at
any layer of this module.  Any contribution that introduces a real-money flow
will be rejected.

This module defines:

* :class:`GameDefinition` — a validated description of a single casino game
  including its payout table and expected-value (EV) guardrail.
* :class:`FairnessAudit` — a computed summary of a game's expected value,
  house edge, and variance, used to enforce designer-set EV limits.
* :class:`GameCatalog` — the registry that holds all available games and
  enforces catalog-level constraints (e.g. no game may offer a positive EV
  to the player).

Expected-value guardrails
~~~~~~~~~~~~~~~~~~~~~~~~~
Every :class:`GameDefinition` must pass a *fairness audit* before it can be
added to the catalog.  The audit checks:

1. **Player EV ≤ 0** — the game must not give the player a statistical
   advantage over the house (to avoid an infinite-money exploit).
2. **House edge ≤ configured maximum** — the game must not be exploitatively
   unfair to the player.
3. **All outcome probabilities sum to 1.0** (within floating-point tolerance).

Usage::

    from tuxemon.casino.catalog import GameCatalog, GameDefinition, Outcome

    slots = GameDefinition(
        slug="slot_basic",
        display_name="Basic Slots",
        min_wager=10,
        max_wager=500,
        outcomes=[
            Outcome(label="jackpot",    probability=0.01,  multiplier=50.0),
            Outcome(label="triple",     probability=0.05,  multiplier=5.0),
            Outcome(label="double",     probability=0.10,  multiplier=2.0),
            Outcome(label="no_win",     probability=0.84,  multiplier=0.0),
        ],
    )
    catalog = GameCatalog()
    catalog.register(slots)
    game = catalog.get("slot_basic")
"""
from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

_PROBABILITY_TOLERANCE = 1e-6
_DEFAULT_MAX_HOUSE_EDGE = 0.30  # house keeps at most 30 % on average


@dataclass(frozen=True)
class Outcome:
    """
    A single possible result of a casino game round.

    Attributes:
        label:       Human-readable name for this outcome (e.g. ``"jackpot"``).
        probability: Probability of this outcome occurring in [0, 1].
        multiplier:  Wager multiplier applied to the player's bet.
                     A value of ``0.0`` means the player loses their wager;
                     ``1.0`` returns the wager (push); ``2.0`` doubles it.
    """

    label: str
    probability: float
    multiplier: float

    def __post_init__(self) -> None:
        if not (0.0 <= self.probability <= 1.0):
            raise ValueError(
                f"Outcome {self.label!r}: probability {self.probability} is not in [0, 1]."
            )
        if self.multiplier < 0.0:
            raise ValueError(
                f"Outcome {self.label!r}: multiplier {self.multiplier} must be ≥ 0."
            )

    @property
    def player_ev_contribution(self) -> float:
        """Contribution of this outcome to player expected value (per unit wagered)."""
        return self.probability * self.multiplier


@dataclass(frozen=True)
class FairnessAudit:
    """
    Computed fairness metrics for a :class:`GameDefinition`.

    Attributes:
        player_ev:   Expected return to the player per unit wagered (e.g.
                     ``0.85`` means the player gets back 85 cents per coin bet).
        house_edge:  ``1 - player_ev``; fraction kept by the house.
        variance:    Variance of the return per unit wagered (higher = more
                     volatile swings).
        passes:      ``True`` if the game satisfies all configured guardrails.
        failure_reasons: List of human-readable strings explaining any failures.
    """

    player_ev: float
    house_edge: float
    variance: float
    passes: bool
    failure_reasons: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "player_ev": round(self.player_ev, 6),
            "house_edge": round(self.house_edge, 6),
            "variance": round(self.variance, 6),
            "passes": self.passes,
            "failure_reasons": list(self.failure_reasons),
        }


def _compute_audit(
    outcomes: list[Outcome],
    max_house_edge: float,
) -> FairnessAudit:
    """Compute a :class:`FairnessAudit` for the given outcome table."""
    failures: list[str] = []

    total_prob = sum(o.probability for o in outcomes)
    if abs(total_prob - 1.0) > _PROBABILITY_TOLERANCE:
        failures.append(
            f"Outcome probabilities sum to {total_prob:.8f}, expected 1.0."
        )

    player_ev = sum(o.player_ev_contribution for o in outcomes)

    # Variance: E[X²] - (E[X])²
    e_x2 = sum(o.probability * (o.multiplier ** 2) for o in outcomes)
    variance = e_x2 - player_ev ** 2

    house_edge = 1.0 - player_ev

    if player_ev > 1.0 + _PROBABILITY_TOLERANCE:
        failures.append(
            f"Player EV {player_ev:.4f} exceeds 1.0; game is player-positive (exploit risk)."
        )
    if house_edge > max_house_edge + _PROBABILITY_TOLERANCE:
        failures.append(
            f"House edge {house_edge:.4f} exceeds configured maximum {max_house_edge:.4f}."
        )

    return FairnessAudit(
        player_ev=player_ev,
        house_edge=house_edge,
        variance=variance,
        passes=len(failures) == 0,
        failure_reasons=failures,
    )


@dataclass
class GameDefinition:
    """
    A validated description of a single casino mini-game.

    The game's :attr:`outcomes` table describes every possible result of a
    single round together with its probability and payout multiplier.  On
    construction the table is verified to sum to 1.0 and each entry is
    range-checked.

    Parameters:
        slug:         Unique machine-readable identifier (e.g. ``"slot_basic"``).
        display_name: Localisation-ready player-facing name.
        min_wager:    Minimum coin bet per round (must be ≥ 1).
        max_wager:    Maximum coin bet per round (must be ≥ min_wager).
        outcomes:     Non-empty list of :class:`Outcome` objects whose
                      probabilities sum to 1.0.
        description:  Optional flavour text for the game browser.
        max_house_edge: Override the default maximum house edge for this game
            (default 0.30).
    """

    slug: str
    display_name: str
    min_wager: int
    max_wager: int
    outcomes: list[Outcome]
    description: str = ""
    max_house_edge: float = _DEFAULT_MAX_HOUSE_EDGE
    _audit: FairnessAudit = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if not self.slug:
            raise ValueError("slug must not be empty.")
        if self.min_wager < 1:
            raise ValueError(
                f"min_wager must be ≥ 1, got {self.min_wager}."
            )
        if self.max_wager < self.min_wager:
            raise ValueError(
                f"max_wager ({self.max_wager}) must be ≥ min_wager ({self.min_wager})."
            )
        if not self.outcomes:
            raise ValueError("outcomes list must not be empty.")
        self._audit = _compute_audit(self.outcomes, self.max_house_edge)

    @property
    def audit(self) -> FairnessAudit:
        """Pre-computed :class:`FairnessAudit` for this game."""
        return self._audit

    def clamp_wager(self, wager: int) -> int:
        """Return *wager* clamped to ``[min_wager, max_wager]``."""
        return max(self.min_wager, min(self.max_wager, wager))

    def to_dict(self) -> dict[str, Any]:
        return {
            "slug": self.slug,
            "display_name": self.display_name,
            "min_wager": self.min_wager,
            "max_wager": self.max_wager,
            "description": self.description,
            "audit": self._audit.to_dict(),
            "outcomes": [
                {
                    "label": o.label,
                    "probability": o.probability,
                    "multiplier": o.multiplier,
                }
                for o in self.outcomes
            ],
        }


class CatalogError(Exception):
    """Base exception for game catalog violations."""


class DuplicateGameError(CatalogError):
    """Raised when registering a game slug that already exists in the catalog."""


class FairnessGuardrailError(CatalogError):
    """
    Raised when a :class:`GameDefinition` fails its fairness audit and cannot
    be added to the catalog.
    """

    def __init__(self, slug: str, audit: FairnessAudit) -> None:
        reasons = "; ".join(audit.failure_reasons)
        super().__init__(
            f"Game {slug!r} failed fairness audit: {reasons}"
        )
        self.slug = slug
        self.audit = audit


class GameCatalog:
    """
    Registry of all available casino mini-games.

    Only games that pass the fairness audit (probability sum == 1.0, player
    EV ≤ 1.0, house edge ≤ configured max) may be registered.

    The catalog exposes a read-only view of all registered games and is the
    single source of truth for the casino mini-game selection screen.

    Parameters:
        enforce_fairness: If ``True`` (default), :meth:`register` raises
            :class:`FairnessGuardrailError` when the audit fails.  Set to
            ``False`` only in test environments that need to exercise invalid
            game definitions.
    """

    def __init__(self, enforce_fairness: bool = True) -> None:
        self._games: dict[str, GameDefinition] = {}
        self._enforce_fairness = enforce_fairness

    def register(self, game: GameDefinition) -> None:
        """
        Add *game* to the catalog.

        Parameters:
            game: The :class:`GameDefinition` to register.

        Raises:
            DuplicateGameError: If a game with the same slug already exists.
            FairnessGuardrailError: If the game fails its audit and
                ``enforce_fairness`` is ``True``.
        """
        if game.slug in self._games:
            raise DuplicateGameError(
                f"A game with slug {game.slug!r} is already registered."
            )
        if self._enforce_fairness and not game.audit.passes:
            raise FairnessGuardrailError(game.slug, game.audit)
        self._games[game.slug] = game
        logger.info(
            "Casino catalog: registered %r (EV=%.4f, house_edge=%.4f)",
            game.slug,
            game.audit.player_ev,
            game.audit.house_edge,
        )

    def get(self, slug: str) -> GameDefinition | None:
        """Return the game with *slug*, or ``None`` if not found."""
        return self._games.get(slug)

    def all_games(self) -> list[GameDefinition]:
        """Return all registered games in registration order."""
        return list(self._games.values())

    def game_count(self) -> int:
        """Return the number of registered games."""
        return len(self._games)

    def to_dict(self) -> list[dict[str, Any]]:
        """Serialise the full catalog for UI consumption."""
        return [g.to_dict() for g in self._games.values()]

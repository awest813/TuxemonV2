# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for the casino game catalog and fairness audit — Phase 2.3.
"""
from __future__ import annotations

import pytest

from tuxemon.casino.catalog import (
    CatalogError,
    DuplicateGameError,
    FairnessGuardrailError,
    GameCatalog,
    GameDefinition,
    Outcome,
    _compute_audit,
)


# ---------------------------------------------------------------------------
# Outcome
# ---------------------------------------------------------------------------


class TestOutcome:
    def test_valid_outcome(self):
        o = Outcome("win", probability=0.5, multiplier=2.0)
        assert o.probability == 0.5
        assert o.multiplier == 2.0

    def test_probability_below_zero_raises(self):
        with pytest.raises(ValueError):
            Outcome("x", probability=-0.1, multiplier=1.0)

    def test_probability_above_one_raises(self):
        with pytest.raises(ValueError):
            Outcome("x", probability=1.1, multiplier=1.0)

    def test_negative_multiplier_raises(self):
        with pytest.raises(ValueError):
            Outcome("x", probability=0.5, multiplier=-1.0)

    def test_ev_contribution(self):
        o = Outcome("win", probability=0.5, multiplier=2.0)
        assert abs(o.player_ev_contribution - 1.0) < 1e-9


# ---------------------------------------------------------------------------
# FairnessAudit helpers
# ---------------------------------------------------------------------------


def _coin_flip_outcomes() -> list[Outcome]:
    return [
        Outcome("win", probability=0.49, multiplier=2.0),
        Outcome("loss", probability=0.51, multiplier=0.0),
    ]


def _slot_outcomes() -> list[Outcome]:
    return [
        Outcome("jackpot", probability=0.01, multiplier=50.0),
        Outcome("triple",  probability=0.05, multiplier=5.0),
        Outcome("double",  probability=0.10, multiplier=2.0),
        Outcome("no_win",  probability=0.84, multiplier=0.0),
    ]


class TestFairnessAudit:
    def test_valid_game_passes_audit(self):
        audit = _compute_audit(_coin_flip_outcomes(), max_house_edge=0.30)
        assert audit.passes is True
        assert audit.failure_reasons == []

    def test_player_ev_computed_correctly(self):
        audit = _compute_audit(_coin_flip_outcomes(), max_house_edge=0.30)
        expected_ev = 0.49 * 2.0 + 0.51 * 0.0
        assert abs(audit.player_ev - expected_ev) < 1e-9

    def test_house_edge_is_complement_of_ev(self):
        audit = _compute_audit(_coin_flip_outcomes(), max_house_edge=0.30)
        assert abs(audit.house_edge - (1.0 - audit.player_ev)) < 1e-9

    def test_variance_computed(self):
        audit = _compute_audit(_coin_flip_outcomes(), max_house_edge=0.30)
        assert audit.variance >= 0.0

    def test_player_positive_ev_fails(self):
        outcomes = [
            Outcome("win", probability=0.6, multiplier=2.0),
            Outcome("loss", probability=0.4, multiplier=0.0),
        ]
        audit = _compute_audit(outcomes, max_house_edge=0.30)
        assert audit.passes is False
        assert any("EV" in r for r in audit.failure_reasons)

    def test_house_edge_too_large_fails(self):
        outcomes = [
            Outcome("win", probability=0.1, multiplier=2.0),
            Outcome("loss", probability=0.9, multiplier=0.0),
        ]
        audit = _compute_audit(outcomes, max_house_edge=0.10)
        assert audit.passes is False
        assert any("house edge" in r.lower() for r in audit.failure_reasons)

    def test_probabilities_not_summing_to_one_fails(self):
        outcomes = [
            Outcome("win", probability=0.3, multiplier=2.0),
            Outcome("loss", probability=0.3, multiplier=0.0),
        ]
        audit = _compute_audit(outcomes, max_house_edge=0.30)
        assert audit.passes is False

    def test_slot_machine_audit_passes(self):
        audit = _compute_audit(_slot_outcomes(), max_house_edge=0.50)
        assert audit.passes is True

    def test_to_dict_has_expected_keys(self):
        audit = _compute_audit(_coin_flip_outcomes(), max_house_edge=0.30)
        d = audit.to_dict()
        assert "player_ev" in d
        assert "house_edge" in d
        assert "variance" in d
        assert "passes" in d
        assert "failure_reasons" in d


# ---------------------------------------------------------------------------
# GameDefinition
# ---------------------------------------------------------------------------


class TestGameDefinition:
    def test_valid_game_definition(self):
        game = GameDefinition(
            slug="coin_flip",
            display_name="Coin Flip",
            min_wager=10,
            max_wager=200,
            outcomes=_coin_flip_outcomes(),
        )
        assert game.slug == "coin_flip"
        assert game.audit.passes is True

    def test_empty_slug_raises(self):
        with pytest.raises(ValueError):
            GameDefinition(
                slug="",
                display_name="X",
                min_wager=10,
                max_wager=100,
                outcomes=_coin_flip_outcomes(),
            )

    def test_min_wager_zero_raises(self):
        with pytest.raises(ValueError):
            GameDefinition(
                slug="x",
                display_name="X",
                min_wager=0,
                max_wager=100,
                outcomes=_coin_flip_outcomes(),
            )

    def test_max_wager_below_min_raises(self):
        with pytest.raises(ValueError):
            GameDefinition(
                slug="x",
                display_name="X",
                min_wager=100,
                max_wager=50,
                outcomes=_coin_flip_outcomes(),
            )

    def test_empty_outcomes_raises(self):
        with pytest.raises(ValueError):
            GameDefinition(
                slug="x",
                display_name="X",
                min_wager=10,
                max_wager=100,
                outcomes=[],
            )

    def test_clamp_wager_below_min(self):
        game = GameDefinition(
            slug="x", display_name="X", min_wager=10, max_wager=100,
            outcomes=_coin_flip_outcomes(),
        )
        assert game.clamp_wager(5) == 10

    def test_clamp_wager_above_max(self):
        game = GameDefinition(
            slug="x", display_name="X", min_wager=10, max_wager=100,
            outcomes=_coin_flip_outcomes(),
        )
        assert game.clamp_wager(200) == 100

    def test_clamp_wager_in_range(self):
        game = GameDefinition(
            slug="x", display_name="X", min_wager=10, max_wager=100,
            outcomes=_coin_flip_outcomes(),
        )
        assert game.clamp_wager(50) == 50

    def test_to_dict_has_expected_keys(self):
        game = GameDefinition(
            slug="x", display_name="X", min_wager=10, max_wager=100,
            outcomes=_coin_flip_outcomes(),
        )
        d = game.to_dict()
        assert "slug" in d
        assert "display_name" in d
        assert "audit" in d
        assert "outcomes" in d


# ---------------------------------------------------------------------------
# GameCatalog
# ---------------------------------------------------------------------------


def _make_game(slug: str = "test_game") -> GameDefinition:
    return GameDefinition(
        slug=slug,
        display_name=slug,
        min_wager=10,
        max_wager=200,
        outcomes=_coin_flip_outcomes(),
    )


class TestGameCatalog:
    def test_register_and_get(self):
        catalog = GameCatalog()
        game = _make_game("flip")
        catalog.register(game)
        assert catalog.get("flip") is game

    def test_get_unknown_slug_returns_none(self):
        catalog = GameCatalog()
        assert catalog.get("ghost") is None

    def test_duplicate_slug_raises(self):
        catalog = GameCatalog()
        catalog.register(_make_game("flip"))
        with pytest.raises(DuplicateGameError):
            catalog.register(_make_game("flip"))

    def test_unfair_game_blocked_by_default(self):
        catalog = GameCatalog()
        bad_game = GameDefinition(
            slug="exploit",
            display_name="Exploit",
            min_wager=10,
            max_wager=100,
            outcomes=[
                Outcome("win", probability=0.9, multiplier=2.0),
                Outcome("loss", probability=0.1, multiplier=0.0),
            ],
        )
        with pytest.raises(FairnessGuardrailError):
            catalog.register(bad_game)

    def test_unfair_game_allowed_with_enforce_false(self):
        catalog = GameCatalog(enforce_fairness=False)
        bad_game = GameDefinition(
            slug="exploit",
            display_name="Exploit",
            min_wager=10,
            max_wager=100,
            outcomes=[
                Outcome("win", probability=0.9, multiplier=2.0),
                Outcome("loss", probability=0.1, multiplier=0.0),
            ],
        )
        catalog.register(bad_game)
        assert catalog.get("exploit") is not None

    def test_game_count(self):
        catalog = GameCatalog()
        catalog.register(_make_game("a"))
        catalog.register(_make_game("b"))
        assert catalog.game_count() == 2

    def test_all_games_returns_list(self):
        catalog = GameCatalog()
        catalog.register(_make_game("a"))
        catalog.register(_make_game("b"))
        games = catalog.all_games()
        assert len(games) == 2

    def test_to_dict_returns_list(self):
        catalog = GameCatalog()
        catalog.register(_make_game("flip"))
        d = catalog.to_dict()
        assert isinstance(d, list)
        assert d[0]["slug"] == "flip"

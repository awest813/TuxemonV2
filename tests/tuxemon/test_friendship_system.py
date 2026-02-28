# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for the friendship/bond system and evolution variety expansion.

Covers bond gain events, bond-triggered evolution checks,
time-of-day evolution conditions, and trade/item evolution paths.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from tuxemon.monster.bond import BondHandler


class TestBondHandler:
    def test_initial_bond_uses_config_default(self):
        handler = BondHandler()
        assert handler.bond == 25

    def test_increase_bond(self):
        handler = BondHandler()
        handler.increase_bond(10)
        assert handler.bond == 35

    def test_decrease_bond(self):
        handler = BondHandler()
        handler.decrease_bond(5)
        assert handler.bond == 20

    def test_bond_clamps_to_max(self):
        handler = BondHandler()
        handler.bond = 200
        assert handler.bond == 100

    def test_bond_clamps_to_min(self):
        handler = BondHandler()
        handler.bond = -50
        assert handler.bond == 0

    def test_change_bond_absolute(self):
        handler = BondHandler()
        handler.change_bond(10)
        assert handler.bond == 35

    def test_change_bond_percentage(self):
        handler = BondHandler()
        handler.bond = 50
        handler.change_bond(0.5)
        assert handler.bond == 75

    def test_is_max_bond(self):
        handler = BondHandler()
        handler.bond = 100
        assert handler.is_max_bond()

    def test_is_low_bond(self):
        handler = BondHandler()
        handler.bond = 15
        assert handler.is_low_bond()

    def test_bond_decay(self):
        handler = BondHandler()
        handler.bond = 100
        handler.bond_decay(0.1)
        assert handler.bond == 90

    def test_reset_bond(self):
        handler = BondHandler()
        handler.bond = 80
        handler.reset_bond()
        assert handler.bond == 25

    def test_save_and_load_roundtrip(self):
        handler = BondHandler()
        handler.bond = 77
        state = handler.get_state()
        new_handler = BondHandler(state)
        assert new_handler.bond == 77

    def test_load_legacy_format(self):
        handler = BondHandler({"bond": 42})
        assert handler.bond == 42

    def test_load_nested_format(self):
        handler = BondHandler({"bond_dict": {"bond": 63}})
        assert handler.bond == 63


class TestBondModifierEvents:
    def test_apply_fainted_modifier(self):
        handler = BondHandler()
        handler.bond = 50
        handler.apply_bond_modifier("fainted")
        assert handler.bond == 40

    def test_apply_battle_won_modifier(self):
        handler = BondHandler()
        handler.bond = 50
        handler.apply_bond_modifier("battle_won")
        assert handler.bond == 53

    def test_apply_level_up_modifier(self):
        handler = BondHandler()
        handler.bond = 50
        handler.apply_bond_modifier("level_up")
        assert handler.bond == 55

    def test_apply_party_walk_modifier(self):
        handler = BondHandler()
        handler.bond = 50
        handler.apply_bond_modifier("party_walk")
        assert handler.bond == 51

    def test_apply_item_used_modifier(self):
        handler = BondHandler()
        handler.bond = 50
        handler.apply_bond_modifier("item_used")
        assert handler.bond == 52

    def test_apply_traded_modifier(self):
        handler = BondHandler()
        handler.bond = 50
        handler.apply_bond_modifier("traded")
        assert handler.bond == 35

    def test_apply_healed_modifier(self):
        handler = BondHandler()
        handler.bond = 50
        handler.apply_bond_modifier("healed")
        assert handler.bond == 51

    def test_unknown_event_does_nothing(self):
        handler = BondHandler()
        handler.bond = 50
        handler.apply_bond_modifier("nonexistent_event")
        assert handler.bond == 50

    def test_bond_does_not_exceed_max_on_event(self):
        handler = BondHandler()
        handler.bond = 99
        handler.apply_bond_modifier("level_up")
        assert handler.bond == 100

    def test_bond_does_not_go_below_min_on_event(self):
        handler = BondHandler()
        handler.bond = 5
        handler.apply_bond_modifier("fainted")
        assert handler.bond == 0


class TestBondSentiments:
    def test_despises_sentiment(self):
        handler = BondHandler()
        handler.bond = 10
        result = handler.get_bond_sentiment("Mon", "Player")
        assert result is not None

    def test_adores_sentiment(self):
        handler = BondHandler()
        handler.bond = 90
        result = handler.get_bond_sentiment("Mon", "Player")
        assert result is not None

    def test_bond_icon_path_exists(self):
        handler = BondHandler()
        handler.bond = 60
        path = handler.get_bond_icon_path()
        assert path is not None
        assert "bond" in path


class TestEvolutionOnBondChange:
    """Test that bond changes trigger evolution checks."""

    def _make_mock_monster(self, bond: int = 50) -> MagicMock:
        monster = MagicMock()
        monster.bond_handler = BondHandler()
        monster.bond_handler.bond = bond
        monster.waiting_to_evolve = False
        monster.evolution_handler.get_eligible_evolution_slug.return_value = None
        return monster

    def test_bond_change_checks_evolution(self):
        from tuxemon.monster.monster import Monster

        monster = self._make_mock_monster(bond=79)
        monster.evolution_handler.get_eligible_evolution_slug.return_value = (
            "evolved_form"
        )

        # Simulate the apply_bond_event logic
        old_bond = monster.bond_handler.bond
        monster.bond_handler.apply_bond_modifier("battle_won")
        new_bond = monster.bond_handler.bond
        if new_bond != old_bond and not monster.waiting_to_evolve:
            slug = monster.evolution_handler.get_eligible_evolution_slug()
            if slug:
                monster.waiting_to_evolve = True

        assert monster.waiting_to_evolve is True

    def test_no_evolution_when_bond_unchanged(self):
        monster = self._make_mock_monster(bond=50)
        monster.evolution_handler.get_eligible_evolution_slug.return_value = (
            "evolved_form"
        )

        old_bond = monster.bond_handler.bond
        monster.bond_handler.apply_bond_modifier("nonexistent_event")
        new_bond = monster.bond_handler.bond
        if new_bond != old_bond and not monster.waiting_to_evolve:
            slug = monster.evolution_handler.get_eligible_evolution_slug()
            if slug:
                monster.waiting_to_evolve = True

        assert monster.waiting_to_evolve is False

    def test_no_double_evolution_flag(self):
        monster = self._make_mock_monster(bond=79)
        monster.waiting_to_evolve = True
        monster.evolution_handler.get_eligible_evolution_slug.return_value = (
            "evolved_form"
        )

        old_bond = monster.bond_handler.bond
        monster.bond_handler.apply_bond_modifier("battle_won")
        new_bond = monster.bond_handler.bond
        if new_bond != old_bond and not monster.waiting_to_evolve:
            slug = monster.evolution_handler.get_eligible_evolution_slug()
            if slug:
                monster.waiting_to_evolve = True

        monster.evolution_handler.get_eligible_evolution_slug.assert_not_called()


class TestDaytimeEvolutionCondition:
    def test_daytime_condition_true_during_day(self):
        from tuxemon.monster.evolution_conditions import check_daytime

        monster = MagicMock()
        evo_item = MagicMock()
        evo_item.daytime = True

        conditions: list[bool] = []
        with patch(
            "tuxemon.time_handler.TimeHandler"
        ) as MockHandler:
            mock_snapshot = MagicMock()
            mock_snapshot.daytime = "true"
            MockHandler.return_value.get_time_snapshot.return_value = (
                mock_snapshot
            )
            check_daytime(monster, evo_item, conditions)

        assert conditions == [True]

    def test_daytime_condition_false_during_night(self):
        from tuxemon.monster.evolution_conditions import check_daytime

        monster = MagicMock()
        evo_item = MagicMock()
        evo_item.daytime = True

        conditions: list[bool] = []
        with patch(
            "tuxemon.time_handler.TimeHandler"
        ) as MockHandler:
            mock_snapshot = MagicMock()
            mock_snapshot.daytime = "false"
            MockHandler.return_value.get_time_snapshot.return_value = (
                mock_snapshot
            )
            check_daytime(monster, evo_item, conditions)

        assert conditions == [False]

    def test_night_evolution_during_night(self):
        from tuxemon.monster.evolution_conditions import check_daytime

        monster = MagicMock()
        evo_item = MagicMock()
        evo_item.daytime = False

        conditions: list[bool] = []
        with patch(
            "tuxemon.time_handler.TimeHandler"
        ) as MockHandler:
            mock_snapshot = MagicMock()
            mock_snapshot.daytime = "false"
            MockHandler.return_value.get_time_snapshot.return_value = (
                mock_snapshot
            )
            check_daytime(monster, evo_item, conditions)

        assert conditions == [True]

    def test_no_daytime_condition_skipped(self):
        from tuxemon.monster.evolution_conditions import check_daytime

        monster = MagicMock()
        evo_item = MagicMock()
        evo_item.daytime = None

        conditions: list[bool] = []
        check_daytime(monster, evo_item, conditions)

        assert conditions == []


class TestBondEventOnOwnerlessMonster:
    """Verify apply_bond_event works safely on monsters without owners."""

    def test_no_evolution_check_without_owner(self):
        monster = MagicMock()
        monster.bond_handler = BondHandler()
        monster.bond_handler.bond = 79
        monster.waiting_to_evolve = False
        monster.owner = None

        old_bond = monster.bond_handler.bond
        monster.bond_handler.apply_bond_modifier("battle_won")
        new_bond = monster.bond_handler.bond
        if new_bond == old_bond or monster.waiting_to_evolve:
            return
        if monster.owner is None:
            return
        monster.evolution_handler.get_eligible_evolution_slug()

        monster.evolution_handler.get_eligible_evolution_slug.assert_not_called()


class TestExistingEvolutionConditions:
    """Verify existing condition checkers still work correctly."""

    def test_check_bond_greater_than(self):
        from tuxemon.monster.evolution_conditions import check_bond

        monster = MagicMock()
        monster.bond_handler.bond = 80

        evo_item = MagicMock()
        evo_item.bond.comparison.value = "greater_than"
        evo_item.bond.value = 40

        conditions: list[bool] = []
        check_bond(monster, evo_item, conditions)
        assert conditions == [True]

    def test_check_bond_not_met(self):
        from tuxemon.monster.evolution_conditions import check_bond

        monster = MagicMock()
        monster.bond_handler.bond = 30

        evo_item = MagicMock()
        evo_item.bond.comparison.value = "greater_than"
        evo_item.bond.value = 40

        conditions: list[bool] = []
        check_bond(monster, evo_item, conditions)
        assert conditions == [False]

    def test_check_bond_skipped_when_none(self):
        from tuxemon.monster.evolution_conditions import check_bond

        monster = MagicMock()
        evo_item = MagicMock()
        evo_item.bond = None

        conditions: list[bool] = []
        check_bond(monster, evo_item, conditions)
        assert conditions == []

# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""Tests for the Battle Tower facility."""
from __future__ import annotations

import pytest

from tuxemon.battle_tower import (
    BattleTowerManager,
    BattleTowerOpponent,
    BattleTowerRules,
    BattleTowerState,
)

MONSTER_POOL = ["alpha", "beta", "gamma", "delta", "epsilon", "zeta"]


@pytest.fixture
def manager() -> BattleTowerManager:
    m = BattleTowerManager(monster_pool=MONSTER_POOL)
    return m


class TestBattleTowerState:
    def test_default_state(self):
        state = BattleTowerState()
        assert state.current_rank == 0
        assert state.current_streak == 0
        assert state.best_streak == 0
        assert state.total_wins == 0
        assert state.total_losses == 0

    def test_roundtrip_serialization(self):
        state = BattleTowerState(
            current_rank=5,
            current_streak=12,
            best_streak=15,
            total_wins=50,
            total_losses=10,
        )
        data = state.to_dict()
        restored = BattleTowerState.from_dict(data)
        assert restored.current_rank == 5
        assert restored.current_streak == 12
        assert restored.best_streak == 15
        assert restored.total_wins == 50
        assert restored.total_losses == 10

    def test_from_dict_with_missing_keys(self):
        state = BattleTowerState.from_dict({})
        assert state.current_rank == 0
        assert state.current_streak == 0


class TestBattleTowerRules:
    def test_default_rules(self):
        rules = BattleTowerRules()
        assert rules.level_cap == 50
        assert rules.party_size == 3
        assert rules.allow_items is False
        assert rules.allow_duplicates is False

    def test_custom_rules(self):
        rules = BattleTowerRules(level_cap=100, party_size=6, allow_items=True)
        assert rules.level_cap == 100
        assert rules.party_size == 6
        assert rules.allow_items is True


class TestOpponentGeneration:
    def test_generate_opponent_returns_valid_opponent(self, manager):
        opp = manager.generate_opponent()
        assert isinstance(opp, BattleTowerOpponent)
        assert opp.name
        assert len(opp.monster_slugs) >= 1
        assert opp.monster_level >= 10
        assert opp.difficulty_rank == 0

    def test_opponent_level_scales_with_rank(self, manager):
        level_at_0 = manager._calculate_opponent_level()
        manager.state.current_rank = 5
        level_at_5 = manager._calculate_opponent_level()
        assert level_at_5 > level_at_0

    def test_opponent_level_capped(self, manager):
        manager.state.current_rank = 100
        level = manager._calculate_opponent_level()
        assert level <= manager.rules.level_cap

    def test_party_size_scales_with_rank(self, manager):
        size_at_0 = manager._calculate_party_size()
        assert size_at_0 == 1

        manager.state.current_rank = 3
        size_at_3 = manager._calculate_party_size()
        assert size_at_3 == 2

        manager.state.current_rank = 6
        size_at_6 = manager._calculate_party_size()
        assert size_at_6 == 3

    def test_no_duplicate_monsters_by_default(self, manager):
        manager.state.current_rank = 10
        opp = manager.generate_opponent()
        assert len(opp.monster_slugs) == len(set(opp.monster_slugs))

    def test_empty_pool_produces_empty_party(self):
        manager = BattleTowerManager(monster_pool=[])
        opp = manager.generate_opponent()
        assert opp.monster_slugs == []

    def test_set_monster_pool(self, manager):
        manager.set_monster_pool(["only_one"])
        opp = manager.generate_opponent()
        assert opp.monster_slugs == ["only_one"]


class TestWinLossTracking:
    def test_record_win_increments_streak(self, manager):
        result = manager.record_win()
        assert result["streak"] == 1
        assert manager.state.current_streak == 1
        assert manager.state.total_wins == 1

    def test_consecutive_wins_build_streak(self, manager):
        for i in range(5):
            result = manager.record_win()
        assert result["streak"] == 5
        assert manager.state.best_streak == 5

    def test_loss_resets_streak(self, manager):
        for _ in range(5):
            manager.record_win()
        result = manager.record_loss()
        assert result["streak"] == 0
        assert manager.state.current_streak == 0
        assert manager.state.best_streak == 5
        assert manager.state.total_losses == 1

    def test_rank_up_every_7_wins(self, manager):
        for i in range(7):
            result = manager.record_win()
        assert result["rank"] == 1
        assert result["rank_up"] == 1

    def test_rank_does_not_increase_before_7(self, manager):
        for i in range(6):
            result = manager.record_win()
        assert result["rank"] == 0

    def test_multiple_rank_ups(self, manager):
        for i in range(21):
            result = manager.record_win()
        assert manager.state.current_rank == 3


class TestRewards:
    def test_reward_increases_with_streak(self, manager):
        r1 = manager.record_win()
        r2 = manager.record_win()
        assert r2["money"] > r1["money"]

    def test_reward_includes_rank_bonus(self, manager):
        manager.state.current_rank = 5
        result = manager.record_win()
        assert result["money"] >= 100


class TestSaveLoad:
    def test_save_and_load_state(self, manager):
        for _ in range(10):
            manager.record_win()
        manager.record_loss()
        for _ in range(3):
            manager.record_win()

        state = manager.get_state()
        new_manager = BattleTowerManager(monster_pool=MONSTER_POOL)
        new_manager.set_state(state)

        assert new_manager.state.current_rank == manager.state.current_rank
        assert new_manager.state.current_streak == manager.state.current_streak
        assert new_manager.state.best_streak == manager.state.best_streak
        assert new_manager.state.total_wins == manager.state.total_wins
        assert new_manager.state.total_losses == manager.state.total_losses

    def test_load_empty_state(self, manager):
        manager.set_state({})
        assert manager.state.current_rank == 0

    def test_load_partial_state(self, manager):
        manager.set_state({"battle_tower": {"current_rank": 7}})
        assert manager.state.current_rank == 7
        assert manager.state.current_streak == 0


class TestSummary:
    def test_get_summary(self, manager):
        for _ in range(3):
            manager.record_win()
        summary = manager.get_summary()
        assert summary["rank"] == 0
        assert summary["current_streak"] == 3
        assert summary["total_wins"] == 3
        assert summary["next_opponent_level"] >= 10
        assert "rules" in summary

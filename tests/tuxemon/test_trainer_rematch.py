# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""Tests for the trainer rematch system."""
from __future__ import annotations

import time

import pytest

from tuxemon.trainer_rematch import (
    TrainerRematchEntry,
    TrainerRematchManager,
)


@pytest.fixture
def manager() -> TrainerRematchManager:
    return TrainerRematchManager(
        level_scaling=3,
        max_level_bonus=30,
        default_cooldown=300,
    )


class TestTrainerRematchEntry:
    def test_default_entry(self):
        entry = TrainerRematchEntry(trainer_slug="rival")
        assert entry.rematch_count == 0
        assert entry.last_defeated_at == 0.0
        assert entry.cooldown_seconds == 300

    def test_roundtrip(self):
        entry = TrainerRematchEntry(
            trainer_slug="gym_leader",
            rematch_count=5,
            last_defeated_at=1000.0,
            cooldown_seconds=600,
        )
        data = entry.to_dict()
        restored = TrainerRematchEntry.from_dict(data)
        assert restored.trainer_slug == "gym_leader"
        assert restored.rematch_count == 5
        assert restored.cooldown_seconds == 600


class TestRecordDefeat:
    def test_first_defeat(self, manager):
        now = 1000.0
        entry = manager.record_defeat("rival", now=now)
        assert entry.rematch_count == 1
        assert entry.last_defeated_at == now

    def test_multiple_defeats(self, manager):
        manager.record_defeat("rival", now=1000.0)
        manager.record_defeat("rival", now=2000.0)
        assert manager.get_rematch_count("rival") == 2

    def test_different_trainers(self, manager):
        manager.record_defeat("rival", now=1000.0)
        manager.record_defeat("gym_leader", now=1000.0)
        assert manager.get_rematch_count("rival") == 1
        assert manager.get_rematch_count("gym_leader") == 1


class TestRematchAvailability:
    def test_not_available_before_defeat(self, manager):
        assert manager.is_rematch_available("rival") is False

    def test_not_available_during_cooldown(self, manager):
        now = 1000.0
        manager.record_defeat("rival", now=now)
        assert manager.is_rematch_available("rival", now=now + 100) is False

    def test_available_after_cooldown(self, manager):
        now = 1000.0
        manager.record_defeat("rival", now=now)
        assert manager.is_rematch_available("rival", now=now + 301) is True

    def test_cooldown_remaining(self, manager):
        now = 1000.0
        manager.record_defeat("rival", now=now)
        remaining = manager.get_cooldown_remaining("rival", now=now + 100)
        assert remaining == 200.0

    def test_cooldown_remaining_zero_when_ready(self, manager):
        now = 1000.0
        manager.record_defeat("rival", now=now)
        remaining = manager.get_cooldown_remaining("rival", now=now + 500)
        assert remaining == 0.0

    def test_get_available_rematches(self, manager):
        now = 1000.0
        manager.record_defeat("rival", now=now)
        manager.record_defeat("gym_leader", now=now)
        manager.record_defeat("elite", now=now + 200)

        available = manager.get_available_rematches(now=now + 301)
        assert "rival" in available
        assert "gym_leader" in available
        assert "elite" not in available


class TestLevelScaling:
    def test_no_bonus_before_defeat(self, manager):
        assert manager.get_level_bonus("rival") == 0

    def test_bonus_increases_with_rematches(self, manager):
        manager.record_defeat("rival", now=1000.0)
        assert manager.get_level_bonus("rival") == 3
        manager.record_defeat("rival", now=2000.0)
        assert manager.get_level_bonus("rival") == 6

    def test_bonus_capped(self, manager):
        for i in range(20):
            manager.record_defeat("rival", now=float(i * 1000))
        assert manager.get_level_bonus("rival") == 30

    def test_rematch_level_calculation(self, manager):
        manager.record_defeat("rival", now=1000.0)
        manager.record_defeat("rival", now=2000.0)
        level = manager.get_rematch_level("rival", base_level=15)
        assert level == 21


class TestSaveLoad:
    def test_save_and_load_roundtrip(self, manager):
        manager.record_defeat("rival", now=1000.0)
        manager.record_defeat("rival", now=2000.0)
        manager.record_defeat("gym_leader", now=1500.0)

        state = manager.get_state()
        new_manager = TrainerRematchManager()
        new_manager.set_state(state)

        assert new_manager.get_rematch_count("rival") == 2
        assert new_manager.get_rematch_count("gym_leader") == 1
        assert new_manager.level_scaling == 3
        assert new_manager.max_level_bonus == 30

    def test_load_empty_state(self, manager):
        manager.set_state({})
        assert manager.get_available_rematches() == []

    def test_load_malformed_entries_skipped(self, manager):
        manager.set_state({
            "trainer_rematches": {
                "valid": {"trainer_slug": "valid", "rematch_count": 2},
                "bad": "not_a_dict",
                "invalid": {"missing_fields": True},
            }
        })
        assert manager.get_rematch_count("valid") == 2


class TestSummary:
    def test_summary_structure(self, manager):
        manager.record_defeat("rival", now=1000.0)
        summary = manager.get_summary()
        assert summary["total_trainers"] == 1
        assert "rival" in summary["trainers"]
        assert summary["trainers"]["rival"]["rematch_count"] == 1

# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from dataclasses import dataclass

from tuxemon.entity.trainer_state import TrainerStateManager
from tuxemon.game_variables import GameVariablesManager
from tuxemon.world.milestone_tracker import PostgameMilestoneTracker
from tuxemon.world.rematch_progression import RematchProgressionService


@dataclass
class DummyPlayer:
    slug: str = "player"

    def __post_init__(self) -> None:
        self.variable_manager = GameVariablesManager()
        self.trainer_state_manager = TrainerStateManager()
        self.milestone_tracker = PostgameMilestoneTracker(player_id=self.slug)


def test_badge_threshold_controls_rematch_unlock():
    player = DummyPlayer()
    player.trainer_state_manager.record_defeat("trainer_a")
    player.variable_manager.world.set("rematch.required_badges.default", 2)

    service = RematchProgressionService(player)

    service.tick()
    assert not player.trainer_state_manager.is_rematch_eligible("trainer_a")

    player.variable_manager.player.set("progress.badges", 1)
    service.tick()
    assert not player.trainer_state_manager.is_rematch_eligible("trainer_a")

    player.variable_manager.player.set("progress.badges", 2)
    service.tick()
    assert player.trainer_state_manager.is_rematch_eligible("trainer_a")


def test_trainer_specific_milestone_requirement():
    player = DummyPlayer()
    player.trainer_state_manager.record_defeat("trainer_b")
    player.variable_manager.world.set(
        "rematch.required_milestones.trainer_b",
        "story_complete, returner",
    )
    service = RematchProgressionService(player)

    service.tick()
    assert not player.trainer_state_manager.is_rematch_eligible("trainer_b")

    player.milestone_tracker.record_story_complete()
    service.tick()
    assert not player.trainer_state_manager.is_rematch_eligible("trainer_b")

    player.milestone_tracker.record_rematch_win()
    service.tick()
    assert player.trainer_state_manager.is_rematch_eligible("trainer_b")


def test_tick_returns_false_when_progression_unchanged():
    player = DummyPlayer()
    player.trainer_state_manager.record_defeat("trainer_c")
    service = RematchProgressionService(player)

    assert service.tick() is True
    assert service.tick() is False

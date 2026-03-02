# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for Hook 4.6 (on_rematch_eligible) integration in TrainerStateManager.

Verifies that set_rematch_eligible() correctly fires the hook only when
eligibility transitions from False → True, and only once.
"""
from __future__ import annotations

import pytest

from tuxemon.entity.trainer_state import TrainerStateManager
from tuxemon.time_hooks import RematchEligiblePayload, hooks


@pytest.fixture(autouse=True)
def clear_hooks():
    hooks.clear()
    yield
    hooks.clear()


@pytest.fixture
def mgr() -> TrainerStateManager:
    return TrainerStateManager()


def test_hook_fires_when_eligibility_set_true(mgr: TrainerStateManager):
    fired: list[RematchEligiblePayload] = []
    hooks.on_rematch_eligible(fired.append)

    mgr.set_rematch_eligible("trainer_1", eligible=True, player_id="player")

    assert len(fired) == 1
    assert fired[0].trainer_id == "trainer_1"
    assert fired[0].player_id == "player"


def test_hook_not_fired_when_eligibility_set_false(mgr: TrainerStateManager):
    fired: list[RematchEligiblePayload] = []
    hooks.on_rematch_eligible(fired.append)

    mgr.set_rematch_eligible("trainer_1", eligible=False)

    assert fired == []


def test_hook_not_fired_when_already_eligible(mgr: TrainerStateManager):
    mgr.set_rematch_eligible("trainer_1", eligible=True, player_id="player")

    fired: list[RematchEligiblePayload] = []
    hooks.on_rematch_eligible(fired.append)

    mgr.set_rematch_eligible("trainer_1", eligible=True, player_id="player")

    assert fired == [], "Hook must not re-fire when already eligible"


def test_hook_fires_again_after_reset(mgr: TrainerStateManager):
    fired: list[RematchEligiblePayload] = []
    hooks.on_rematch_eligible(fired.append)

    mgr.set_rematch_eligible("trainer_1", eligible=True, player_id="p")
    mgr.set_rematch_eligible("trainer_1", eligible=False)
    mgr.set_rematch_eligible("trainer_1", eligible=True, player_id="p")

    assert len(fired) == 2


def test_hook_without_player_id_fires_with_empty_string(mgr: TrainerStateManager):
    fired: list[RematchEligiblePayload] = []
    hooks.on_rematch_eligible(fired.append)

    mgr.set_rematch_eligible("trainer_1", eligible=True)

    assert len(fired) == 1
    assert fired[0].player_id == ""


def test_multiple_trainers_fire_independently(mgr: TrainerStateManager):
    fired: list[RematchEligiblePayload] = []
    hooks.on_rematch_eligible(fired.append)

    mgr.set_rematch_eligible("trainer_a", eligible=True, player_id="player")
    mgr.set_rematch_eligible("trainer_b", eligible=True, player_id="player")

    trainer_ids = {p.trainer_id for p in fired}
    assert trainer_ids == {"trainer_a", "trainer_b"}

# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for the trainer state model and manager.

Covers the persistent trainer state described in
docs/gold_silver_blueprint.md §3.1 and §3.2.
"""

from __future__ import annotations

from datetime import datetime, timedelta

import pytest

from tuxemon.entity.trainer_state import TrainerStateManager
from tuxemon.save_state import TIME_FORMAT, TrainerState

# ---------------------------------------------------------------------------
# TrainerState model
# ---------------------------------------------------------------------------


class TestTrainerStateModel:
    def test_defaults(self):
        ts = TrainerState(trainer_id="gym_1")
        assert ts.trainer_id == "gym_1"
        assert ts.defeated is False
        assert ts.last_rematch_at is None
        assert ts.rematch_count == 0
        assert ts.rematch_eligible is False

    def test_fully_specified(self):
        ts = TrainerState(
            trainer_id="gym_1",
            defeated=True,
            last_rematch_at="2026-03-01 10:00",
            rematch_count=3,
            rematch_eligible=True,
        )
        assert ts.defeated is True
        assert ts.rematch_count == 3
        assert ts.rematch_eligible is True

    def test_rematch_count_non_negative(self):
        with pytest.raises(Exception):
            TrainerState(trainer_id="gym_1", rematch_count=-1)


# ---------------------------------------------------------------------------
# TrainerStateManager — basic operations
# ---------------------------------------------------------------------------


@pytest.fixture
def mgr() -> TrainerStateManager:
    return TrainerStateManager()


def test_get_creates_default_state(mgr: TrainerStateManager):
    state = mgr.get("trainer_1")
    assert state.trainer_id == "trainer_1"
    assert state.defeated is False


def test_get_same_instance(mgr: TrainerStateManager):
    s1 = mgr.get("trainer_1")
    s2 = mgr.get("trainer_1")
    assert s1.trainer_id == s2.trainer_id


def test_is_defeated_initially_false(mgr: TrainerStateManager):
    assert mgr.is_defeated("trainer_1") is False


def test_record_defeat(mgr: TrainerStateManager):
    mgr.record_defeat("trainer_1")
    assert mgr.is_defeated("trainer_1") is True


def test_record_defeat_preserves_other_fields(mgr: TrainerStateManager):
    mgr.set_rematch_eligible("trainer_1", True)
    mgr.record_defeat("trainer_1")
    assert mgr.get("trainer_1").rematch_eligible is True


def test_set_rematch_eligible_true(mgr: TrainerStateManager):
    mgr.set_rematch_eligible("trainer_1", True)
    assert mgr.is_rematch_eligible("trainer_1") is True


def test_set_rematch_eligible_false(mgr: TrainerStateManager):
    mgr.set_rematch_eligible("trainer_1", True)
    mgr.set_rematch_eligible("trainer_1", False)
    assert mgr.is_rematch_eligible("trainer_1") is False


def test_record_rematch_increments_count(mgr: TrainerStateManager):
    mgr.record_rematch("trainer_1")
    assert mgr.get("trainer_1").rematch_count == 1
    mgr.record_rematch("trainer_1")
    assert mgr.get("trainer_1").rematch_count == 2


def test_record_rematch_stamps_time(mgr: TrainerStateManager):
    before = datetime.now()
    mgr.record_rematch("trainer_1")
    after = datetime.now()

    ts_str = mgr.get("trainer_1").last_rematch_at
    assert ts_str is not None
    recorded = datetime.strptime(ts_str, TIME_FORMAT)
    assert (
        before.replace(second=0, microsecond=0)
        <= recorded
        <= after.replace(second=59, microsecond=999999)
    )


# ---------------------------------------------------------------------------
# TrainerStateManager — rematch readiness
# ---------------------------------------------------------------------------


def test_not_ready_when_not_eligible(mgr: TrainerStateManager):
    assert mgr.is_rematch_ready("trainer_1") is False


def test_ready_when_eligible_and_no_prior_rematch(mgr: TrainerStateManager):
    mgr.set_rematch_eligible("trainer_1", True)
    assert mgr.is_rematch_ready("trainer_1") is True


def test_not_ready_when_cooldown_has_not_elapsed(mgr: TrainerStateManager):
    recent = (datetime.now() - timedelta(hours=1)).strftime(TIME_FORMAT)
    mgr._states["trainer_1"] = TrainerState(
        trainer_id="trainer_1",
        rematch_eligible=True,
        last_rematch_at=recent,
    )
    assert mgr.is_rematch_ready("trainer_1", cooldown_hours=24) is False


def test_ready_when_cooldown_has_elapsed(mgr: TrainerStateManager):
    old = (datetime.now() - timedelta(hours=25)).strftime(TIME_FORMAT)
    mgr._states["trainer_1"] = TrainerState(
        trainer_id="trainer_1",
        rematch_eligible=True,
        last_rematch_at=old,
    )
    assert mgr.is_rematch_ready("trainer_1", cooldown_hours=24) is True


# ---------------------------------------------------------------------------
# TrainerStateManager — serialisation round-trip
# ---------------------------------------------------------------------------


def test_encode_decode_round_trip(mgr: TrainerStateManager):
    mgr.record_defeat("gym_1")
    mgr.set_rematch_eligible("gym_1", True)
    mgr.record_rematch("gym_1")

    encoded = mgr.encode()

    mgr2 = TrainerStateManager()
    mgr2.decode(encoded)

    s = mgr2.get("gym_1")
    assert s.defeated is True
    assert s.rematch_eligible is True
    assert s.rematch_count == 1
    assert s.last_rematch_at is not None


def test_encode_empty_manager(mgr: TrainerStateManager):
    assert mgr.encode() == {}


def test_decode_empty_dict(mgr: TrainerStateManager):
    mgr.decode({})
    assert mgr.encode() == {}


def test_decode_ignores_malformed_entries(mgr: TrainerStateManager):
    mgr.decode({"bad_trainer": {"not_valid_fields": True}})
    # Should not raise; bad entry is skipped
    assert "bad_trainer" not in mgr._states


def test_multiple_trainers_independent(mgr: TrainerStateManager):
    mgr.record_defeat("trainer_a")
    mgr.set_rematch_eligible("trainer_b", True)

    assert mgr.is_defeated("trainer_a") is True
    assert mgr.is_defeated("trainer_b") is False
    assert mgr.is_rematch_eligible("trainer_a") is False
    assert mgr.is_rematch_eligible("trainer_b") is True

# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for the time-aware hook registry (tuxemon/time_hooks.py).

Covers all 9 hooks defined in docs/gold_silver_blueprint.md §4.
"""

from __future__ import annotations

from datetime import date, datetime

import pytest

from tuxemon.time_hooks import (
    DayChangePayload,
    EncounterTableQueryPayload,
    HookRegistry,
    MapZoneEnterPayload,
    PostgameMilestonePayload,
    RematchEligiblePayload,
    TimeSegmentChangePayload,
    TrainerDefeatedPayload,
    WeeklyEventWindowPayload,
    hooks,
)


@pytest.fixture(autouse=True)
def isolate_global_registry():
    """Clear the module-level registry before and after each test."""
    hooks.clear()
    yield
    hooks.clear()


@pytest.fixture()
def registry() -> HookRegistry:
    """Return a fresh, isolated registry for handler-registration tests."""
    return HookRegistry()


# ---------------------------------------------------------------------------
# Hook 4.1 — on_time_segment_change
# ---------------------------------------------------------------------------


def test_time_segment_change_handler_fires(registry: HookRegistry):
    received: list[TimeSegmentChangePayload] = []
    registry.on_time_segment_change(received.append)

    payload = TimeSegmentChangePayload(
        previous_segment="morning",
        new_segment="afternoon",
        current_time=datetime(2026, 3, 1, 12, 0),
    )
    registry.fire_time_segment_change(payload)
    assert received == [payload]


def test_time_segment_change_multiple_handlers(registry: HookRegistry):
    log: list[str] = []
    registry.on_time_segment_change(lambda p: log.append("first"))
    registry.on_time_segment_change(lambda p: log.append("second"))

    registry.fire_time_segment_change(
        TimeSegmentChangePayload("dawn", "morning", datetime.now())
    )
    assert log == ["first", "second"]


def test_time_segment_change_handler_exception_does_not_propagate(
    registry: HookRegistry,
):
    def bad_handler(p: TimeSegmentChangePayload) -> None:
        raise RuntimeError("boom")

    registry.on_time_segment_change(bad_handler)
    registry.fire_time_segment_change(
        TimeSegmentChangePayload("dusk", "night", datetime.now())
    )


# ---------------------------------------------------------------------------
# Hook 4.2 — on_day_change
# ---------------------------------------------------------------------------


def test_day_change_handler_fires(registry: HookRegistry):
    received: list[DayChangePayload] = []
    registry.on_day_change(received.append)

    payload = DayChangePayload(
        previous_date=date(2026, 2, 28),
        new_date=date(2026, 3, 1),
        weekday="sunday",
    )
    registry.fire_day_change(payload)
    assert received == [payload]


# ---------------------------------------------------------------------------
# Hook 4.3 — on_map_zone_enter
# ---------------------------------------------------------------------------


def test_map_zone_enter_handler_fires(registry: HookRegistry):
    received: list[MapZoneEnterPayload] = []
    registry.on_map_zone_enter(received.append)

    payload = MapZoneEnterPayload(
        zone_id="national_park",
        player_id="player_1",
        current_time=datetime.now(),
        time_segment="morning",
        weekday="tuesday",
        season="spring",
    )
    registry.fire_map_zone_enter(payload)
    assert received == [payload]


# ---------------------------------------------------------------------------
# Hook 4.4 — on_encounter_table_query (chaining filter)
# ---------------------------------------------------------------------------


def _make_encounter_payload(table: list[dict]) -> EncounterTableQueryPayload:
    return EncounterTableQueryPayload(
        zone_id="test_zone",
        current_time=datetime.now(),
        time_segment="morning",
        weekday="monday",
        season="spring",
        raw_encounter_table=table,
    )


def test_encounter_table_query_no_handlers_returns_raw(registry: HookRegistry):
    table = [{"monster": "agnite"}, {"monster": "pairagrin"}]
    result = registry.fire_encounter_table_query(
        _make_encounter_payload(table)
    )
    assert result == table


def test_encounter_table_query_filter_reduces_table(registry: HookRegistry):
    def filter_to_agnite(
        payload: EncounterTableQueryPayload,
    ) -> list[dict]:
        return [
            e for e in payload.raw_encounter_table if e["monster"] == "agnite"
        ]

    registry.on_encounter_table_query(filter_to_agnite)

    table = [{"monster": "agnite"}, {"monster": "pairagrin"}]
    result = registry.fire_encounter_table_query(
        _make_encounter_payload(table)
    )
    assert result == [{"monster": "agnite"}]


def test_encounter_table_query_handlers_chain(registry: HookRegistry):
    """Each handler receives the output of the previous one."""
    calls: list[int] = []

    def first(p: EncounterTableQueryPayload) -> list[dict]:
        calls.append(len(p.raw_encounter_table))
        return p.raw_encounter_table[:2]

    def second(p: EncounterTableQueryPayload) -> list[dict]:
        calls.append(len(p.raw_encounter_table))
        return p.raw_encounter_table[:1]

    registry.on_encounter_table_query(first)
    registry.on_encounter_table_query(second)

    table = [{"monster": "a"}, {"monster": "b"}, {"monster": "c"}]
    result = registry.fire_encounter_table_query(
        _make_encounter_payload(table)
    )
    assert calls == [3, 2]
    assert len(result) == 1


# ---------------------------------------------------------------------------
# Hook 4.5 — on_trainer_defeated
# ---------------------------------------------------------------------------


def test_trainer_defeated_handler_fires(registry: HookRegistry):
    received: list[TrainerDefeatedPayload] = []
    registry.on_trainer_defeated(received.append)

    payload = TrainerDefeatedPayload(
        trainer_id="gym_leader_1",
        player_id="player_1",
        timestamp=datetime.now(),
    )
    registry.fire_trainer_defeated(payload)
    assert received == [payload]


# ---------------------------------------------------------------------------
# Hook 4.6 — on_rematch_eligible
# ---------------------------------------------------------------------------


def test_rematch_eligible_handler_fires(registry: HookRegistry):
    received: list[RematchEligiblePayload] = []
    registry.on_rematch_eligible(received.append)

    payload = RematchEligiblePayload(
        trainer_id="gym_leader_1",
        player_id="player_1",
    )
    registry.fire_rematch_eligible(payload)
    assert received == [payload]


# ---------------------------------------------------------------------------
# Hook 4.7 — on_weekly_event_window_open
# ---------------------------------------------------------------------------


def test_weekly_event_window_open_fires(registry: HookRegistry):
    received: list[WeeklyEventWindowPayload] = []
    registry.on_weekly_event_window_open(received.append)

    payload = WeeklyEventWindowPayload(
        event_id="bug_catching_contest",
        zone_id="national_park",
        current_time=datetime.now(),
        time_segment="morning",
        weekday="tuesday",
    )
    registry.fire_weekly_event_window_open(payload)
    assert received == [payload]


# ---------------------------------------------------------------------------
# Hook 4.8 — on_weekly_event_window_close
# ---------------------------------------------------------------------------


def test_weekly_event_window_close_fires(registry: HookRegistry):
    received: list[WeeklyEventWindowPayload] = []
    registry.on_weekly_event_window_close(received.append)

    payload = WeeklyEventWindowPayload(
        event_id="bug_catching_contest",
        zone_id="national_park",
        current_time=datetime.now(),
        time_segment="afternoon",
        weekday="tuesday",
    )
    registry.fire_weekly_event_window_close(payload)
    assert received == [payload]


# ---------------------------------------------------------------------------
# Hook 4.9 — on_postgame_milestone_reached
# ---------------------------------------------------------------------------


def test_postgame_milestone_fires(registry: HookRegistry):
    received: list[PostgameMilestonePayload] = []
    registry.on_postgame_milestone_reached(received.append)

    payload = PostgameMilestonePayload(
        milestone_id="story_complete",
        player_id="player_1",
        timestamp=datetime.now(),
    )
    registry.fire_postgame_milestone_reached(payload)
    assert received == [payload]


# ---------------------------------------------------------------------------
# Registry management
# ---------------------------------------------------------------------------


def test_clear_removes_all_handlers(registry: HookRegistry):
    log: list[str] = []
    registry.on_time_segment_change(lambda p: log.append("fired"))
    registry.clear()

    registry.fire_time_segment_change(
        TimeSegmentChangePayload("morning", "afternoon", datetime.now())
    )
    assert log == []


def test_decorator_returns_original_callable(registry: HookRegistry):
    def my_handler(p: TimeSegmentChangePayload) -> None:
        pass

    returned = registry.on_time_segment_change(my_handler)
    assert returned is my_handler


def test_module_level_registry_is_hook_registry():
    assert isinstance(hooks, HookRegistry)

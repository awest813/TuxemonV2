# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for the WeeklyEventCalendar schema and WeeklyEventScheduler runtime.

Covers the design described in docs/gold_silver_blueprint.md §2.4.
"""
from __future__ import annotations

from datetime import datetime
from unittest.mock import MagicMock

import pytest

from tuxemon.time_handler import TimeSnapshot
from tuxemon.time_hooks import WeeklyEventWindowPayload, hooks
from tuxemon.world.weekly_events import (
    WeeklyEventCalendar,
    WeeklyEventEntry,
    WeeklyEventScheduler,
)


@pytest.fixture(autouse=True)
def clear_hooks():
    hooks.clear()
    yield
    hooks.clear()


# ---------------------------------------------------------------------------
# WeeklyEventEntry schema
# ---------------------------------------------------------------------------


class TestWeeklyEventEntry:
    def test_valid_entry(self):
        entry = WeeklyEventEntry(
            id="bug_contest",
            name_key="event_bug_catching_contest",
            days=["tuesday", "thursday", "saturday"],
            time=["morning", "afternoon"],
            map="national_park",
            trigger_script="start_bug_contest",
            reward_script="award_bug_contest",
        )
        assert entry.id == "bug_contest"
        assert "tuesday" in entry.days

    def test_invalid_day_raises(self):
        with pytest.raises(Exception):
            WeeklyEventEntry(
                id="bad",
                name_key="bad_event",
                days=["funday"],  # invalid
                time=["morning"],
            )

    def test_invalid_time_raises(self):
        with pytest.raises(Exception):
            WeeklyEventEntry(
                id="bad",
                name_key="bad_event",
                days=["monday"],
                time=["lunchtime"],  # invalid
            )

    def test_empty_days_raises(self):
        with pytest.raises(Exception):
            WeeklyEventEntry(
                id="bad",
                name_key="bad_event",
                days=[],
                time=["morning"],
            )

    def test_is_active_now_true(self):
        entry = WeeklyEventEntry(
            id="e",
            name_key="k",
            days=["tuesday"],
            time=["morning"],
        )
        assert entry.is_active_now("tuesday", "morning") is True

    def test_is_active_now_wrong_day(self):
        entry = WeeklyEventEntry(
            id="e",
            name_key="k",
            days=["tuesday"],
            time=["morning"],
        )
        assert entry.is_active_now("monday", "morning") is False

    def test_is_active_now_wrong_time(self):
        entry = WeeklyEventEntry(
            id="e",
            name_key="k",
            days=["tuesday"],
            time=["morning"],
        )
        assert entry.is_active_now("tuesday", "night") is False


# ---------------------------------------------------------------------------
# WeeklyEventCalendar
# ---------------------------------------------------------------------------

_SAMPLE_DICT = {
    "weekly_events": [
        {
            "id": "bug_catching_contest",
            "name_key": "event_bug_catching_contest",
            "days": ["tuesday", "thursday", "saturday"],
            "time": ["morning", "afternoon"],
            "map": "national_park",
            "trigger_script": "start_bug_contest",
            "reward_script": "award_bug_contest",
        },
        {
            "id": "farmers_market",
            "name_key": "event_farmers_market",
            "days": ["sunday"],
            "time": ["morning", "afternoon", "dusk"],
            "map": "goldenrod_market_square",
            "trigger_script": "open_farmers_market",
        },
    ]
}


class TestWeeklyEventCalendar:
    def test_from_dict(self):
        cal = WeeklyEventCalendar.from_dict(_SAMPLE_DICT)
        assert len(cal.weekly_events) == 2

    def test_get_event_by_id(self):
        cal = WeeklyEventCalendar.from_dict(_SAMPLE_DICT)
        event = cal.get_event("bug_catching_contest")
        assert event is not None
        assert event.name_key == "event_bug_catching_contest"

    def test_get_event_missing_returns_none(self):
        cal = WeeklyEventCalendar.from_dict(_SAMPLE_DICT)
        assert cal.get_event("nonexistent") is None

    def test_get_active_events_tuesday_morning(self):
        cal = WeeklyEventCalendar.from_dict(_SAMPLE_DICT)
        active = cal.get_active_events("tuesday", "morning")
        assert len(active) == 1
        assert active[0].id == "bug_catching_contest"

    def test_get_active_events_sunday_afternoon(self):
        cal = WeeklyEventCalendar.from_dict(_SAMPLE_DICT)
        active = cal.get_active_events("sunday", "afternoon")
        assert len(active) == 1
        assert active[0].id == "farmers_market"

    def test_get_active_events_no_match(self):
        cal = WeeklyEventCalendar.from_dict(_SAMPLE_DICT)
        active = cal.get_active_events("monday", "night")
        assert active == []

    def test_empty_calendar(self):
        cal = WeeklyEventCalendar()
        assert cal.get_active_events("tuesday", "morning") == []


# ---------------------------------------------------------------------------
# WeeklyEventScheduler
# ---------------------------------------------------------------------------


def _make_scheduler(calendar: WeeklyEventCalendar) -> WeeklyEventScheduler:
    return WeeklyEventScheduler(calendar)


def _patch_time(scheduler: WeeklyEventScheduler, snapshot: TimeSnapshot) -> None:
    scheduler._time_handler.get_time_variables = lambda: snapshot


def _snap(weekday: str, stage_of_day: str) -> TimeSnapshot:
    return TimeSnapshot(
        hour=9,
        day_of_year=80,
        year=2026,
        month=3,
        day=21,
        weekday=weekday,
        leap_year="false",
        daytime="true",
        stage_of_day=stage_of_day,
        season="spring",
    )


class TestWeeklyEventScheduler:
    def _make(self, cal_dict: dict | None = None) -> WeeklyEventScheduler:
        cal = WeeklyEventCalendar.from_dict(cal_dict or _SAMPLE_DICT)
        return _make_scheduler(cal)

    def test_initially_no_open_events(self):
        sched = self._make()
        assert len(sched.open_event_ids) == 0

    def test_tick_opens_matching_event(self):
        sched = self._make()
        _patch_time(sched, _snap("tuesday", "morning"))
        sched.tick(zone_id="national_park")
        assert sched.is_open("bug_catching_contest") is True

    def test_tick_does_not_open_wrong_zone(self):
        sched = self._make()
        _patch_time(sched, _snap("tuesday", "morning"))
        sched.tick(zone_id="some_other_zone")
        assert sched.is_open("bug_catching_contest") is False

    def test_tick_fires_open_hook(self):
        opened: list[WeeklyEventWindowPayload] = []
        hooks.on_weekly_event_window_open(opened.append)

        sched = self._make()
        _patch_time(sched, _snap("tuesday", "morning"))
        sched.tick(zone_id="national_park")

        assert len(opened) == 1
        assert opened[0].event_id == "bug_catching_contest"

    def test_tick_fires_close_hook_when_window_ends(self):
        closed: list[WeeklyEventWindowPayload] = []
        hooks.on_weekly_event_window_close(closed.append)

        sched = self._make()
        # Open the window on Tuesday morning
        _patch_time(sched, _snap("tuesday", "morning"))
        sched.tick(zone_id="national_park")

        # Advance to night — window should close
        _patch_time(sched, _snap("tuesday", "night"))
        sched.tick(zone_id="national_park")

        assert len(closed) == 1
        assert closed[0].event_id == "bug_catching_contest"
        assert sched.is_open("bug_catching_contest") is False

    def test_open_hook_fires_only_once_per_window(self):
        opened: list[WeeklyEventWindowPayload] = []
        hooks.on_weekly_event_window_open(opened.append)

        sched = self._make()
        _patch_time(sched, _snap("tuesday", "morning"))
        sched.tick(zone_id="national_park")
        sched.tick(zone_id="national_park")  # second tick in same window

        assert len(opened) == 1  # hook fired only once

    def test_event_without_map_fires_for_any_zone(self):
        cal = WeeklyEventCalendar(
            weekly_events=[
                WeeklyEventEntry(
                    id="global_event",
                    name_key="global_event_key",
                    days=["monday"],
                    time=["morning"],
                    # map intentionally left empty
                )
            ]
        )
        sched = _make_scheduler(cal)
        _patch_time(sched, _snap("monday", "morning"))
        sched.tick(zone_id="any_zone")
        assert sched.is_open("global_event") is True

    def test_is_open_false_for_unknown_event(self):
        sched = self._make()
        assert sched.is_open("nonexistent_event") is False

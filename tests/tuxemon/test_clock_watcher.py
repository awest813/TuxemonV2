# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for ClockWatcher — Hook 4.1 and Hook 4.2 integration.
"""

from __future__ import annotations

from datetime import date
from unittest.mock import MagicMock, patch

import pytest

from tuxemon.time_handler import TimeSnapshot
from tuxemon.time_hooks import (
    DayChangePayload,
    TimeSegmentChangePayload,
    hooks,
)
from tuxemon.world.clock_watcher import ClockWatcher


def _snap(stage_of_day: str, weekday: str = "monday") -> TimeSnapshot:
    return TimeSnapshot(
        hour=9,
        day_of_year=80,
        year=2026,
        month=3,
        day=1,
        weekday=weekday,
        leap_year="false",
        daytime="true",
        stage_of_day=stage_of_day,
        season="spring",
    )


@pytest.fixture(autouse=True)
def clear_hooks():
    hooks.clear()
    yield
    hooks.clear()


def _make_watcher(initial_segment: str = "morning") -> ClockWatcher:
    watcher = ClockWatcher.__new__(ClockWatcher)
    watcher._time_handler = MagicMock()
    watcher._time_handler.get_time_variables.return_value = _snap(
        initial_segment
    )
    watcher._last_segment = initial_segment
    watcher._last_date = date(2026, 3, 1)
    return watcher


class TestClockWatcherTimeSegment:
    def test_no_hook_fired_when_segment_unchanged(self):
        fired: list[TimeSegmentChangePayload] = []
        hooks.on_time_segment_change(fired.append)

        watcher = _make_watcher("morning")
        watcher._time_handler.get_time_variables.return_value = _snap(
            "morning"
        )
        with patch("tuxemon.world.clock_watcher.date") as mock_date:
            mock_date.today.return_value = date(2026, 3, 1)
            watcher.tick()

        assert fired == []

    def test_hook_fires_when_segment_changes(self):
        fired: list[TimeSegmentChangePayload] = []
        hooks.on_time_segment_change(fired.append)

        watcher = _make_watcher("morning")
        watcher._time_handler.get_time_variables.return_value = _snap(
            "afternoon"
        )
        with patch("tuxemon.world.clock_watcher.date") as mock_date:
            mock_date.today.return_value = date(2026, 3, 1)
            watcher.tick()

        assert len(fired) == 1
        assert fired[0].previous_segment == "morning"
        assert fired[0].new_segment == "afternoon"

    def test_last_segment_updated_after_change(self):
        watcher = _make_watcher("morning")
        watcher._time_handler.get_time_variables.return_value = _snap(
            "afternoon"
        )
        with patch("tuxemon.world.clock_watcher.date") as mock_date:
            mock_date.today.return_value = date(2026, 3, 1)
            watcher.tick()

        assert watcher._last_segment == "afternoon"

    def test_hook_fires_once_per_transition(self):
        fired: list[TimeSegmentChangePayload] = []
        hooks.on_time_segment_change(fired.append)

        watcher = _make_watcher("morning")
        watcher._time_handler.get_time_variables.return_value = _snap(
            "afternoon"
        )
        with patch("tuxemon.world.clock_watcher.date") as mock_date:
            mock_date.today.return_value = date(2026, 3, 1)
            watcher.tick()
            watcher.tick()  # second tick — segment unchanged now

        assert len(fired) == 1

    def test_multiple_segment_transitions(self):
        fired: list[TimeSegmentChangePayload] = []
        hooks.on_time_segment_change(fired.append)
        watcher = _make_watcher("morning")

        for new_seg in ["afternoon", "dusk", "night"]:
            watcher._time_handler.get_time_variables.return_value = _snap(
                new_seg
            )
            with patch("tuxemon.world.clock_watcher.date") as mock_date:
                mock_date.today.return_value = date(2026, 3, 1)
                watcher.tick()

        assert len(fired) == 3
        assert [p.new_segment for p in fired] == ["afternoon", "dusk", "night"]


class TestClockWatcherDayChange:
    def test_no_hook_fired_when_date_unchanged(self):
        fired: list[DayChangePayload] = []
        hooks.on_day_change(fired.append)

        watcher = _make_watcher("morning")
        watcher._time_handler.get_time_variables.return_value = _snap(
            "morning"
        )
        with patch("tuxemon.world.clock_watcher.date") as mock_date:
            mock_date.today.return_value = date(2026, 3, 1)
            watcher.tick()

        assert fired == []

    def test_hook_fires_when_date_changes(self):
        fired: list[DayChangePayload] = []
        hooks.on_day_change(fired.append)

        watcher = _make_watcher("morning")
        watcher._time_handler.get_time_variables.return_value = _snap(
            "morning", weekday="tuesday"
        )
        with patch("tuxemon.world.clock_watcher.date") as mock_date:
            mock_date.today.return_value = date(2026, 3, 2)
            watcher.tick()

        assert len(fired) == 1
        assert fired[0].previous_date == date(2026, 3, 1)
        assert fired[0].new_date == date(2026, 3, 2)
        assert fired[0].weekday == "tuesday"

    def test_last_date_updated_after_day_change(self):
        watcher = _make_watcher("morning")
        watcher._time_handler.get_time_variables.return_value = _snap(
            "morning"
        )
        with patch("tuxemon.world.clock_watcher.date") as mock_date:
            mock_date.today.return_value = date(2026, 3, 2)
            watcher.tick()

        assert watcher._last_date == date(2026, 3, 2)

    def test_both_segment_and_day_hooks_fire_together(self):
        seg_fired: list[TimeSegmentChangePayload] = []
        day_fired: list[DayChangePayload] = []
        hooks.on_time_segment_change(seg_fired.append)
        hooks.on_day_change(day_fired.append)

        watcher = _make_watcher("morning")
        watcher._time_handler.get_time_variables.return_value = _snap(
            "afternoon", weekday="tuesday"
        )
        with patch("tuxemon.world.clock_watcher.date") as mock_date:
            mock_date.today.return_value = date(2026, 3, 2)
            watcher.tick()

        assert len(seg_fired) == 1
        assert len(day_fired) == 1

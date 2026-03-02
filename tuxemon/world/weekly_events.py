# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Weekly event calendar schema and runtime manager.

Implements the calendar design described in
docs/gold_silver_blueprint.md §2.4.

YAML format example::

    weekly_events:
      - id: "bug_catching_contest"
        name_key: "event_bug_catching_contest"
        days: ["tuesday", "thursday", "saturday"]
        time: ["morning", "afternoon"]
        map: "national_park"
        trigger_script: "start_bug_contest"
        reward_script: "award_bug_contest"

      - id: "farmers_market"
        name_key: "event_farmers_market"
        days: ["sunday"]
        time: ["morning", "afternoon", "dusk"]
        map: "goldenrod_market_square"
        trigger_script: "open_farmers_market"
"""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator

from tuxemon.db import VALID_TIME_SEGMENTS, VALID_WEEKDAYS
from tuxemon.time_handler import TimeHandler
from tuxemon.time_hooks import WeeklyEventWindowPayload, hooks

logger = logging.getLogger(__name__)

_VALID_DAYS: frozenset[str] = VALID_WEEKDAYS
_VALID_TIMES: frozenset[str] = VALID_TIME_SEGMENTS


class WeeklyEventEntry(BaseModel):
    """
    Schema for a single entry in a mod's weekly event calendar.

    Each entry defines a recurring event that becomes active on specific
    weekdays and time segments, optionally associated with a map and
    controlled by trigger/reward scripts.
    """

    id: str = Field(
        ...,
        min_length=1,
        description="Stable identifier for this event (used in world-state tracking).",
    )
    name_key: str = Field(
        ...,
        min_length=1,
        description="Localisation key for the player-facing event name.",
    )
    days: list[str] = Field(
        ...,
        min_length=1,
        description="Weekdays on which this event is active (e.g. ['tuesday', 'saturday']).",
    )
    time: list[str] = Field(
        ...,
        min_length=1,
        description="Time segments during which this event is active (e.g. ['morning', 'afternoon']).",
    )
    map: str = Field(
        default="",
        description="Map slug where the event takes place (empty = world-wide).",
    )
    trigger_script: str = Field(
        default="",
        description="Event script called when the event window opens.",
    )
    reward_script: str = Field(
        default="",
        description="Event script called when the event window closes or the player completes it.",
    )

    @field_validator("days")
    def validate_days(cls, v: list[str]) -> list[str]:
        invalid = set(v) - _VALID_DAYS
        if invalid:
            raise ValueError(
                f"Invalid weekday(s): {invalid}. "
                f"Allowed: {sorted(_VALID_DAYS)}"
            )
        return v

    @field_validator("time")
    def validate_time(cls, v: list[str]) -> list[str]:
        invalid = set(v) - _VALID_TIMES
        if invalid:
            raise ValueError(
                f"Invalid time segment(s): {invalid}. "
                f"Allowed: {sorted(_VALID_TIMES)}"
            )
        return v

    def is_active_now(self, weekday: str, time_segment: str) -> bool:
        """Return True when this event should be running right now."""
        return weekday in self.days and time_segment in self.time


class WeeklyEventCalendar(BaseModel):
    """
    Container for all weekly events defined in a mod or campaign.

    Load from YAML::

        calendar = WeeklyEventCalendar.from_dict(yaml_data)

    The runtime manager (``WeeklyEventScheduler``) uses this schema to
    evaluate which events are open or closed at any moment.
    """

    weekly_events: list[WeeklyEventEntry] = Field(
        default_factory=list,
        description="All weekly event definitions for this mod/campaign.",
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> WeeklyEventCalendar:
        """Construct from a parsed YAML/JSON dictionary."""
        return cls(**data)

    def get_active_events(
        self, weekday: str, time_segment: str
    ) -> list[WeeklyEventEntry]:
        """Return all events that are currently active."""
        return [
            e
            for e in self.weekly_events
            if e.is_active_now(weekday, time_segment)
        ]

    def get_event(self, event_id: str) -> WeeklyEventEntry | None:
        """Look up an event by its stable identifier."""
        for event in self.weekly_events:
            if event.id == event_id:
                return event
        return None


class WeeklyEventScheduler:
    """
    Runtime manager that drives the weekly event calendar.

    Tracks which event windows are currently open, fires Hook 4.7
    (``on_weekly_event_window_open``) when a window opens and Hook 4.8
    (``on_weekly_event_window_close``) when it closes, and records fired
    events so they do not re-fire within the same window.

    Typical usage::

        scheduler = WeeklyEventScheduler(calendar)
        # call once per game loop / time-segment tick:
        scheduler.tick(zone_id="national_park")
    """

    def __init__(self, calendar: WeeklyEventCalendar) -> None:
        self.calendar = calendar
        self._open_events: set[str] = set()
        self._time_handler = TimeHandler()

    def tick(self, zone_id: str = "") -> None:
        """
        Evaluate the calendar against the current real-world time and fire
        open/close hooks for any events whose window state has changed.

        Parameters:
            zone_id: The map/zone the player is currently in.  Events with a
                non-empty ``map`` field only fire when ``zone_id`` matches.
        """
        snap = self._time_handler.get_time_variables()
        weekday = snap.weekday
        time_segment = snap.stage_of_day
        now = datetime.now()

        currently_active: set[str] = set()

        for event in self.calendar.weekly_events:
            if not event.is_active_now(weekday, time_segment):
                continue
            if event.map and event.map != zone_id:
                continue
            currently_active.add(event.id)

        newly_opened = currently_active - self._open_events
        newly_closed = self._open_events - currently_active

        for event_id in newly_opened:
            event = self.calendar.get_event(event_id)
            if event is None:
                continue
            payload = WeeklyEventWindowPayload(
                event_id=event_id,
                zone_id=zone_id,
                current_time=now,
                time_segment=time_segment,
                weekday=weekday,
            )
            hooks.fire_weekly_event_window_open(payload)
            logger.info("Weekly event window opened: %s", event_id)

        for event_id in newly_closed:
            payload = WeeklyEventWindowPayload(
                event_id=event_id,
                zone_id=zone_id,
                current_time=now,
                time_segment=time_segment,
                weekday=weekday,
            )
            hooks.fire_weekly_event_window_close(payload)
            logger.info("Weekly event window closed: %s", event_id)

        self._open_events = currently_active

    @property
    def open_event_ids(self) -> frozenset[str]:
        """Return the set of currently-open event IDs."""
        return frozenset(self._open_events)

    def is_open(self, event_id: str) -> bool:
        """Return True if *event_id*'s window is currently open."""
        return event_id in self._open_events

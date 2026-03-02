# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Real-world clock monitor for time-hook integration.

Watches for time-segment transitions (Hook 4.1) and day rollovers (Hook 4.2)
and fires the corresponding hooks via the module-level registry.

Designed to be ticked once per world-state update frame. Because real-world
time advances slowly the per-tick cost is trivial (two datetime comparisons).
"""
from __future__ import annotations

import logging
from datetime import date, datetime

from tuxemon.time_handler import TimeHandler
from tuxemon.time_hooks import DayChangePayload, TimeSegmentChangePayload, hooks

logger = logging.getLogger(__name__)


class ClockWatcher:
    """
    Monitor the real-world clock and fire Hook 4.1 and Hook 4.2.

    Hook 4.1 — ``on_time_segment_change`` — fires whenever the active time
    segment transitions (e.g. ``morning`` → ``afternoon``).

    Hook 4.2 — ``on_day_change`` — fires once at the first tick after
    midnight crosses into a new calendar date.

    Typical usage inside ``WorldState.update()``::

        self.clock_watcher.tick()
    """

    def __init__(self) -> None:
        self._time_handler = TimeHandler()
        snap = self._time_handler.get_time_variables()
        self._last_segment: str = snap.stage_of_day
        self._last_date: date = date.today()

    def tick(self) -> None:
        """
        Check for time-segment and day changes; fire hooks if either changed.

        Safe to call every frame — hooks only fire when the segment or date
        actually differs from the last observed value.
        """
        snap = self._time_handler.get_time_variables()
        now = datetime.now()
        today = date.today()

        if snap.stage_of_day != self._last_segment:
            logger.info(
                "Time segment changed: %s → %s",
                self._last_segment,
                snap.stage_of_day,
            )
            hooks.fire_time_segment_change(
                TimeSegmentChangePayload(
                    previous_segment=self._last_segment,
                    new_segment=snap.stage_of_day,
                    current_time=now,
                )
            )
            self._last_segment = snap.stage_of_day

        if today != self._last_date:
            logger.info(
                "Day changed: %s → %s (%s)",
                self._last_date,
                today,
                snap.weekday,
            )
            hooks.fire_day_change(
                DayChangePayload(
                    previous_date=self._last_date,
                    new_date=today,
                    weekday=snap.weekday,
                )
            )
            self._last_date = today

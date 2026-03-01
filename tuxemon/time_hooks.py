# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Engine hook interfaces for time-aware content.

These Protocol definitions specify the call signatures for each hook described
in docs/gold_silver_blueprint.md §4. Game-logic systems and content scripts
register concrete callables that match these protocols.

Hook registry:
  HookRegistry is the central object that content systems subscribe to and
  that the engine fires when events occur.

Usage::

    registry = HookRegistry()

    # Register a handler (e.g. from the encounter system):
    @registry.on_time_segment_change
    def _update_encounters(payload: TimeSegmentChangePayload) -> None:
        ...

    # Fire from the engine when time advances:
    registry.fire_time_segment_change(
        TimeSegmentChangePayload(
            previous_segment="morning",
            new_segment="afternoon",
            current_time=datetime.now(),
        )
    )
"""
from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Payload dataclasses — one per hook
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class TimeSegmentChangePayload:
    """Payload for on_time_segment_change (Hook 4.1)."""

    previous_segment: str
    new_segment: str
    current_time: datetime


@dataclass(frozen=True)
class DayChangePayload:
    """Payload for on_day_change (Hook 4.2)."""

    previous_date: date
    new_date: date
    weekday: str


@dataclass(frozen=True)
class MapZoneEnterPayload:
    """Payload for on_map_zone_enter (Hook 4.3)."""

    zone_id: str
    player_id: str
    current_time: datetime
    time_segment: str
    weekday: str
    season: str


@dataclass(frozen=True)
class EncounterTableQueryPayload:
    """
    Payload for on_encounter_table_query (Hook 4.4).

    Handlers receive this payload and return a (possibly filtered) encounter
    table. The engine uses the return value of the last registered handler,
    so handlers should be chained carefully — typically only one handler
    per zone performs the filtering.
    """

    zone_id: str
    current_time: datetime
    time_segment: str
    weekday: str
    season: str
    raw_encounter_table: list[dict]


@dataclass(frozen=True)
class TrainerDefeatedPayload:
    """Payload for on_trainer_defeated (Hook 4.5)."""

    trainer_id: str
    player_id: str
    timestamp: datetime


@dataclass(frozen=True)
class RematchEligiblePayload:
    """Payload for on_rematch_eligible (Hook 4.6)."""

    trainer_id: str
    player_id: str


@dataclass(frozen=True)
class WeeklyEventWindowPayload:
    """Payload for on_weekly_event_window_open and on_weekly_event_window_close (Hooks 4.7, 4.8)."""

    event_id: str
    zone_id: str
    current_time: datetime
    time_segment: str
    weekday: str


@dataclass(frozen=True)
class PostgameMilestonePayload:
    """Payload for on_postgame_milestone_reached (Hook 4.9)."""

    milestone_id: str
    player_id: str
    timestamp: datetime


# ---------------------------------------------------------------------------
# Protocol type aliases
# ---------------------------------------------------------------------------

TimeSegmentChangeHandler = Callable[[TimeSegmentChangePayload], None]
DayChangeHandler = Callable[[DayChangePayload], None]
MapZoneEnterHandler = Callable[[MapZoneEnterPayload], None]
EncounterTableQueryHandler = Callable[[EncounterTableQueryPayload], list[dict]]
TrainerDefeatedHandler = Callable[[TrainerDefeatedPayload], None]
RematchEligibleHandler = Callable[[RematchEligiblePayload], None]
WeeklyEventWindowHandler = Callable[[WeeklyEventWindowPayload], None]
PostgameMilestoneHandler = Callable[[PostgameMilestonePayload], None]


# ---------------------------------------------------------------------------
# Hook Registry
# ---------------------------------------------------------------------------


@dataclass
class HookRegistry:
    """
    Central registry for all time-aware content hooks.

    Systems that react to world-clock events (encounter tables, NPC schedulers,
    world-state gates) register handlers here. The engine fires hooks at the
    appropriate moments in the game loop.

    All handler lists are ordered; handlers fire in registration order.
    """

    _time_segment_change: list[TimeSegmentChangeHandler] = field(
        default_factory=list
    )
    _day_change: list[DayChangeHandler] = field(default_factory=list)
    _map_zone_enter: list[MapZoneEnterHandler] = field(default_factory=list)
    _encounter_table_query: list[EncounterTableQueryHandler] = field(
        default_factory=list
    )
    _trainer_defeated: list[TrainerDefeatedHandler] = field(default_factory=list)
    _rematch_eligible: list[RematchEligibleHandler] = field(default_factory=list)
    _weekly_event_window_open: list[WeeklyEventWindowHandler] = field(
        default_factory=list
    )
    _weekly_event_window_close: list[WeeklyEventWindowHandler] = field(
        default_factory=list
    )
    _postgame_milestone_reached: list[PostgameMilestoneHandler] = field(
        default_factory=list
    )

    # ------------------------------------------------------------------
    # Registration decorators / methods
    # ------------------------------------------------------------------

    def on_time_segment_change(
        self, fn: TimeSegmentChangeHandler
    ) -> TimeSegmentChangeHandler:
        """Register a handler for time-segment transitions (Hook 4.1)."""
        self._time_segment_change.append(fn)
        return fn

    def on_day_change(self, fn: DayChangeHandler) -> DayChangeHandler:
        """Register a handler for day transitions (Hook 4.2)."""
        self._day_change.append(fn)
        return fn

    def on_map_zone_enter(self, fn: MapZoneEnterHandler) -> MapZoneEnterHandler:
        """Register a handler for zone entry (Hook 4.3)."""
        self._map_zone_enter.append(fn)
        return fn

    def on_encounter_table_query(
        self, fn: EncounterTableQueryHandler
    ) -> EncounterTableQueryHandler:
        """
        Register an encounter table filter (Hook 4.4).

        Each registered handler receives the payload with the current table
        and returns a (possibly filtered) table. Handlers chain in
        registration order; each handler receives the output of the previous.
        """
        self._encounter_table_query.append(fn)
        return fn

    def on_trainer_defeated(
        self, fn: TrainerDefeatedHandler
    ) -> TrainerDefeatedHandler:
        """Register a handler for trainer defeat events (Hook 4.5)."""
        self._trainer_defeated.append(fn)
        return fn

    def on_rematch_eligible(
        self, fn: RematchEligibleHandler
    ) -> RematchEligibleHandler:
        """Register a handler for rematch eligibility transitions (Hook 4.6)."""
        self._rematch_eligible.append(fn)
        return fn

    def on_weekly_event_window_open(
        self, fn: WeeklyEventWindowHandler
    ) -> WeeklyEventWindowHandler:
        """Register a handler for weekly event window opens (Hook 4.7)."""
        self._weekly_event_window_open.append(fn)
        return fn

    def on_weekly_event_window_close(
        self, fn: WeeklyEventWindowHandler
    ) -> WeeklyEventWindowHandler:
        """Register a handler for weekly event window closes (Hook 4.8)."""
        self._weekly_event_window_close.append(fn)
        return fn

    def on_postgame_milestone_reached(
        self, fn: PostgameMilestoneHandler
    ) -> PostgameMilestoneHandler:
        """Register a handler for post-game milestone events (Hook 4.9)."""
        self._postgame_milestone_reached.append(fn)
        return fn

    # ------------------------------------------------------------------
    # Fire methods — called by the engine
    # ------------------------------------------------------------------

    def fire_time_segment_change(self, payload: TimeSegmentChangePayload) -> None:
        """Fire Hook 4.1."""
        for handler in self._time_segment_change:
            try:
                handler(payload)
            except Exception:
                logger.exception(
                    "time_segment_change handler %s raised an exception", handler
                )

    def fire_day_change(self, payload: DayChangePayload) -> None:
        """Fire Hook 4.2."""
        for handler in self._day_change:
            try:
                handler(payload)
            except Exception:
                logger.exception(
                    "day_change handler %s raised an exception", handler
                )

    def fire_map_zone_enter(self, payload: MapZoneEnterPayload) -> None:
        """Fire Hook 4.3."""
        for handler in self._map_zone_enter:
            try:
                handler(payload)
            except Exception:
                logger.exception(
                    "map_zone_enter handler %s raised an exception", handler
                )

    def fire_encounter_table_query(
        self, payload: EncounterTableQueryPayload
    ) -> list[dict]:
        """
        Fire Hook 4.4 and return the final filtered encounter table.

        Each handler receives a payload whose `raw_encounter_table` contains
        the table produced by the previous handler. The output of the last
        handler is returned.
        """
        current_table = list(payload.raw_encounter_table)
        for handler in self._encounter_table_query:
            try:
                filtered = handler(
                    EncounterTableQueryPayload(
                        zone_id=payload.zone_id,
                        current_time=payload.current_time,
                        time_segment=payload.time_segment,
                        weekday=payload.weekday,
                        season=payload.season,
                        raw_encounter_table=current_table,
                    )
                )
                current_table = filtered
            except Exception:
                logger.exception(
                    "encounter_table_query handler %s raised an exception", handler
                )
        return current_table

    def fire_trainer_defeated(self, payload: TrainerDefeatedPayload) -> None:
        """Fire Hook 4.5."""
        for handler in self._trainer_defeated:
            try:
                handler(payload)
            except Exception:
                logger.exception(
                    "trainer_defeated handler %s raised an exception", handler
                )

    def fire_rematch_eligible(self, payload: RematchEligiblePayload) -> None:
        """Fire Hook 4.6."""
        for handler in self._rematch_eligible:
            try:
                handler(payload)
            except Exception:
                logger.exception(
                    "rematch_eligible handler %s raised an exception", handler
                )

    def fire_weekly_event_window_open(
        self, payload: WeeklyEventWindowPayload
    ) -> None:
        """Fire Hook 4.7."""
        for handler in self._weekly_event_window_open:
            try:
                handler(payload)
            except Exception:
                logger.exception(
                    "weekly_event_window_open handler %s raised an exception",
                    handler,
                )

    def fire_weekly_event_window_close(
        self, payload: WeeklyEventWindowPayload
    ) -> None:
        """Fire Hook 4.8."""
        for handler in self._weekly_event_window_close:
            try:
                handler(payload)
            except Exception:
                logger.exception(
                    "weekly_event_window_close handler %s raised an exception",
                    handler,
                )

    def fire_postgame_milestone_reached(
        self, payload: PostgameMilestonePayload
    ) -> None:
        """Fire Hook 4.9."""
        for handler in self._postgame_milestone_reached:
            try:
                handler(payload)
            except Exception:
                logger.exception(
                    "postgame_milestone_reached handler %s raised an exception",
                    handler,
                )

    def clear(self) -> None:
        """Remove all registered handlers. Useful for test isolation."""
        self._time_segment_change.clear()
        self._day_change.clear()
        self._map_zone_enter.clear()
        self._encounter_table_query.clear()
        self._trainer_defeated.clear()
        self._rematch_eligible.clear()
        self._weekly_event_window_open.clear()
        self._weekly_event_window_close.clear()
        self._postgame_milestone_reached.clear()


# ---------------------------------------------------------------------------
# Shared module-level registry instance
# ---------------------------------------------------------------------------

#: Module-level registry used throughout the engine.
#: Systems import this directly to register handlers.
hooks: HookRegistry = HookRegistry()

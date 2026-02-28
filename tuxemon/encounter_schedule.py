# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Encounter schedule system for time-based encounter variation.

Applies time-of-day, weekday, and seasonal filters to encounter tables,
enabling different monster populations at different times.  Works alongside
the existing encounter variable conditions by providing a higher-level
scheduling API.
"""
from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

WEEKDAYS = {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
STAGES_OF_DAY = {"dawn", "morning", "afternoon", "dusk", "night"}
SEASONS = {"spring", "summer", "autumn", "winter"}


@dataclass
class EncounterScheduleFilter:
    """A time-based filter that determines whether an encounter is active."""

    daytime: bool | None = None
    weekdays: set[str] = field(default_factory=set)
    stages_of_day: set[str] = field(default_factory=set)
    seasons: set[str] = field(default_factory=set)

    def matches(
        self,
        *,
        daytime: str = "true",
        weekday: str = "",
        stage_of_day: str = "",
        season: str = "",
    ) -> bool:
        """Check if the current time snapshot matches this filter."""
        if self.daytime is not None:
            is_day = daytime == "true"
            if is_day != self.daytime:
                return False

        if self.weekdays and weekday.lower() not in self.weekdays:
            return False

        if self.stages_of_day and stage_of_day.lower() not in self.stages_of_day:
            return False

        if self.seasons and season.lower() not in self.seasons:
            return False

        return True

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        if self.daytime is not None:
            result["daytime"] = self.daytime
        if self.weekdays:
            result["weekdays"] = sorted(self.weekdays)
        if self.stages_of_day:
            result["stages_of_day"] = sorted(self.stages_of_day)
        if self.seasons:
            result["seasons"] = sorted(self.seasons)
        return result

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> EncounterScheduleFilter:
        daytime = data.get("daytime")
        weekdays_raw = data.get("weekdays", [])
        stages_raw = data.get("stages_of_day", [])
        seasons_raw = data.get("seasons", [])
        return cls(
            daytime=daytime if isinstance(daytime, bool) else None,
            weekdays={w.lower() for w in weekdays_raw if isinstance(w, str) and w.lower() in WEEKDAYS},
            stages_of_day={s.lower() for s in stages_raw if isinstance(s, str) and s.lower() in STAGES_OF_DAY},
            seasons={s.lower() for s in seasons_raw if isinstance(s, str) and s.lower() in SEASONS},
        )


@dataclass
class ScheduledEncounter:
    """An encounter entry with an optional time-based schedule filter."""

    monster_slug: str
    encounter_rate: float
    level_range: tuple[int, int]
    schedule: EncounterScheduleFilter = field(
        default_factory=EncounterScheduleFilter
    )

    def is_active(
        self,
        *,
        daytime: str = "true",
        weekday: str = "",
        stage_of_day: str = "",
        season: str = "",
    ) -> bool:
        return self.schedule.matches(
            daytime=daytime,
            weekday=weekday,
            stage_of_day=stage_of_day,
            season=season,
        )


class EncounterScheduleManager:
    """
    Manages scheduled encounters for a zone, filtering by time conditions.

    This sits alongside the existing EncounterManager and provides
    time-aware filtering for encounter tables.
    """

    def __init__(self) -> None:
        self._zones: dict[str, list[ScheduledEncounter]] = {}

    def register_zone(
        self, zone_slug: str, encounters: Sequence[ScheduledEncounter]
    ) -> None:
        self._zones[zone_slug] = list(encounters)

    def get_active_encounters(
        self,
        zone_slug: str,
        *,
        daytime: str = "true",
        weekday: str = "",
        stage_of_day: str = "",
        season: str = "",
    ) -> list[ScheduledEncounter]:
        """Return encounters active for the given time conditions."""
        zone = self._zones.get(zone_slug, [])
        return [
            enc
            for enc in zone
            if enc.is_active(
                daytime=daytime,
                weekday=weekday,
                stage_of_day=stage_of_day,
                season=season,
            )
        ]

    def get_all_zones(self) -> list[str]:
        return list(self._zones.keys())

    def get_zone_summary(
        self,
        zone_slug: str,
        *,
        daytime: str = "true",
        weekday: str = "",
        stage_of_day: str = "",
        season: str = "",
    ) -> dict[str, Any]:
        """Return a summary of encounter availability for a zone."""
        all_encounters = self._zones.get(zone_slug, [])
        active = self.get_active_encounters(
            zone_slug,
            daytime=daytime,
            weekday=weekday,
            stage_of_day=stage_of_day,
            season=season,
        )
        return {
            "zone": zone_slug,
            "total_encounters": len(all_encounters),
            "active_encounters": len(active),
            "active_monsters": [e.monster_slug for e in active],
        }

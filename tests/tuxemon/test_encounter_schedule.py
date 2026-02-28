# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""Tests for the encounter schedule system."""
from __future__ import annotations

import pytest

from tuxemon.encounter_schedule import (
    EncounterScheduleFilter,
    EncounterScheduleManager,
    ScheduledEncounter,
)


class TestEncounterScheduleFilter:
    def test_empty_filter_matches_everything(self):
        f = EncounterScheduleFilter()
        assert f.matches(daytime="true", weekday="monday") is True
        assert f.matches(daytime="false", weekday="friday") is True

    def test_daytime_filter(self):
        day = EncounterScheduleFilter(daytime=True)
        assert day.matches(daytime="true") is True
        assert day.matches(daytime="false") is False

        night = EncounterScheduleFilter(daytime=False)
        assert night.matches(daytime="false") is True
        assert night.matches(daytime="true") is False

    def test_weekday_filter(self):
        f = EncounterScheduleFilter(weekdays={"monday", "wednesday", "friday"})
        assert f.matches(weekday="monday") is True
        assert f.matches(weekday="tuesday") is False
        assert f.matches(weekday="friday") is True

    def test_stage_of_day_filter(self):
        f = EncounterScheduleFilter(stages_of_day={"dawn", "dusk"})
        assert f.matches(stage_of_day="dawn") is True
        assert f.matches(stage_of_day="morning") is False
        assert f.matches(stage_of_day="dusk") is True

    def test_season_filter(self):
        f = EncounterScheduleFilter(seasons={"winter", "autumn"})
        assert f.matches(season="winter") is True
        assert f.matches(season="summer") is False

    def test_combined_filters(self):
        f = EncounterScheduleFilter(
            daytime=True, weekdays={"saturday", "sunday"}, seasons={"summer"}
        )
        assert f.matches(
            daytime="true", weekday="saturday", season="summer"
        ) is True
        assert f.matches(
            daytime="false", weekday="saturday", season="summer"
        ) is False
        assert f.matches(
            daytime="true", weekday="monday", season="summer"
        ) is False
        assert f.matches(
            daytime="true", weekday="saturday", season="winter"
        ) is False

    def test_roundtrip_serialization(self):
        f = EncounterScheduleFilter(
            daytime=True,
            weekdays={"monday", "friday"},
            stages_of_day={"morning"},
            seasons={"spring"},
        )
        data = f.to_dict()
        restored = EncounterScheduleFilter.from_dict(data)
        assert restored.daytime is True
        assert restored.weekdays == {"monday", "friday"}
        assert restored.stages_of_day == {"morning"}
        assert restored.seasons == {"spring"}

    def test_from_dict_filters_invalid_values(self):
        f = EncounterScheduleFilter.from_dict({
            "weekdays": ["monday", "invalid_day", "friday"],
            "seasons": ["winter", "fake_season"],
        })
        assert f.weekdays == {"monday", "friday"}
        assert f.seasons == {"winter"}


class TestScheduledEncounter:
    def test_always_active_by_default(self):
        enc = ScheduledEncounter(
            monster_slug="alpha", encounter_rate=5.0, level_range=(5, 10)
        )
        assert enc.is_active() is True
        assert enc.is_active(daytime="false", weekday="sunday") is True

    def test_daytime_restricted(self):
        enc = ScheduledEncounter(
            monster_slug="alpha",
            encounter_rate=5.0,
            level_range=(5, 10),
            schedule=EncounterScheduleFilter(daytime=True),
        )
        assert enc.is_active(daytime="true") is True
        assert enc.is_active(daytime="false") is False

    def test_weekday_restricted(self):
        enc = ScheduledEncounter(
            monster_slug="beta",
            encounter_rate=3.0,
            level_range=(10, 15),
            schedule=EncounterScheduleFilter(weekdays={"wednesday"}),
        )
        assert enc.is_active(weekday="wednesday") is True
        assert enc.is_active(weekday="thursday") is False


class TestEncounterScheduleManager:
    def test_register_and_query_zone(self):
        mgr = EncounterScheduleManager()
        encounters = [
            ScheduledEncounter("alpha", 5.0, (5, 10)),
            ScheduledEncounter("beta", 3.0, (8, 12)),
        ]
        mgr.register_zone("route1", encounters)

        active = mgr.get_active_encounters("route1")
        assert len(active) == 2

    def test_time_filtering(self):
        mgr = EncounterScheduleManager()
        encounters = [
            ScheduledEncounter(
                "day_mon", 5.0, (5, 10),
                schedule=EncounterScheduleFilter(daytime=True),
            ),
            ScheduledEncounter(
                "night_mon", 3.0, (5, 10),
                schedule=EncounterScheduleFilter(daytime=False),
            ),
            ScheduledEncounter("any_mon", 4.0, (5, 10)),
        ]
        mgr.register_zone("route1", encounters)

        day_active = mgr.get_active_encounters("route1", daytime="true")
        assert len(day_active) == 2
        slugs = {e.monster_slug for e in day_active}
        assert "day_mon" in slugs
        assert "any_mon" in slugs

        night_active = mgr.get_active_encounters("route1", daytime="false")
        assert len(night_active) == 2
        slugs = {e.monster_slug for e in night_active}
        assert "night_mon" in slugs
        assert "any_mon" in slugs

    def test_weekday_filtering(self):
        mgr = EncounterScheduleManager()
        encounters = [
            ScheduledEncounter(
                "weekend_mon", 8.0, (10, 20),
                schedule=EncounterScheduleFilter(weekdays={"saturday", "sunday"}),
            ),
            ScheduledEncounter("always_mon", 5.0, (5, 10)),
        ]
        mgr.register_zone("route2", encounters)

        weekday = mgr.get_active_encounters("route2", weekday="monday")
        assert len(weekday) == 1
        assert weekday[0].monster_slug == "always_mon"

        weekend = mgr.get_active_encounters("route2", weekday="saturday")
        assert len(weekend) == 2

    def test_season_filtering(self):
        mgr = EncounterScheduleManager()
        encounters = [
            ScheduledEncounter(
                "winter_mon", 6.0, (15, 25),
                schedule=EncounterScheduleFilter(seasons={"winter"}),
            ),
            ScheduledEncounter("always_mon", 5.0, (5, 10)),
        ]
        mgr.register_zone("route3", encounters)

        summer = mgr.get_active_encounters("route3", season="summer")
        assert len(summer) == 1

        winter = mgr.get_active_encounters("route3", season="winter")
        assert len(winter) == 2

    def test_empty_zone(self):
        mgr = EncounterScheduleManager()
        active = mgr.get_active_encounters("nonexistent")
        assert active == []

    def test_zone_summary(self):
        mgr = EncounterScheduleManager()
        encounters = [
            ScheduledEncounter(
                "day_mon", 5.0, (5, 10),
                schedule=EncounterScheduleFilter(daytime=True),
            ),
            ScheduledEncounter("any_mon", 4.0, (5, 10)),
        ]
        mgr.register_zone("route1", encounters)

        summary = mgr.get_zone_summary("route1", daytime="true")
        assert summary["total_encounters"] == 2
        assert summary["active_encounters"] == 2

        summary = mgr.get_zone_summary("route1", daytime="false")
        assert summary["active_encounters"] == 1

    def test_get_all_zones(self):
        mgr = EncounterScheduleManager()
        mgr.register_zone("route1", [])
        mgr.register_zone("route2", [])
        assert sorted(mgr.get_all_zones()) == ["route1", "route2"]

# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import random

import pytest

from tuxemon.db import EncounterType
from tuxemon.encounter import Encounter, EncounterResult, HordeEncounterResult
from tuxemon.time_handler import TimeSnapshot


class DummyNPC:
    def __init__(self, avg_level=5, variables=None):
        self.party = type("Party", (), {"level_average": avg_level})
        self.game_variables = variables or {}


class DummyEncounterData:
    """Minimal stub for EncounterData that avoids DB lookups."""

    def __init__(self, slug="test-zone"):
        self.slug = slug
        self.encounter_type = EncounterType.SINGLE
        self.encounters = []
        self.horde = None
        self.scaling_zone = False
        self.override_level_range = None
        self.scale_offset_range = None
        self.scale_multiplier = 1.0

    def get_encounters(self):
        return self.encounters


class DummyEncounterItem:
    def __init__(
        self,
        monster="agnite",
        rate=100,
        level_range=(1, 5),
        held_items=None,
        scaling_enabled=False,
        time_restrictions=None,
        season_restrictions=None,
        weekday_restrictions=None,
    ):
        self.monster = monster
        self.encounter_rate = rate
        self.level_range = level_range
        self.level_offset_range = None
        self.level_offset = 0
        self.held_items = held_items or []
        self.scaling_enabled = scaling_enabled
        self.min_player_level = None
        self.max_player_level = None
        self.variables = []
        self.override_level_range = None
        self.scaling_offset_range = None
        self.time_restrictions = time_restrictions or []
        self.season_restrictions = season_restrictions or []
        self.weekday_restrictions = weekday_restrictions or []


class DummyHeldItem:
    def __init__(self, slug="potion", prob=100):
        self.item_slug = slug
        self.probability = prob


@pytest.mark.parametrize(
    "roll_value, expected",
    [
        (0, True),  # encounter succeeds
        (200, False),  # encounter fails
    ],
)
def test_probability_gate(monkeypatch, roll_value, expected):
    zone = DummyEncounterData()
    zone.encounters = [
        DummyEncounterItem(monster="agnite", rate=100, level_range=(1, 5))
    ]
    enc = Encounter(zone)

    monkeypatch.setattr(random, "uniform", lambda a, b: roll_value)
    monkeypatch.setattr(random, "choices", lambda seq, weights, k: [seq[0]])

    npc = DummyNPC()
    result = enc.get_single_encounter(npc, total_prob=100)
    assert (result is not None) == expected


def test_weighted_monster_selection(monkeypatch):
    zone = DummyEncounterData()
    agnite = DummyEncounterItem(monster="agnite", rate=10, level_range=(1, 5))
    pairagrin = DummyEncounterItem(
        monster="pairagrin", rate=90, level_range=(1, 5)
    )
    zone.encounters = [agnite, pairagrin]
    enc = Encounter(zone)

    monkeypatch.setattr(random, "uniform", lambda a, b: 0)
    monkeypatch.setattr(
        random,
        "choices",
        lambda seq, weights, k: [seq[weights.index(max(weights))]],
    )

    npc = DummyNPC()
    result = enc.get_single_encounter(npc, total_prob=100)
    assert result.monster.monster == "pairagrin"


def test_level_scaling(monkeypatch):
    zone = DummyEncounterData()
    zone.scaling_zone = True
    item = DummyEncounterItem(
        monster="rockitten",
        rate=100,
        level_range=(1, 10),
        scaling_enabled=True,
    )
    zone.encounters = [item]
    enc = Encounter(zone)

    monkeypatch.setattr(random, "uniform", lambda a, b: 0)
    monkeypatch.setattr(random, "choices", lambda seq, weights, k: [seq[0]])
    monkeypatch.setattr(random, "randint", lambda a, b: a)

    npc = DummyNPC(avg_level=10)
    result = enc.get_single_encounter(npc, total_prob=100)
    assert isinstance(result, EncounterResult)
    assert result.monster.monster == "rockitten"
    assert result.level >= 1


def test_held_item_selection(monkeypatch):
    zone = DummyEncounterData()
    item = DummyEncounterItem(
        monster="rat",
        rate=100,
        level_range=(1, 5),
        held_items=[DummyHeldItem("potion", 100)],
    )
    zone.encounters = [item]
    enc = Encounter(zone)

    monkeypatch.setattr(random, "uniform", lambda a, b: 0)
    monkeypatch.setattr(random, "choices", lambda seq, weights, k: [seq[0]])

    npc = DummyNPC()
    result = enc.get_single_encounter(npc, total_prob=100)
    assert isinstance(result, EncounterResult)
    assert result.held_item == "potion"


def test_horde_encounter(monkeypatch):
    zone = DummyEncounterData()
    zone.encounter_type = EncounterType.HORDE
    zone.horde = type(
        "HordeModel",
        (),
        {
            "monsters": [
                DummyEncounterItem(
                    monster="rockitten", rate=100, level_range=(1, 5)
                ),
                DummyEncounterItem(
                    monster="pairagrin", rate=100, level_range=(1, 5)
                ),
            ],
            "horde_level_range": None,
            "horde_exp_mod": None,
        },
    )()
    enc = Encounter(zone)

    monkeypatch.setattr(random, "uniform", lambda a, b: 0)
    monkeypatch.setattr(random, "randint", lambda a, b: a)

    npc = DummyNPC(avg_level=5)
    result = enc.get_horde_encounter(npc, total_prob=100)
    assert isinstance(result, HordeEncounterResult)
    assert len(result.monsters) == 2
    assert {r.monster.monster for r in result.monsters} == {
        "rockitten",
        "pairagrin",
    }
    assert result.horde_exp_mod is None


# ---------------------------------------------------------------------------
# Time / season / weekday restriction tests
# ---------------------------------------------------------------------------


def _make_snapshot(
    stage_of_day="morning", season="spring", weekday="monday"
) -> TimeSnapshot:
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
        season=season,
    )


def _patch_time(monkeypatch, snapshot: TimeSnapshot):
    """Patch _time_handler.get_time_variables() inside encounter module."""
    import tuxemon.encounter as enc_module

    monkeypatch.setattr(
        enc_module._time_handler, "get_time_variables", lambda: snapshot
    )


def test_no_restrictions_always_valid(monkeypatch):
    """An encounter entry with no restrictions passes at any time."""
    _patch_time(monkeypatch, _make_snapshot("night", "winter", "sunday"))
    monkeypatch.setattr(random, "uniform", lambda a, b: 0)
    monkeypatch.setattr(random, "choices", lambda seq, weights, k: [seq[0]])

    zone = DummyEncounterData()
    zone.encounters = [DummyEncounterItem(monster="agnite", rate=100)]
    enc = Encounter(zone)

    npc = DummyNPC()
    result = enc.get_single_encounter(npc, total_prob=100)
    assert result is not None
    assert result.monster.monster == "agnite"


def test_time_restriction_blocks_wrong_segment(monkeypatch):
    """An encounter restricted to 'night' is excluded during 'morning'."""
    _patch_time(monkeypatch, _make_snapshot("morning", "spring", "monday"))
    monkeypatch.setattr(random, "uniform", lambda a, b: 0)
    monkeypatch.setattr(random, "choices", lambda seq, weights, k: [seq[0]])

    zone = DummyEncounterData()
    zone.encounters = [
        DummyEncounterItem(
            monster="nightbat",
            rate=100,
            time_restrictions=["night"],
        )
    ]
    enc = Encounter(zone)
    npc = DummyNPC()
    result = enc.get_single_encounter(npc, total_prob=100)
    assert result is None


def test_time_restriction_allows_correct_segment(monkeypatch):
    """An encounter restricted to 'night' is included during 'night'."""
    _patch_time(monkeypatch, _make_snapshot("night", "spring", "monday"))
    monkeypatch.setattr(random, "uniform", lambda a, b: 0)
    monkeypatch.setattr(random, "choices", lambda seq, weights, k: [seq[0]])

    zone = DummyEncounterData()
    zone.encounters = [
        DummyEncounterItem(
            monster="nightbat",
            rate=100,
            time_restrictions=["night"],
        )
    ]
    enc = Encounter(zone)
    npc = DummyNPC()
    result = enc.get_single_encounter(npc, total_prob=100)
    assert result is not None
    assert result.monster.monster == "nightbat"


def test_season_restriction_blocks_wrong_season(monkeypatch):
    """An encounter restricted to 'winter' is excluded in 'summer'."""
    _patch_time(monkeypatch, _make_snapshot("morning", "summer", "monday"))
    monkeypatch.setattr(random, "uniform", lambda a, b: 0)
    monkeypatch.setattr(random, "choices", lambda seq, weights, k: [seq[0]])

    zone = DummyEncounterData()
    zone.encounters = [
        DummyEncounterItem(
            monster="snowfox",
            rate=100,
            season_restrictions=["winter"],
        )
    ]
    enc = Encounter(zone)
    npc = DummyNPC()
    result = enc.get_single_encounter(npc, total_prob=100)
    assert result is None


def test_season_restriction_allows_correct_season(monkeypatch):
    """An encounter restricted to 'winter' appears in 'winter'."""
    _patch_time(monkeypatch, _make_snapshot("morning", "winter", "monday"))
    monkeypatch.setattr(random, "uniform", lambda a, b: 0)
    monkeypatch.setattr(random, "choices", lambda seq, weights, k: [seq[0]])

    zone = DummyEncounterData()
    zone.encounters = [
        DummyEncounterItem(
            monster="snowfox",
            rate=100,
            season_restrictions=["winter"],
        )
    ]
    enc = Encounter(zone)
    npc = DummyNPC()
    result = enc.get_single_encounter(npc, total_prob=100)
    assert result is not None


def test_weekday_restriction_blocks_wrong_day(monkeypatch):
    """An encounter restricted to 'friday'/'saturday' is excluded on 'monday'."""
    _patch_time(monkeypatch, _make_snapshot("morning", "spring", "monday"))
    monkeypatch.setattr(random, "uniform", lambda a, b: 0)
    monkeypatch.setattr(random, "choices", lambda seq, weights, k: [seq[0]])

    zone = DummyEncounterData()
    zone.encounters = [
        DummyEncounterItem(
            monster="weekendbug",
            rate=100,
            weekday_restrictions=["friday", "saturday"],
        )
    ]
    enc = Encounter(zone)
    npc = DummyNPC()
    result = enc.get_single_encounter(npc, total_prob=100)
    assert result is None


def test_weekday_restriction_allows_correct_day(monkeypatch):
    """An encounter restricted to 'friday'/'saturday' appears on 'friday'."""
    _patch_time(monkeypatch, _make_snapshot("morning", "spring", "friday"))
    monkeypatch.setattr(random, "uniform", lambda a, b: 0)
    monkeypatch.setattr(random, "choices", lambda seq, weights, k: [seq[0]])

    zone = DummyEncounterData()
    zone.encounters = [
        DummyEncounterItem(
            monster="weekendbug",
            rate=100,
            weekday_restrictions=["friday", "saturday"],
        )
    ]
    enc = Encounter(zone)
    npc = DummyNPC()
    result = enc.get_single_encounter(npc, total_prob=100)
    assert result is not None


def test_combined_restrictions_all_must_pass(monkeypatch):
    """All three restriction types must pass simultaneously."""
    _patch_time(monkeypatch, _make_snapshot("night", "winter", "friday"))
    monkeypatch.setattr(random, "uniform", lambda a, b: 0)
    monkeypatch.setattr(random, "choices", lambda seq, weights, k: [seq[0]])

    zone = DummyEncounterData()
    zone.encounters = [
        DummyEncounterItem(
            monster="rare_one",
            rate=100,
            time_restrictions=["night"],
            season_restrictions=["winter"],
            weekday_restrictions=["friday"],
        )
    ]
    enc = Encounter(zone)
    npc = DummyNPC()
    result = enc.get_single_encounter(npc, total_prob=100)
    assert result is not None


def test_combined_restrictions_partial_fail(monkeypatch):
    """If any restriction fails, the encounter is excluded."""
    _patch_time(monkeypatch, _make_snapshot("night", "summer", "friday"))
    monkeypatch.setattr(random, "uniform", lambda a, b: 0)
    monkeypatch.setattr(random, "choices", lambda seq, weights, k: [seq[0]])

    zone = DummyEncounterData()
    zone.encounters = [
        DummyEncounterItem(
            monster="rare_one",
            rate=100,
            time_restrictions=["night"],
            season_restrictions=["winter"],  # fails — it's summer
            weekday_restrictions=["friday"],
        )
    ]
    enc = Encounter(zone)
    npc = DummyNPC()
    result = enc.get_single_encounter(npc, total_prob=100)
    assert result is None


def test_unrestricted_and_restricted_coexist(monkeypatch):
    """Unrestricted entries remain when time-restricted ones are filtered out."""
    _patch_time(monkeypatch, _make_snapshot("morning", "spring", "monday"))
    monkeypatch.setattr(random, "uniform", lambda a, b: 0)
    monkeypatch.setattr(random, "choices", lambda seq, weights, k: [seq[0]])

    zone = DummyEncounterData()
    zone.encounters = [
        DummyEncounterItem(monster="daybug", rate=90),  # no restrictions
        DummyEncounterItem(
            monster="nightbat", rate=10, time_restrictions=["night"]
        ),
    ]
    enc = Encounter(zone)
    npc = DummyNPC()
    result = enc.get_single_encounter(npc, total_prob=100)
    assert result is not None
    assert result.monster.monster == "daybug"


def test_horde_time_filter(monkeypatch):
    """Time-restricted monsters are excluded from horde encounters too."""
    _patch_time(monkeypatch, _make_snapshot("morning", "spring", "monday"))
    monkeypatch.setattr(random, "uniform", lambda a, b: 0)
    monkeypatch.setattr(random, "randint", lambda a, b: a)

    zone = DummyEncounterData()
    zone.encounter_type = EncounterType.HORDE
    zone.horde = type(
        "HordeModel",
        (),
        {
            "monsters": [
                DummyEncounterItem(monster="daybug", rate=100),
                DummyEncounterItem(
                    monster="nightbat",
                    rate=100,
                    time_restrictions=["night"],
                ),
            ],
            "horde_level_range": None,
            "horde_exp_mod": None,
        },
    )()
    enc = Encounter(zone)
    npc = DummyNPC()
    result = enc.get_horde_encounter(npc, total_prob=100)
    assert isinstance(result, HordeEncounterResult)
    slugs = {r.monster.monster for r in result.monsters}
    assert "daybug" in slugs
    assert "nightbat" not in slugs

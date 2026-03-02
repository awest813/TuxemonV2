# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for tuxemon.campaign.encounter_editor — EncounterTable, EncounterZone,
and EncounterTableBuilder.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from tuxemon.campaign.encounter_editor import (
    EncounterTable,
    EncounterTableBuilder,
    EncounterZone,
)
from tuxemon.campaign.models import EncounterEntry


class TestEncounterZone:
    def test_valid_zone(self):
        entry = EncounterEntry(monster_id="porcupinito", weight=10, level_min=3, level_max=7)
        zone = EncounterZone(zone_id="route_1_grass", entries=[entry])
        assert zone.zone_id == "route_1_grass"
        assert zone.total_weight() == 10

    def test_empty_entries_raises(self):
        with pytest.raises(ValidationError):
            EncounterZone(zone_id="empty_zone", entries=[])

    def test_invalid_time_slot(self):
        with pytest.raises(ValidationError):
            EncounterZone(
                zone_id="z",
                entries=[EncounterEntry(monster_id="m")],
                active_time_slots=["lunchtime"],
            )

    def test_valid_time_slots(self):
        zone = EncounterZone(
            zone_id="z",
            entries=[EncounterEntry(monster_id="m")],
            active_time_slots=["dawn", "morning", "night"],
        )
        assert "dawn" in zone.active_time_slots

    def test_invalid_season(self):
        with pytest.raises(ValidationError):
            EncounterZone(
                zone_id="z",
                entries=[EncounterEntry(monster_id="m")],
                active_seasons=["monsoon"],
            )

    def test_valid_seasons(self):
        zone = EncounterZone(
            zone_id="z",
            entries=[EncounterEntry(monster_id="m")],
            active_seasons=["spring", "winter"],
        )
        assert "spring" in zone.active_seasons

    def test_monster_ids_deduplicated(self):
        zone = EncounterZone(
            zone_id="z",
            entries=[
                EncounterEntry(monster_id="porcupinito"),
                EncounterEntry(monster_id="porcupinito"),
                EncounterEntry(monster_id="iguana_evo"),
            ],
        )
        mids = zone.monster_ids()
        assert mids.count("porcupinito") == 1
        assert "iguana_evo" in mids

    def test_total_weight(self):
        zone = EncounterZone(
            zone_id="z",
            entries=[
                EncounterEntry(monster_id="a", weight=5),
                EncounterEntry(monster_id="b", weight=15),
            ],
        )
        assert zone.total_weight() == 20

    def test_suggested_level_field(self):
        zone = EncounterZone(
            zone_id="z",
            suggested_level=10,
            entries=[EncounterEntry(monster_id="m")],
        )
        assert zone.suggested_level == 10


class TestEncounterTable:
    def _valid_table(self, map_id: str = "route_1") -> EncounterTable:
        return EncounterTable(
            map_id=map_id,
            zones=[
                EncounterZone(
                    zone_id="grass",
                    entries=[EncounterEntry(monster_id="porcupinito")],
                )
            ],
        )

    def test_valid_table(self):
        table = self._valid_table()
        assert table.map_id == "route_1"
        assert len(table.zones) == 1

    def test_duplicate_zone_id_raises(self):
        entry = EncounterEntry(monster_id="m")
        with pytest.raises(ValidationError):
            EncounterTable(
                map_id="route_1",
                zones=[
                    EncounterZone(zone_id="zone_a", entries=[entry]),
                    EncounterZone(zone_id="zone_a", entries=[entry]),
                ],
            )

    def test_get_zone_by_id(self):
        table = self._valid_table()
        zone = table.get_zone("grass")
        assert zone is not None
        assert zone.zone_id == "grass"

    def test_get_zone_missing(self):
        table = self._valid_table()
        assert table.get_zone("no_such_zone") is None

    def test_all_monster_ids(self):
        table = EncounterTable(
            map_id="route_1",
            zones=[
                EncounterZone(
                    zone_id="zone_a",
                    entries=[
                        EncounterEntry(monster_id="porcupinito"),
                        EncounterEntry(monster_id="iguana_evo"),
                    ],
                ),
                EncounterZone(
                    zone_id="zone_b",
                    entries=[
                        EncounterEntry(monster_id="porcupinito"),
                        EncounterEntry(monster_id="drakovex"),
                    ],
                ),
            ],
        )
        mids = table.all_monster_ids()
        assert "porcupinito" in mids
        assert "iguana_evo" in mids
        assert "drakovex" in mids
        assert mids.count("porcupinito") == 1

    def test_yaml_round_trip(self):
        table = self._valid_table()
        yaml_str = table.to_yaml()
        table2 = EncounterTable.from_yaml(yaml_str)
        assert table2.map_id == table.map_id
        assert len(table2.zones) == len(table.zones)

    def test_save_and_load_from_file(self, tmp_path):
        table = self._valid_table("saved_route")
        saved = table.save(tmp_path, "saved_route")
        assert saved.exists()
        assert saved.name == "saved_route.encounters.yaml"
        loaded = EncounterTable.from_file(saved)
        assert loaded.map_id == "saved_route"

    def test_empty_zones_list(self):
        table = EncounterTable(map_id="empty_map")
        assert table.all_monster_ids() == []


class TestEncounterTableBuilder:
    def test_basic_builder(self):
        table = (
            EncounterTableBuilder("route_1")
            .zone("grass", suggested_level=5)
            .add("porcupinito", weight=10, level_min=3, level_max=7)
            .build()
        )
        assert table.map_id == "route_1"
        assert len(table.zones) == 1
        assert table.zones[0].zone_id == "grass"
        assert len(table.zones[0].entries) == 1

    def test_multiple_zones(self):
        table = (
            EncounterTableBuilder("route_2")
            .zone("grass")
            .add("porcupinito")
            .zone("water")
            .add("aquazor")
            .build()
        )
        assert len(table.zones) == 2
        assert table.zones[0].zone_id == "grass"
        assert table.zones[1].zone_id == "water"

    def test_multiple_entries_per_zone(self):
        table = (
            EncounterTableBuilder("route_3")
            .zone("mixed")
            .add("porcupinito", weight=10)
            .add("iguana_evo", weight=5)
            .build()
        )
        assert len(table.zones[0].entries) == 2
        assert table.zones[0].total_weight() == 15

    def test_time_restricted_entries(self):
        table = (
            EncounterTableBuilder("route_4")
            .zone("day_zone")
            .add("porcupinito", time_restrictions=["morning", "afternoon"])
            .build()
        )
        entry = table.zones[0].entries[0]
        assert "morning" in entry.time_restrictions

    def test_add_without_zone_raises(self):
        with pytest.raises(RuntimeError, match="Call .zone()"):
            EncounterTableBuilder("route_5").add("porcupinito")

    def test_builder_produces_encounter_table(self):
        table = (
            EncounterTableBuilder("route_6")
            .zone("z")
            .add("m")
            .build()
        )
        assert isinstance(table, EncounterTable)

    def test_zone_with_time_slot_restriction(self):
        table = (
            EncounterTableBuilder("route_7")
            .zone("night_zone", active_time_slots=["night", "dusk"])
            .add("noctulite")
            .build()
        )
        assert "night" in table.zones[0].active_time_slots

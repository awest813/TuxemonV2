# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Encounter table editor data model.

Implements the encounter table editing workflow described in
docs/campaign_maker_mvp.md §3 Workflow B.

The encounter editor provides:
- A schema for zone encounter tables (EncounterZone / EncounterTable).
- YAML serialization for storing encounter tables alongside maps.
- A validation layer that integrates with CampaignManifest constraints.
- A fluent builder for constructing encounter tables programmatically.

Encounter tables are stored as YAML files in the campaign's maps/ directory,
co-located with the .tmx files they reference.

File convention: ``<campaign_root>/maps/<map_stem>.encounters.yaml``
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Optional

import yaml
from pydantic import BaseModel, Field, field_validator, model_validator

from tuxemon.campaign.models import (
    VALID_SEASON_TOKENS,
    VALID_TIME_RESTRICTION_TOKENS,
    VALID_WEEKDAY_TOKENS,
    EncounterEntry,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Encounter zone
# ---------------------------------------------------------------------------


class EncounterZone(BaseModel):
    """
    A single encounter zone within a map.

    Each zone groups a set of monster encounter entries and can apply
    time, season, and weekday restrictions to the whole zone.
    """

    zone_id: str = Field(..., min_length=1, max_length=64)
    description: str = ""
    suggested_level: Optional[int] = Field(default=None, ge=1, le=100)
    entries: list[EncounterEntry] = Field(default_factory=list)
    active_time_slots: list[str] = Field(default_factory=list)
    active_seasons: list[str] = Field(default_factory=list)
    active_weekdays: list[str] = Field(default_factory=list)

    @field_validator("active_time_slots", mode="before")
    @classmethod
    def _validate_time_slots(cls, v: list[str]) -> list[str]:
        for token in v:
            if token not in VALID_TIME_RESTRICTION_TOKENS:
                raise ValueError(
                    f"Invalid time slot token: '{token}'. "
                    f"Must be one of: {sorted(VALID_TIME_RESTRICTION_TOKENS)}"
                )
        return v

    @field_validator("active_seasons", mode="before")
    @classmethod
    def _validate_seasons(cls, v: list[str]) -> list[str]:
        for token in v:
            if token not in VALID_SEASON_TOKENS:
                raise ValueError(
                    f"Invalid season token: '{token}'. "
                    f"Must be one of: {sorted(VALID_SEASON_TOKENS)}"
                )
        return v

    @field_validator("active_weekdays", mode="before")
    @classmethod
    def _validate_weekdays(cls, v: list[str]) -> list[str]:
        for token in v:
            if token not in VALID_WEEKDAY_TOKENS:
                raise ValueError(
                    f"Invalid weekday token: '{token}'. "
                    f"Must be one of: {sorted(VALID_WEEKDAY_TOKENS)}"
                )
        return v

    @model_validator(mode="after")
    def _entries_not_empty(self) -> "EncounterZone":
        if len(self.entries) == 0:
            raise ValueError(
                f"Encounter zone '{self.zone_id}' must have at least one entry."
            )
        return self

    def total_weight(self) -> int:
        """Sum of all entry weights (for probability calculations)."""
        return sum(e.weight for e in self.entries)

    def monster_ids(self) -> list[str]:
        """Return a deduplicated list of monster IDs in this zone."""
        seen: set[str] = set()
        result: list[str] = []
        for e in self.entries:
            if e.monster_id not in seen:
                seen.add(e.monster_id)
                result.append(e.monster_id)
        return result


# ---------------------------------------------------------------------------
# Encounter table (per-map)
# ---------------------------------------------------------------------------


class EncounterTable(BaseModel):
    """
    The complete encounter table for a single map.

    Contains one or more EncounterZones. Stored as a YAML file co-located
    with the map's .tmx file.

    Convention: ``maps/<map_stem>.encounters.yaml``
    """

    map_id: str = Field(..., min_length=1)
    zones: list[EncounterZone] = Field(default_factory=list)

    @model_validator(mode="after")
    def _zone_ids_unique(self) -> "EncounterTable":
        seen: set[str] = set()
        for zone in self.zones:
            if zone.zone_id in seen:
                raise ValueError(
                    f"Duplicate zone_id '{zone.zone_id}' in encounter table "
                    f"for map '{self.map_id}'."
                )
            seen.add(zone.zone_id)
        return self

    def get_zone(self, zone_id: str) -> Optional[EncounterZone]:
        """Return the zone with the given ID, or None."""
        for zone in self.zones:
            if zone.zone_id == zone_id:
                return zone
        return None

    def all_monster_ids(self) -> list[str]:
        """Collect all unique monster IDs across all zones."""
        seen: set[str] = set()
        result: list[str] = []
        for zone in self.zones:
            for mid in zone.monster_ids():
                if mid not in seen:
                    seen.add(mid)
                    result.append(mid)
        return result

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_yaml(self) -> str:
        """Serialize to YAML string for writing to disk."""
        data = self.model_dump()
        return yaml.dump(data, sort_keys=False, allow_unicode=True)

    @classmethod
    def from_yaml(cls, text: str) -> "EncounterTable":
        """Deserialize from a YAML string."""
        raw = yaml.safe_load(text)
        return cls(**raw)

    @classmethod
    def from_file(cls, path: Path) -> "EncounterTable":
        """Load an EncounterTable from a .yaml file."""
        return cls.from_yaml(path.read_text(encoding="utf-8"))

    def save(self, maps_dir: Path, map_stem: str) -> Path:
        """
        Write this table to ``<maps_dir>/<map_stem>.encounters.yaml``.

        Returns the path of the written file.
        """
        maps_dir.mkdir(parents=True, exist_ok=True)
        out = maps_dir / f"{map_stem}.encounters.yaml"
        out.write_text(self.to_yaml(), encoding="utf-8")
        return out


# ---------------------------------------------------------------------------
# Encounter table builder (fluent API)
# ---------------------------------------------------------------------------


class EncounterTableBuilder:
    """
    Fluent builder for EncounterTable objects.

    Usage::

        table = (
            EncounterTableBuilder("route_1")
            .zone("route_1_grass", suggested_level=5)
                .add("porcupinito", weight=10, level_min=3, level_max=7,
                     time_restrictions=["morning", "afternoon"])
                .add("iguana_evo", weight=5, level_min=4, level_max=8)
            .zone("route_1_water", suggested_level=8)
                .add("aquazor", weight=8, level_min=5, level_max=10)
            .build()
        )
    """

    def __init__(self, map_id: str) -> None:
        self._map_id = map_id
        self._zones: list[dict] = []
        self._current_zone: Optional[dict] = None

    def zone(
        self,
        zone_id: str,
        *,
        description: str = "",
        suggested_level: Optional[int] = None,
        active_time_slots: Optional[list[str]] = None,
        active_seasons: Optional[list[str]] = None,
        active_weekdays: Optional[list[str]] = None,
    ) -> "EncounterTableBuilder":
        """Start a new zone (or switch to a named zone if it already exists)."""
        if self._current_zone is not None:
            self._zones.append(self._current_zone)
        self._current_zone = {
            "zone_id": zone_id,
            "description": description,
            "suggested_level": suggested_level,
            "entries": [],
            "active_time_slots": active_time_slots or [],
            "active_seasons": active_seasons or [],
            "active_weekdays": active_weekdays or [],
        }
        return self

    def add(
        self,
        monster_id: str,
        *,
        weight: int = 10,
        level_min: int = 1,
        level_max: int = 5,
        time_restrictions: Optional[list[str]] = None,
        season_restrictions: Optional[list[str]] = None,
        weekday_restrictions: Optional[list[str]] = None,
    ) -> "EncounterTableBuilder":
        """Add an encounter entry to the current zone."""
        if self._current_zone is None:
            raise RuntimeError(
                "Call .zone() before .add() to specify which zone to add to."
            )
        self._current_zone["entries"].append(
            {
                "monster_id": monster_id,
                "weight": weight,
                "level_min": level_min,
                "level_max": level_max,
                "time_restrictions": time_restrictions or [],
                "season_restrictions": season_restrictions or [],
                "weekday_restrictions": weekday_restrictions or [],
            }
        )
        return self

    def build(self) -> EncounterTable:
        """Finalize and validate the EncounterTable."""
        if self._current_zone is not None:
            self._zones.append(self._current_zone)
            self._current_zone = None

        return EncounterTable(
            map_id=self._map_id,
            zones=[EncounterZone(**z) for z in self._zones],
        )

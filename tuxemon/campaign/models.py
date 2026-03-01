# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Pydantic schema models for campaign manifests and wizard steps.

Schema constraints are defined in docs/campaign_maker_mvp.md §4.
"""
from __future__ import annotations

import re
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from tuxemon.rules.models import ClauseID, DifficultyPreset

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_CAMPAIGN_ID_RE = re.compile(r"^[a-z][a-z0-9_]{2,63}$")
_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")

VALID_TIME_RESTRICTION_TOKENS: frozenset[str] = frozenset(
    {"dawn", "morning", "afternoon", "dusk", "night", "day", "any"}
)
VALID_SEASON_TOKENS: frozenset[str] = frozenset(
    {"spring", "summer", "autumn", "winter"}
)
VALID_WEEKDAY_TOKENS: frozenset[str] = frozenset(
    {"monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"}
)

STARTER_TEMPLATES: frozenset[str] = frozenset(
    {"blank", "classic_two_region", "battle_challenge", "event_adventure"}
)


# ---------------------------------------------------------------------------
# Encounter entry
# ---------------------------------------------------------------------------


class EncounterEntry(BaseModel):
    """A single monster entry in a zone's encounter table."""

    monster_id: str = Field(..., min_length=1)
    weight: int = Field(default=10, ge=1)
    level_min: int = Field(default=1, ge=1, le=100)
    level_max: int = Field(default=5, ge=1, le=100)
    time_restrictions: list[str] = Field(default_factory=list)
    season_restrictions: list[str] = Field(default_factory=list)
    weekday_restrictions: list[str] = Field(default_factory=list)

    @field_validator("time_restrictions", mode="before")
    @classmethod
    def _validate_time_tokens(cls, v: list[str]) -> list[str]:
        for token in v:
            if token not in VALID_TIME_RESTRICTION_TOKENS:
                raise ValueError(
                    f"Invalid time restriction token: '{token}'. "
                    f"Must be one of: {sorted(VALID_TIME_RESTRICTION_TOKENS)}"
                )
        return v

    @field_validator("season_restrictions", mode="before")
    @classmethod
    def _validate_season_tokens(cls, v: list[str]) -> list[str]:
        for token in v:
            if token not in VALID_SEASON_TOKENS:
                raise ValueError(
                    f"Invalid season token: '{token}'. "
                    f"Must be one of: {sorted(VALID_SEASON_TOKENS)}"
                )
        return v

    @field_validator("weekday_restrictions", mode="before")
    @classmethod
    def _validate_weekday_tokens(cls, v: list[str]) -> list[str]:
        for token in v:
            if token not in VALID_WEEKDAY_TOKENS:
                raise ValueError(
                    f"Invalid weekday token: '{token}'. "
                    f"Must be one of: {sorted(VALID_WEEKDAY_TOKENS)}"
                )
        return v

    @model_validator(mode="after")
    def _level_range_valid(self) -> "EncounterEntry":
        if self.level_min > self.level_max:
            raise ValueError(
                f"level_min ({self.level_min}) must be ≤ level_max ({self.level_max})"
            )
        return self


# ---------------------------------------------------------------------------
# Campaign ruleset override
# ---------------------------------------------------------------------------


class CampaignRulesetOverride(BaseModel):
    """
    Optional battle ruleset overrides embedded in the campaign manifest.

    Validated against BattleRules field constraints.
    """

    team_size: Optional[int] = Field(default=None, ge=1, le=6)
    level_cap: Optional[int] = Field(default=None, ge=10, le=100)
    active_clauses: Optional[list[ClauseID]] = None
    allow_items_in_battle: Optional[bool] = None
    allow_held_items: Optional[bool] = None
    permadeath: bool = False
    nuzlocke_mode: bool = False
    default_difficulty: DifficultyPreset = DifficultyPreset.NORMAL


# ---------------------------------------------------------------------------
# Campaign manifest (campaign.yaml)
# ---------------------------------------------------------------------------


class CampaignManifest(BaseModel):
    """
    Validated campaign manifest model.

    Corresponds to the campaign.yaml schema in docs/campaign_maker_mvp.md §4.1.
    """

    id: str = Field(..., min_length=3, max_length=64)
    name: str = Field(..., min_length=3, max_length=80)
    version: str
    author: str = Field(..., min_length=1, max_length=60)
    engine_min_version: str
    description: str = Field(..., min_length=10, max_length=500)
    start_map: str = Field(..., min_length=1)
    entry_script: str = Field(..., min_length=1)
    tags: list[str] = Field(default_factory=list)
    license: Optional[str] = None
    language: str = "en_US"
    ruleset: CampaignRulesetOverride = Field(
        default_factory=CampaignRulesetOverride
    )

    @field_validator("id")
    @classmethod
    def _validate_id(cls, v: str) -> str:
        if not _CAMPAIGN_ID_RE.match(v):
            raise ValueError(
                f"Campaign ID '{v}' is invalid. "
                "Must start with a lowercase letter, contain only lowercase "
                "letters, digits, and underscores, and be 3–64 characters long."
            )
        return v

    @field_validator("version", "engine_min_version")
    @classmethod
    def _validate_semver(cls, v: str) -> str:
        if not _SEMVER_RE.match(v):
            raise ValueError(
                f"'{v}' is not a valid semantic version (expected MAJOR.MINOR.PATCH)."
            )
        return v

    @field_validator("start_map")
    @classmethod
    def _validate_map_extension(cls, v: str) -> str:
        if not v.endswith(".tmx"):
            raise ValueError(
                f"start_map '{v}' must be a .tmx file path."
            )
        return v


# ---------------------------------------------------------------------------
# Wizard step models
# ---------------------------------------------------------------------------


class WizardStep1(BaseModel):
    """Step 1 — Campaign Identity."""

    id: str
    name: str = Field(..., min_length=3, max_length=80)
    author: str = Field(..., min_length=1, max_length=60)
    description: str = Field(..., min_length=10, max_length=500)

    @field_validator("id")
    @classmethod
    def _validate_id(cls, v: str) -> str:
        if not _CAMPAIGN_ID_RE.match(v):
            raise ValueError(
                f"Campaign ID '{v}' is invalid. "
                "Must start with a lowercase letter, contain only lowercase "
                "letters, digits, and underscores, and be 3–64 characters long."
            )
        return v


class WizardStep2(BaseModel):
    """Step 2 — Starting Point (template selection)."""

    template: str = "blank"

    @field_validator("template")
    @classmethod
    def _validate_template(cls, v: str) -> str:
        if v not in STARTER_TEMPLATES:
            raise ValueError(
                f"Unknown template '{v}'. "
                f"Must be one of: {sorted(STARTER_TEMPLATES)}"
            )
        return v


class WizardStep3(BaseModel):
    """Step 3 — Rules and Difficulty."""

    default_difficulty: DifficultyPreset = DifficultyPreset.NORMAL
    permadeath: bool = False
    nuzlocke_mode: bool = False
    active_clauses: list[ClauseID] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Scaffold directory descriptor
# ---------------------------------------------------------------------------


class ScaffoldDirectory(BaseModel):
    """
    Describes the directory structure generated by the wizard for a new campaign.

    Paths are relative to the campaign root. The wizard creates these on disk.
    """

    root: Path
    maps_dir: Path
    scripts_dir: Path
    monsters_dir: Path
    items_dir: Path
    music_dir: Path
    sounds_dir: Path
    gfx_dir: Path
    locale_dir: Path
    manifest_path: Path

    @classmethod
    def from_root(cls, root: Path) -> "ScaffoldDirectory":
        return cls(
            root=root,
            maps_dir=root / "maps",
            scripts_dir=root / "scripts",
            monsters_dir=root / "monsters",
            items_dir=root / "items",
            music_dir=root / "music",
            sounds_dir=root / "sounds",
            gfx_dir=root / "gfx",
            locale_dir=root / "locale",
            manifest_path=root / "campaign.yaml",
        )

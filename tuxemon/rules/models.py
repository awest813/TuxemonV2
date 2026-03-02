# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Pydantic models for the OpenCapsuleMon rules and settings system.

Each model corresponds to a settings layer as described in docs/settings_taxonomy.md.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field, field_validator


class PlayContext(str, Enum):
    """The play context that determines which rules apply."""

    CAMPAIGN = "campaign"
    CASUAL_ONLINE = "casual_online"
    TOURNAMENT = "tournament"


class ClauseID(str, Enum):
    """Vocabulary of supported battle clauses."""

    DUPLICATE_SPECIES = "duplicate_species"
    DUPLICATE_ITEM = "duplicate_item"
    SLEEP_LIMIT = "sleep_limit"
    OHKO_BAN = "ohko_ban"
    EVASION_LIMIT = "evasion_limit"
    SELF_KO_DRAW = "self_ko_draw"


class DifficultyPreset(str, Enum):
    EASY = "easy"
    NORMAL = "normal"
    HARD = "hard"
    CHALLENGE = "challenge"


class RematchPolicy(str, Enum):
    DISABLED = "disabled"
    ENABLED = "enabled"


class RematchLevelPolicy(str, Enum):
    STATIC = "static"
    SCALED = "scaled"
    AUTHORED = "authored"


# ---------------------------------------------------------------------------
# Layer 1 — Engine-default battle rules
# ---------------------------------------------------------------------------


class BattleRules(BaseModel):
    """
    Core battle rule parameters.

    These are the engine defaults (Layer 1). Higher layers may override these
    for their authorized keys only.
    """

    team_size: int = Field(default=6, ge=1, le=6)
    level_cap: Optional[int] = Field(default=None, ge=10, le=100)
    turn_timer_seconds: int = Field(default=0, ge=0)
    active_clauses: list[ClauseID] = Field(default_factory=list)
    allow_items_in_battle: bool = True
    allow_held_items: bool = True

    @field_validator("team_size")
    @classmethod
    def _team_size_range(cls, v: int) -> int:
        if not 1 <= v <= 6:
            raise ValueError("team_size must be between 1 and 6")
        return v

    @field_validator("turn_timer_seconds")
    @classmethod
    def _timer_range(cls, v: int) -> int:
        if v != 0 and not 15 <= v <= 300:
            raise ValueError(
                "turn_timer_seconds must be 0 (disabled) or between 15 and 300"
            )
        return v


class TournamentRules(BaseModel):
    """Tournament-specific parameters."""

    bracket_size: int = Field(default=8)
    check_in_duration_minutes: int = Field(default=15, ge=1)
    reconnect_grace_seconds: int = Field(default=90, ge=0)
    no_show_timeout_seconds: int = Field(default=120, ge=0)

    @field_validator("bracket_size")
    @classmethod
    def _valid_bracket_size(cls, v: int) -> int:
        if v not in (8, 16):
            raise ValueError("bracket_size must be 8 or 16")
        return v


class EncounterRules(BaseModel):
    """Encounter rate and time-restriction parameters."""

    encounter_rate_modifier: float = Field(default=1.0, ge=0.0, le=2.0)
    time_restrictions: Optional[list[str]] = None


class CampaignRules(BaseModel):
    """Campaign-specific rules and accessibility settings."""

    difficulty: DifficultyPreset = DifficultyPreset.NORMAL
    permadeath: bool = False
    nuzlocke_mode: bool = False
    rematch_policy: RematchPolicy = RematchPolicy.ENABLED
    rematch_level_policy: RematchLevelPolicy = RematchLevelPolicy.SCALED


# ---------------------------------------------------------------------------
# Layer 2 — Player Config
# ---------------------------------------------------------------------------


class PlayerConfig(BaseModel):
    """
    Player-owned settings (Layer 2).

    Only keys listed here may be set by a player. The resolver ignores
    any extra keys the player config provides for higher-layer-owned settings.
    """

    encounter_rate_modifier: float = Field(default=1.0, ge=0.0, le=2.0)
    dialog_speed: str = "slow"
    unit_measure: str = "metric"
    combat_click_to_continue: bool = False
    sound_volume: float = Field(default=0.2, ge=0.0, le=1.0)
    music_volume: float = Field(default=0.5, ge=0.0, le=1.0)
    large_gui: bool = False
    difficulty: DifficultyPreset = DifficultyPreset.NORMAL


# ---------------------------------------------------------------------------
# Layer 3 — Host / Server Config
# ---------------------------------------------------------------------------


class HostConfig(BaseModel):
    """
    Host or tournament administrator settings (Layer 3).

    Only keys listed here may be set by a host or admin.
    """

    team_size: Optional[int] = Field(default=None, ge=1, le=6)
    level_cap: Optional[int] = Field(default=None, ge=10, le=100)
    turn_timer_seconds: Optional[int] = None
    active_clauses: Optional[list[ClauseID]] = None
    allow_items_in_battle: Optional[bool] = None
    allow_held_items: Optional[bool] = None
    bracket_size: Optional[int] = None
    check_in_duration_minutes: Optional[int] = None
    reconnect_grace_seconds: Optional[int] = None
    no_show_timeout_seconds: Optional[int] = None

    @field_validator("bracket_size")
    @classmethod
    def _valid_bracket_size(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v not in (8, 16):
            raise ValueError("bracket_size must be 8 or 16")
        return v

    @field_validator("turn_timer_seconds")
    @classmethod
    def _timer_range(cls, v: Optional[int]) -> Optional[int]:
        if v is not None and v != 0 and not 15 <= v <= 300:
            raise ValueError(
                "turn_timer_seconds must be 0 (disabled) or between 15 and 300"
            )
        return v


# ---------------------------------------------------------------------------
# Layer 4 — Mod / Campaign Override
# ---------------------------------------------------------------------------


class ModOverride(BaseModel):
    """
    Mod or campaign author overrides (Layer 4, highest priority).

    Only keys listed here may be pinned by a mod. These overrides apply for
    a specific zone or event and expire when the zone/event ends.
    """

    team_size: Optional[int] = Field(default=None, ge=1, le=6)
    level_cap: Optional[int] = Field(default=None, ge=10, le=100)
    active_clauses: Optional[list[ClauseID]] = None
    allow_items_in_battle: Optional[bool] = None
    allow_held_items: Optional[bool] = None
    encounter_rate_modifier: Optional[float] = Field(
        default=None, ge=0.0, le=2.0
    )
    time_restrictions: Optional[list[str]] = None
    rematch_policy: Optional[RematchPolicy] = None
    permadeath: Optional[bool] = None
    nuzlocke_mode: Optional[bool] = None


# ---------------------------------------------------------------------------
# Resolved snapshot
# ---------------------------------------------------------------------------


class ResolvedRuleset(BaseModel):
    """
    Final resolved ruleset snapshot, frozen at battle/session start.

    Constructed by SettingsResolver.resolve() and immutable thereafter.
    """

    context: PlayContext
    battle: BattleRules
    tournament: TournamentRules
    encounter: EncounterRules
    campaign: CampaignRules

    model_config = {"frozen": True}

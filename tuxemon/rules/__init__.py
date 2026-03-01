# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Rules and settings resolution system.

Exposes the settings resolver and ruleset models for use throughout the engine.
"""
from tuxemon.rules.models import (
    BattleRules,
    CampaignRules,
    ClauseID,
    EncounterRules,
    HostConfig,
    ModOverride,
    PlayContext,
    PlayerConfig,
    ResolvedRuleset,
    TournamentRules,
)
from tuxemon.rules.resolver import SettingsResolver

__all__ = [
    "BattleRules",
    "CampaignRules",
    "ClauseID",
    "EncounterRules",
    "HostConfig",
    "ModOverride",
    "PlayContext",
    "PlayerConfig",
    "ResolvedRuleset",
    "SettingsResolver",
    "TournamentRules",
]

# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Rules and settings resolution system.

Exposes the settings resolver and ruleset models for use throughout the engine.
"""

from tuxemon.rules.clause_sets import (
    default_clauses_for_context,
    optional_clauses_for_context,
)
from tuxemon.rules.match_confirmation import (
    MatchConfirmationSnapshot,
    RuleDifference,
    build_match_confirmation_snapshot,
)
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
    "build_match_confirmation_snapshot",
    "CampaignRules",
    "default_clauses_for_context",
    "ClauseID",
    "EncounterRules",
    "MatchConfirmationSnapshot",
    "HostConfig",
    "ModOverride",
    "PlayContext",
    "PlayerConfig",
    "ResolvedRuleset",
    "RuleDifference",
    "SettingsResolver",
    "optional_clauses_for_context",
    "TournamentRules",
]

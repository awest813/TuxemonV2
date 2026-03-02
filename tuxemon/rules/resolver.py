# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Settings resolver with four-layer precedence.

Precedence (highest to lowest):
  4. ModOverride    — mod/campaign author, zone/event scope
  3. HostConfig     — session host or tournament admin
  2. PlayerConfig   — per-user preferences
  1. Engine default — built-in rulebook values

Each layer is only consulted for keys it is authorized to provide.
A layer that does not provide a value for a key falls through to the next layer.
"""

from __future__ import annotations

from typing import Any, Optional

from tuxemon.rules.clause_sets import default_clauses_for_context
from tuxemon.rules.models import (
    BattleRules,
    CampaignRules,
    ClauseID,
    DifficultyPreset,
    EncounterRules,
    HostConfig,
    ModOverride,
    PlayContext,
    PlayerConfig,
    ResolvedRuleset,
    TournamentRules,
)


def _first(*values: Any) -> Any:
    """Return the first non-None value from the provided sequence."""
    for v in values:
        if v is not None:
            return v
    return None


class SettingsResolver:
    """
    Resolves the final ruleset for a given play context by merging all four
    settings layers according to the precedence rules in docs/settings_taxonomy.md.

    Usage::

        resolver = SettingsResolver(
            context=PlayContext.TOURNAMENT,
            player=PlayerConfig(...),
            host=HostConfig(level_cap=50, active_clauses=[...]),
            mod=None,
        )
        ruleset = resolver.resolve()
    """

    def __init__(
        self,
        context: PlayContext,
        player: Optional[PlayerConfig] = None,
        host: Optional[HostConfig] = None,
        mod: Optional[ModOverride] = None,
    ) -> None:
        self.context = context
        self.player = player or PlayerConfig()
        self.host = host or HostConfig()
        self.mod = mod or ModOverride()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def resolve(self) -> ResolvedRuleset:
        """
        Produce the final immutable ResolvedRuleset for the current context.

        The returned snapshot should be taken once at session/battle start and
        held for the duration of the match; it will not reflect later changes
        to any layer.
        """
        return ResolvedRuleset(
            context=self.context,
            battle=self._resolve_battle(),
            tournament=self._resolve_tournament(),
            encounter=self._resolve_encounter(),
            campaign=self._resolve_campaign(),
        )

    # ------------------------------------------------------------------
    # Per-domain resolvers
    # ------------------------------------------------------------------

    def _resolve_battle(self) -> BattleRules:
        defaults = BattleRules()

        # team_size: mod > host > engine default
        team_size: int = _first(
            self.mod.team_size,
            self.host.team_size,
            defaults.team_size,
        )

        # level_cap: mod > host > engine default (None means no cap)
        level_cap: Optional[int] = _first(
            self.mod.level_cap,
            self.host.level_cap,
            defaults.level_cap,
        )

        # turn_timer_seconds: host > engine default (mod cannot set timer)
        turn_timer_seconds: int = _first(
            self.host.turn_timer_seconds,
            defaults.turn_timer_seconds,
        )

        # active_clauses: mod > host > context-based default
        active_clauses: list[ClauseID] = _first(
            self.mod.active_clauses,
            self.host.active_clauses,
            default_clauses_for_context(self.context),
        )

        # allow_items_in_battle: mod > host > engine default
        allow_items_in_battle: bool = _first(
            self.mod.allow_items_in_battle,
            self.host.allow_items_in_battle,
            defaults.allow_items_in_battle,
        )

        # allow_held_items: mod > host > engine default
        allow_held_items: bool = _first(
            self.mod.allow_held_items,
            self.host.allow_held_items,
            defaults.allow_held_items,
        )

        return BattleRules(
            team_size=team_size,
            level_cap=level_cap,
            turn_timer_seconds=turn_timer_seconds,
            active_clauses=active_clauses,
            allow_items_in_battle=allow_items_in_battle,
            allow_held_items=allow_held_items,
        )

    def _resolve_tournament(self) -> TournamentRules:
        defaults = TournamentRules()

        bracket_size: int = _first(
            self.host.bracket_size,
            defaults.bracket_size,
        )
        check_in_duration_minutes: int = _first(
            self.host.check_in_duration_minutes,
            defaults.check_in_duration_minutes,
        )
        reconnect_grace_seconds: int = _first(
            self.host.reconnect_grace_seconds,
            defaults.reconnect_grace_seconds,
        )
        no_show_timeout_seconds: int = _first(
            self.host.no_show_timeout_seconds,
            defaults.no_show_timeout_seconds,
        )

        return TournamentRules(
            bracket_size=bracket_size,
            check_in_duration_minutes=check_in_duration_minutes,
            reconnect_grace_seconds=reconnect_grace_seconds,
            no_show_timeout_seconds=no_show_timeout_seconds,
        )

    def _resolve_encounter(self) -> EncounterRules:
        defaults = EncounterRules()

        # encounter_rate_modifier: mod > player > engine default
        encounter_rate_modifier: float = _first(
            self.mod.encounter_rate_modifier,
            self.player.encounter_rate_modifier,
            defaults.encounter_rate_modifier,
        )

        # time_restrictions: mod only (players and hosts cannot set these)
        time_restrictions: Optional[list[str]] = self.mod.time_restrictions

        return EncounterRules(
            encounter_rate_modifier=encounter_rate_modifier,
            time_restrictions=time_restrictions,
        )

    def _resolve_campaign(self) -> CampaignRules:
        defaults = CampaignRules()

        # difficulty: player > engine default (mod cannot change difficulty tier)
        difficulty: DifficultyPreset = _first(
            self.player.difficulty,
            defaults.difficulty,
        )

        # permadeath / nuzlocke_mode: mod > engine default
        permadeath: bool = _first(
            self.mod.permadeath,
            defaults.permadeath,
        )
        nuzlocke_mode: bool = _first(
            self.mod.nuzlocke_mode,
            defaults.nuzlocke_mode,
        )

        # rematch_policy: mod > engine default
        rematch_policy = _first(
            self.mod.rematch_policy,
            defaults.rematch_policy,
        )

        return CampaignRules(
            difficulty=difficulty,
            permadeath=permadeath,
            nuzlocke_mode=nuzlocke_mode,
            rematch_policy=rematch_policy,
            rematch_level_policy=defaults.rematch_level_policy,
        )


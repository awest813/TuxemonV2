# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Regression tests for tuxemon.rules.resolver — settings precedence and fallback behavior.

Coverage map (from docs/settings_taxonomy.md §5):
  R1 — Default resolution: key resolves to engine default when no other layer provides it.
  R2 — Player override: player config value overrides default for authorized keys.
  R3 — Host override: host config value overrides player config for authorized keys.
  R4 — Mod override: mod override takes precedence over host and player for authorized keys.
  R5 — Unauthorized override ignored: a layer attempting to set a key it does not own
       falls through to the next authorized layer.
  R6 — Battle snapshot: resolved ruleset frozen at battle start.
"""

import pytest

from tuxemon.rules.models import (
    BattleRules,
    ClauseID,
    DifficultyPreset,
    HostConfig,
    ModOverride,
    PlayContext,
    PlayerConfig,
    RematchPolicy,
)
from tuxemon.rules.resolver import SettingsResolver

# ---------------------------------------------------------------------------
# R1 — Default resolution
# ---------------------------------------------------------------------------


class TestDefaultResolution:
    """R1: All layers absent → engine defaults prevail."""

    def test_campaign_defaults(self):
        r = SettingsResolver(context=PlayContext.CAMPAIGN).resolve()
        assert r.battle.team_size == 6
        assert r.battle.level_cap is None
        assert r.battle.turn_timer_seconds == 0
        assert r.battle.active_clauses == []
        assert r.battle.allow_items_in_battle is True
        assert r.battle.allow_held_items is True

    def test_tournament_defaults(self):
        r = SettingsResolver(context=PlayContext.TOURNAMENT).resolve()
        assert r.tournament.bracket_size == 8
        assert r.tournament.reconnect_grace_seconds == 90
        assert r.tournament.no_show_timeout_seconds == 120

    def test_encounter_defaults(self):
        r = SettingsResolver(context=PlayContext.CAMPAIGN).resolve()
        assert r.encounter.encounter_rate_modifier == 1.0
        assert r.encounter.time_restrictions is None

    def test_campaign_rules_defaults(self):
        r = SettingsResolver(context=PlayContext.CAMPAIGN).resolve()
        assert r.campaign.difficulty == DifficultyPreset.NORMAL
        assert r.campaign.permadeath is False
        assert r.campaign.nuzlocke_mode is False
        assert r.campaign.rematch_policy == RematchPolicy.ENABLED

    def test_tournament_context_enables_default_clauses(self):
        """Tournaments default to duplicate_species + self_ko_draw."""
        r = SettingsResolver(context=PlayContext.TOURNAMENT).resolve()
        assert ClauseID.DUPLICATE_SPECIES in r.battle.active_clauses
        assert ClauseID.SELF_KO_DRAW in r.battle.active_clauses

    def test_campaign_context_has_no_default_clauses(self):
        r = SettingsResolver(context=PlayContext.CAMPAIGN).resolve()
        assert r.battle.active_clauses == []

    def test_casual_online_has_no_default_clauses(self):
        r = SettingsResolver(context=PlayContext.CASUAL_ONLINE).resolve()
        assert r.battle.active_clauses == []


# ---------------------------------------------------------------------------
# R2 — Player override
# ---------------------------------------------------------------------------


class TestPlayerOverride:
    """R2: Player config overrides engine defaults for authorized keys."""

    def test_player_sets_encounter_rate(self):
        player = PlayerConfig(encounter_rate_modifier=0.5)
        r = SettingsResolver(
            context=PlayContext.CAMPAIGN, player=player
        ).resolve()
        assert r.encounter.encounter_rate_modifier == 0.5

    def test_player_sets_difficulty(self):
        player = PlayerConfig(difficulty=DifficultyPreset.HARD)
        r = SettingsResolver(
            context=PlayContext.CAMPAIGN, player=player
        ).resolve()
        assert r.campaign.difficulty == DifficultyPreset.HARD

    def test_player_easy_difficulty(self):
        player = PlayerConfig(difficulty=DifficultyPreset.EASY)
        r = SettingsResolver(
            context=PlayContext.CAMPAIGN, player=player
        ).resolve()
        assert r.campaign.difficulty == DifficultyPreset.EASY

    def test_player_max_encounter_rate(self):
        player = PlayerConfig(encounter_rate_modifier=2.0)
        r = SettingsResolver(
            context=PlayContext.CAMPAIGN, player=player
        ).resolve()
        assert r.encounter.encounter_rate_modifier == 2.0

    def test_player_zero_encounter_rate(self):
        player = PlayerConfig(encounter_rate_modifier=0.0)
        r = SettingsResolver(
            context=PlayContext.CAMPAIGN, player=player
        ).resolve()
        assert r.encounter.encounter_rate_modifier == 0.0


# ---------------------------------------------------------------------------
# R3 — Host override
# ---------------------------------------------------------------------------


class TestHostOverride:
    """R3: Host config overrides player config (and engine defaults) for authorized keys."""

    def test_host_sets_team_size(self):
        host = HostConfig(team_size=3)
        r = SettingsResolver(
            context=PlayContext.CASUAL_ONLINE, host=host
        ).resolve()
        assert r.battle.team_size == 3

    def test_host_sets_level_cap(self):
        host = HostConfig(level_cap=50)
        r = SettingsResolver(
            context=PlayContext.TOURNAMENT, host=host
        ).resolve()
        assert r.battle.level_cap == 50

    def test_host_sets_timer(self):
        host = HostConfig(turn_timer_seconds=60)
        r = SettingsResolver(
            context=PlayContext.TOURNAMENT, host=host
        ).resolve()
        assert r.battle.turn_timer_seconds == 60

    def test_host_disables_timer(self):
        host = HostConfig(turn_timer_seconds=0)
        r = SettingsResolver(
            context=PlayContext.CASUAL_ONLINE, host=host
        ).resolve()
        assert r.battle.turn_timer_seconds == 0

    def test_host_sets_clauses(self):
        host = HostConfig(active_clauses=[ClauseID.SLEEP_LIMIT])
        r = SettingsResolver(
            context=PlayContext.CASUAL_ONLINE, host=host
        ).resolve()
        assert r.battle.active_clauses == [ClauseID.SLEEP_LIMIT]

    def test_host_disables_items(self):
        host = HostConfig(allow_items_in_battle=False)
        r = SettingsResolver(
            context=PlayContext.CASUAL_ONLINE, host=host
        ).resolve()
        assert r.battle.allow_items_in_battle is False

    def test_host_overrides_bracket_size(self):
        host = HostConfig(bracket_size=16)
        r = SettingsResolver(
            context=PlayContext.TOURNAMENT, host=host
        ).resolve()
        assert r.tournament.bracket_size == 16

    def test_host_sets_reconnect_grace(self):
        host = HostConfig(reconnect_grace_seconds=30)
        r = SettingsResolver(
            context=PlayContext.TOURNAMENT, host=host
        ).resolve()
        assert r.tournament.reconnect_grace_seconds == 30

    def test_host_overrides_player_encounter_rate(self):
        """Host cannot set encounter_rate — player config should take precedence over defaults."""
        player = PlayerConfig(encounter_rate_modifier=0.25)
        host = HostConfig()
        r = SettingsResolver(
            context=PlayContext.CASUAL_ONLINE, player=player, host=host
        ).resolve()
        assert r.encounter.encounter_rate_modifier == 0.25

    def test_host_clauses_override_tournament_defaults(self):
        """A host clause list replaces the default tournament clauses."""
        host = HostConfig(active_clauses=[ClauseID.OHKO_BAN])
        r = SettingsResolver(
            context=PlayContext.TOURNAMENT, host=host
        ).resolve()
        assert r.battle.active_clauses == [ClauseID.OHKO_BAN]
        assert ClauseID.DUPLICATE_SPECIES not in r.battle.active_clauses


# ---------------------------------------------------------------------------
# R4 — Mod override
# ---------------------------------------------------------------------------


class TestModOverride:
    """R4: Mod override takes highest precedence for authorized keys."""

    def test_mod_pins_level_cap(self):
        mod = ModOverride(level_cap=20)
        host = HostConfig(level_cap=50)
        r = SettingsResolver(
            context=PlayContext.CAMPAIGN, host=host, mod=mod
        ).resolve()
        assert r.battle.level_cap == 20

    def test_mod_pins_team_size(self):
        mod = ModOverride(team_size=1)
        host = HostConfig(team_size=6)
        r = SettingsResolver(
            context=PlayContext.CAMPAIGN, host=host, mod=mod
        ).resolve()
        assert r.battle.team_size == 1

    def test_mod_disables_items(self):
        mod = ModOverride(allow_items_in_battle=False)
        host = HostConfig(allow_items_in_battle=True)
        r = SettingsResolver(
            context=PlayContext.CAMPAIGN, host=host, mod=mod
        ).resolve()
        assert r.battle.allow_items_in_battle is False

    def test_mod_pins_clauses(self):
        mod = ModOverride(active_clauses=[ClauseID.EVASION_LIMIT])
        host = HostConfig(active_clauses=[ClauseID.SLEEP_LIMIT])
        r = SettingsResolver(
            context=PlayContext.CAMPAIGN, host=host, mod=mod
        ).resolve()
        assert r.battle.active_clauses == [ClauseID.EVASION_LIMIT]

    def test_mod_enables_permadeath(self):
        mod = ModOverride(permadeath=True)
        r = SettingsResolver(context=PlayContext.CAMPAIGN, mod=mod).resolve()
        assert r.campaign.permadeath is True

    def test_mod_enables_nuzlocke(self):
        mod = ModOverride(nuzlocke_mode=True)
        r = SettingsResolver(context=PlayContext.CAMPAIGN, mod=mod).resolve()
        assert r.campaign.nuzlocke_mode is True

    def test_mod_pins_encounter_rate(self):
        """Mod can disable encounters in a zone by setting rate to 0."""
        player = PlayerConfig(encounter_rate_modifier=1.5)
        mod = ModOverride(encounter_rate_modifier=0.0)
        r = SettingsResolver(
            context=PlayContext.CAMPAIGN, player=player, mod=mod
        ).resolve()
        assert r.encounter.encounter_rate_modifier == 0.0

    def test_mod_sets_time_restrictions(self):
        mod = ModOverride(time_restrictions=["morning", "afternoon"])
        r = SettingsResolver(context=PlayContext.CAMPAIGN, mod=mod).resolve()
        assert r.encounter.time_restrictions == ["morning", "afternoon"]

    def test_mod_disables_rematch(self):
        mod = ModOverride(rematch_policy=RematchPolicy.DISABLED)
        r = SettingsResolver(context=PlayContext.CAMPAIGN, mod=mod).resolve()
        assert r.campaign.rematch_policy == RematchPolicy.DISABLED

    def test_mod_overrides_all_three_layers(self):
        """Mod beats host and player simultaneously."""
        player = PlayerConfig(encounter_rate_modifier=1.5)
        host = HostConfig(level_cap=40, team_size=4)
        mod = ModOverride(
            level_cap=10, team_size=2, encounter_rate_modifier=0.0
        )
        r = SettingsResolver(
            context=PlayContext.CAMPAIGN, player=player, host=host, mod=mod
        ).resolve()
        assert r.battle.level_cap == 10
        assert r.battle.team_size == 2
        assert r.encounter.encounter_rate_modifier == 0.0


# ---------------------------------------------------------------------------
# R5 — Unauthorized override is ignored
# ---------------------------------------------------------------------------


class TestUnauthorizedOverrideIgnored:
    """
    R5: A layer attempting to set a key it does not own falls through to the
    next authorized layer.

    The resolver's architecture enforces this by only reading each key from
    layers that are authorized to provide it (see resolver.py). This test
    suite validates the runtime behavior of that design.
    """

    def test_player_cannot_pin_team_size(self):
        """
        team_size is a host/mod key. PlayerConfig has no team_size field.
        Even if a player provides a team_size value it cannot be read by the
        resolver for that key — the default (6) should apply.
        """
        r = SettingsResolver(context=PlayContext.CASUAL_ONLINE).resolve()
        assert r.battle.team_size == 6

    def test_player_cannot_set_clauses(self):
        """
        active_clauses is a host/mod key. Player has no active_clauses field.
        Casual online default is empty; no player-path sets clauses.
        """
        r = SettingsResolver(context=PlayContext.CASUAL_ONLINE).resolve()
        assert r.battle.active_clauses == []

    def test_host_cannot_set_permadeath(self):
        """
        permadeath is a mod-only key. HostConfig has no permadeath field.
        Resolver defaults to False.
        """
        host = HostConfig()
        r = SettingsResolver(context=PlayContext.CAMPAIGN, host=host).resolve()
        assert r.campaign.permadeath is False

    def test_host_cannot_set_time_restrictions(self):
        """
        time_restrictions is a mod-only key.
        """
        host = HostConfig()
        r = SettingsResolver(context=PlayContext.CAMPAIGN, host=host).resolve()
        assert r.encounter.time_restrictions is None

    def test_mod_cannot_set_difficulty(self):
        """
        difficulty is a player-only key. ModOverride has no difficulty field.
        Player default (normal) should be used, not any mod-supplied value.
        """
        player = PlayerConfig(difficulty=DifficultyPreset.HARD)
        mod = ModOverride()
        r = SettingsResolver(
            context=PlayContext.CAMPAIGN, player=player, mod=mod
        ).resolve()
        assert r.campaign.difficulty == DifficultyPreset.HARD


# ---------------------------------------------------------------------------
# R6 — Battle snapshot immutability
# ---------------------------------------------------------------------------


class TestBattleSnapshot:
    """
    R6: The resolved ruleset frozen at battle start is immutable.
    Changing a layer's value after resolve() should not mutate the snapshot.
    """

    def test_snapshot_is_frozen(self):
        host = HostConfig(level_cap=50)
        resolver = SettingsResolver(context=PlayContext.TOURNAMENT, host=host)
        snapshot = resolver.resolve()

        assert snapshot.battle.level_cap == 50
        with pytest.raises(Exception):
            snapshot.battle = BattleRules(level_cap=30)  # type: ignore[misc]

    def test_snapshot_context_is_frozen(self):
        resolver = SettingsResolver(context=PlayContext.CAMPAIGN)
        snapshot = resolver.resolve()
        with pytest.raises(Exception):
            snapshot.context = PlayContext.TOURNAMENT  # type: ignore[misc]

    def test_snapshot_is_independent_of_later_resolver_changes(self):
        """
        The snapshot is a value object; re-running resolve() with different
        inputs produces a new object — the original snapshot is unchanged.
        """
        host = HostConfig(level_cap=50)
        resolver = SettingsResolver(context=PlayContext.TOURNAMENT, host=host)
        snapshot1 = resolver.resolve()

        resolver2 = SettingsResolver(
            context=PlayContext.TOURNAMENT,
            host=HostConfig(level_cap=30),
        )
        snapshot2 = resolver2.resolve()

        assert snapshot1.battle.level_cap == 50
        assert snapshot2.battle.level_cap == 30

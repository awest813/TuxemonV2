# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for tuxemon.rules.models — Pydantic model validation and constraints.
"""

import pytest
from pydantic import ValidationError

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


class TestBattleRules:
    def test_defaults(self):
        r = BattleRules()
        assert r.team_size == 6
        assert r.level_cap is None
        assert r.turn_timer_seconds == 0
        assert r.active_clauses == []
        assert r.allow_items_in_battle is True
        assert r.allow_held_items is True

    def test_team_size_bounds(self):
        assert BattleRules(team_size=1).team_size == 1
        assert BattleRules(team_size=6).team_size == 6
        with pytest.raises(ValidationError):
            BattleRules(team_size=0)
        with pytest.raises(ValidationError):
            BattleRules(team_size=7)

    def test_turn_timer_zero_allowed(self):
        assert BattleRules(turn_timer_seconds=0).turn_timer_seconds == 0

    def test_turn_timer_valid_range(self):
        assert BattleRules(turn_timer_seconds=15).turn_timer_seconds == 15
        assert BattleRules(turn_timer_seconds=300).turn_timer_seconds == 300

    def test_turn_timer_invalid(self):
        with pytest.raises(ValidationError):
            BattleRules(turn_timer_seconds=5)
        with pytest.raises(ValidationError):
            BattleRules(turn_timer_seconds=301)

    def test_clause_enum_values(self):
        r = BattleRules(
            active_clauses=[ClauseID.DUPLICATE_SPECIES, ClauseID.SLEEP_LIMIT]
        )
        assert ClauseID.DUPLICATE_SPECIES in r.active_clauses
        assert ClauseID.SLEEP_LIMIT in r.active_clauses

    def test_level_cap_bounds(self):
        assert BattleRules(level_cap=10).level_cap == 10
        assert BattleRules(level_cap=100).level_cap == 100
        with pytest.raises(ValidationError):
            BattleRules(level_cap=9)
        with pytest.raises(ValidationError):
            BattleRules(level_cap=101)


class TestTournamentRules:
    def test_defaults(self):
        t = TournamentRules()
        assert t.bracket_size == 8
        assert t.check_in_duration_minutes == 15
        assert t.reconnect_grace_seconds == 90
        assert t.no_show_timeout_seconds == 120

    def test_valid_bracket_sizes(self):
        assert TournamentRules(bracket_size=8).bracket_size == 8
        assert TournamentRules(bracket_size=16).bracket_size == 16

    def test_invalid_bracket_size(self):
        with pytest.raises(ValidationError):
            TournamentRules(bracket_size=4)
        with pytest.raises(ValidationError):
            TournamentRules(bracket_size=32)


class TestHostConfig:
    def test_all_none_by_default(self):
        h = HostConfig()
        assert h.team_size is None
        assert h.level_cap is None
        assert h.turn_timer_seconds is None
        assert h.active_clauses is None
        assert h.allow_items_in_battle is None
        assert h.allow_held_items is None
        assert h.bracket_size is None

    def test_partial_override(self):
        h = HostConfig(team_size=3, level_cap=50)
        assert h.team_size == 3
        assert h.level_cap == 50
        assert h.turn_timer_seconds is None

    def test_bracket_size_validation(self):
        with pytest.raises(ValidationError):
            HostConfig(bracket_size=12)

    def test_timer_validation(self):
        with pytest.raises(ValidationError):
            HostConfig(turn_timer_seconds=10)


class TestModOverride:
    def test_all_none_by_default(self):
        m = ModOverride()
        assert m.team_size is None
        assert m.level_cap is None
        assert m.permadeath is None
        assert m.nuzlocke_mode is None

    def test_specific_override(self):
        m = ModOverride(level_cap=20, allow_items_in_battle=False)
        assert m.level_cap == 20
        assert m.allow_items_in_battle is False


class TestPlayerConfig:
    def test_defaults(self):
        p = PlayerConfig()
        assert p.encounter_rate_modifier == 1.0
        assert p.dialog_speed == "slow"
        assert p.difficulty == DifficultyPreset.NORMAL
        assert p.large_gui is False

    def test_encounter_rate_bounds(self):
        assert (
            PlayerConfig(encounter_rate_modifier=0.0).encounter_rate_modifier
            == 0.0
        )
        assert (
            PlayerConfig(encounter_rate_modifier=2.0).encounter_rate_modifier
            == 2.0
        )
        with pytest.raises(ValidationError):
            PlayerConfig(encounter_rate_modifier=2.1)
        with pytest.raises(ValidationError):
            PlayerConfig(encounter_rate_modifier=-0.1)


class TestResolvedRuleset:
    def test_frozen(self):
        rs = ResolvedRuleset(
            context=PlayContext.CAMPAIGN,
            battle=BattleRules(),
            tournament=TournamentRules(),
            encounter=EncounterRules(),
            campaign=CampaignRules(),
        )
        with pytest.raises(Exception):
            rs.context = PlayContext.TOURNAMENT  # type: ignore[misc]

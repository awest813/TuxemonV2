# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>

from tuxemon.rules.clause_sets import (
    default_clauses_for_context,
    optional_clauses_for_context,
)
from tuxemon.rules.match_confirmation import build_match_confirmation_snapshot
from tuxemon.rules.models import ClauseID, HostConfig, PlayContext
from tuxemon.rules.resolver import SettingsResolver


def test_context_clause_sets_are_stable():
    assert default_clauses_for_context(PlayContext.TOURNAMENT) == [
        ClauseID.DUPLICATE_SPECIES,
        ClauseID.SELF_KO_DRAW,
    ]
    assert optional_clauses_for_context(PlayContext.TOURNAMENT) == [
        ClauseID.DUPLICATE_ITEM,
        ClauseID.SLEEP_LIMIT,
        ClauseID.OHKO_BAN,
        ClauseID.EVASION_LIMIT,
    ]


def test_match_confirmation_snapshot_surfaces_rule_differences():
    host = HostConfig(
        team_size=3,
        level_cap=50,
        turn_timer_seconds=60,
        active_clauses=[ClauseID.OHKO_BAN],
        allow_items_in_battle=False,
    )
    resolved = SettingsResolver(
        context=PlayContext.CASUAL_ONLINE,
        host=host,
    ).resolve()

    snapshot = build_match_confirmation_snapshot(
        context=PlayContext.CASUAL_ONLINE,
        resolved_battle_rules=resolved.battle,
    )

    fields = {d.field for d in snapshot.differences}
    assert fields == {
        "team_size",
        "level_cap",
        "turn_timer_seconds",
        "active_clauses",
        "allow_items_in_battle",
    }


def test_match_confirmation_snapshot_has_no_diffs_for_pure_defaults():
    resolved = SettingsResolver(context=PlayContext.CAMPAIGN).resolve()

    snapshot = build_match_confirmation_snapshot(
        context=PlayContext.CAMPAIGN,
        resolved_battle_rules=resolved.battle,
    )

    assert snapshot.differences == []

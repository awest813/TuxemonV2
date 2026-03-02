# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""Helpers for surfacing resolved rule differences before match confirmation."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from tuxemon.rules.clause_sets import default_clauses_for_context
from tuxemon.rules.models import BattleRules, PlayContext


@dataclass(frozen=True)
class RuleDifference:
    """A single field difference between baseline and resolved battle rules."""

    field: str
    baseline: Any
    resolved: Any


@dataclass(frozen=True)
class MatchConfirmationSnapshot:
    """Battle-rule payload shown to players prior to match confirmation."""

    context: PlayContext
    baseline: BattleRules
    resolved: BattleRules
    differences: list[RuleDifference]


def build_match_confirmation_snapshot(
    context: PlayContext, resolved_battle_rules: BattleRules
) -> MatchConfirmationSnapshot:
    """Build a deterministic rule snapshot suitable for pre-match UI surfaces."""
    baseline = BattleRules(active_clauses=default_clauses_for_context(context))
    differences: list[RuleDifference] = []

    fields = (
        "team_size",
        "level_cap",
        "turn_timer_seconds",
        "active_clauses",
        "allow_items_in_battle",
        "allow_held_items",
    )
    for field in fields:
        baseline_value = getattr(baseline, field)
        resolved_value = getattr(resolved_battle_rules, field)
        if baseline_value != resolved_value:
            differences.append(
                RuleDifference(
                    field=field,
                    baseline=baseline_value,
                    resolved=resolved_value,
                )
            )

    return MatchConfirmationSnapshot(
        context=context,
        baseline=baseline,
        resolved=resolved_battle_rules,
        differences=differences,
    )


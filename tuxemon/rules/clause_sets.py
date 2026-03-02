# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""Default and optional clause sets by play context."""

from __future__ import annotations

from tuxemon.rules.models import ClauseID, PlayContext

_DEFAULT_CLAUSES_BY_CONTEXT: dict[PlayContext, list[ClauseID]] = {
    PlayContext.CAMPAIGN: [],
    PlayContext.CASUAL_ONLINE: [],
    PlayContext.TOURNAMENT: [
        ClauseID.DUPLICATE_SPECIES,
        ClauseID.SELF_KO_DRAW,
    ],
}

_OPTIONAL_CLAUSES_BY_CONTEXT: dict[PlayContext, list[ClauseID]] = {
    PlayContext.CAMPAIGN: [ClauseID.DUPLICATE_SPECIES],
    PlayContext.CASUAL_ONLINE: [
        ClauseID.DUPLICATE_SPECIES,
        ClauseID.DUPLICATE_ITEM,
        ClauseID.SLEEP_LIMIT,
        ClauseID.OHKO_BAN,
        ClauseID.EVASION_LIMIT,
        ClauseID.SELF_KO_DRAW,
    ],
    PlayContext.TOURNAMENT: [
        ClauseID.DUPLICATE_ITEM,
        ClauseID.SLEEP_LIMIT,
        ClauseID.OHKO_BAN,
        ClauseID.EVASION_LIMIT,
    ],
}


def default_clauses_for_context(context: PlayContext) -> list[ClauseID]:
    """Return rulebook default clauses for the given play context."""
    return list(_DEFAULT_CLAUSES_BY_CONTEXT[context])


def optional_clauses_for_context(context: PlayContext) -> list[ClauseID]:
    """Return clauses that are legal but not default for the context."""
    return list(_OPTIONAL_CLAUSES_BY_CONTEXT[context])


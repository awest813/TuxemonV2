# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Campaign starter templates.

Provides first-party campaign scaffolding content for the three supported
starter templates defined in docs/campaign_maker_mvp.md §3 Workflow F:

- ``blank``              — Empty scaffold (no extra content)
- ``classic_two_region`` — Two connected regions with gym progression
- ``battle_challenge``   — Single facility with 5 difficulty tiers
- ``event_adventure``    — Linear event-driven campaign with time-gated content

Templates are applied by CampaignTemplateEngine.apply() after the wizard
generates the base scaffold directory.
"""

from __future__ import annotations

from tuxemon.campaign.templates._base import CampaignTemplate
from tuxemon.campaign.templates.battle_challenge import BattleChallengeTemplate
from tuxemon.campaign.templates.classic_two_region import (
    ClassicTwoRegionTemplate,
)
from tuxemon.campaign.templates.event_adventure import EventAdventureTemplate

_REGISTRY: dict[str, CampaignTemplate] = {
    "blank": CampaignTemplate(
        name="blank",
        display_name="Blank Campaign",
        description="An empty scaffold with no pre-generated content.",
        features=[],
    ),
    "classic_two_region": ClassicTwoRegionTemplate(),
    "battle_challenge": BattleChallengeTemplate(),
    "event_adventure": EventAdventureTemplate(),
}


def get_template(name: str) -> CampaignTemplate:
    """
    Return the CampaignTemplate for *name*.

    Raises
    ------
    KeyError
        When *name* is not a registered template.
    """
    try:
        return _REGISTRY[name]
    except KeyError:
        raise KeyError(
            f"Unknown template '{name}'. "
            f"Available templates: {sorted(_REGISTRY)}"
        )


def list_templates() -> list[dict]:
    """Return metadata for all registered templates (for UI display)."""
    return [
        {
            "name": t.name,
            "display_name": t.display_name,
            "description": t.description,
            "features": t.features,
        }
        for t in _REGISTRY.values()
    ]


__all__ = [
    "CampaignTemplate",
    "ClassicTwoRegionTemplate",
    "BattleChallengeTemplate",
    "EventAdventureTemplate",
    "get_template",
    "list_templates",
]

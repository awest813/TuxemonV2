# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Campaign Maker package.

Provides Pydantic schema models for campaign manifests and the validator-backed
New Campaign Wizard prototype described in docs/campaign_maker_mvp.md.
"""
from tuxemon.campaign.models import (
    CampaignManifest,
    CampaignRulesetOverride,
    EncounterEntry,
    ScaffoldDirectory,
    WizardStep1,
    WizardStep2,
    WizardStep3,
)
from tuxemon.campaign.wizard import CampaignWizard, WizardValidationError

__all__ = [
    "CampaignManifest",
    "CampaignRulesetOverride",
    "CampaignWizard",
    "EncounterEntry",
    "ScaffoldDirectory",
    "WizardStep1",
    "WizardStep2",
    "WizardStep3",
    "WizardValidationError",
]

# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Campaign Maker package — Phase 3 Implementation.

Provides the full Campaign Maker toolchain as described in
docs/campaign_maker_mvp.md:

Schema models and wizard (Phase 1):
    CampaignManifest, CampaignRulesetOverride, EncounterEntry, ScaffoldDirectory
    WizardStep1, WizardStep2, WizardStep3
    CampaignWizard, WizardValidationError

Campaign validation and linting (Phase 3 §3.3):
    CampaignValidator, ValidationReport, ValidationIssue, Severity
    CampaignLinter, LintReport, LintIssue

Build pipeline (Phase 3 §3.2):
    CampaignBuilder, BuildResult

Import and compatibility (Phase 3 §3.2):
    CampaignImporter, CompatibilityResult, ImportResult

Event authoring (Phase 3 §3.1):
    EventGraph, EventNode, EventTrigger, EventGraphBuilder
    ActionType, TriggerType

Encounter table editor (Phase 3 §3.1):
    EncounterTable, EncounterZone, EncounterTableBuilder

Starter templates (Phase 3 §3.1):
    ClassicTwoRegionTemplate, BattleChallengeTemplate, EventAdventureTemplate
    get_template, list_templates

Smoke test harness (Phase 3 §3.3):
    CampaignSmokeTest, SmokeTestResult, SmokeCheck
"""
from tuxemon.campaign.builder import BuildResult, CampaignBuilder
from tuxemon.campaign.encounter_editor import (
    EncounterTable,
    EncounterTableBuilder,
    EncounterZone,
)
from tuxemon.campaign.event_graph import (
    ActionType,
    EventGraph,
    EventGraphBuilder,
    EventNode,
    EventTrigger,
    TriggerType,
)
from tuxemon.campaign.importer import (
    CampaignImporter,
    CompatibilityResult,
    ImportResult,
)
from tuxemon.campaign.linter import CampaignLinter, LintIssue, LintReport
from tuxemon.campaign.models import (
    CampaignManifest,
    CampaignRulesetOverride,
    EncounterEntry,
    ScaffoldDirectory,
    WizardStep1,
    WizardStep2,
    WizardStep3,
)
from tuxemon.campaign.smoke_test import CampaignSmokeTest, SmokeCheck, SmokeTestResult
from tuxemon.campaign.templates import (
    BattleChallengeTemplate,
    CampaignTemplate,
    ClassicTwoRegionTemplate,
    EventAdventureTemplate,
    get_template,
    list_templates,
)
from tuxemon.campaign.validator import (
    CampaignValidator,
    Severity,
    ValidationIssue,
    ValidationReport,
)
from tuxemon.campaign.wizard import CampaignWizard, WizardValidationError

__all__ = [
    # Schema models
    "CampaignManifest",
    "CampaignRulesetOverride",
    "EncounterEntry",
    "ScaffoldDirectory",
    "WizardStep1",
    "WizardStep2",
    "WizardStep3",
    # Wizard
    "CampaignWizard",
    "WizardValidationError",
    # Validator
    "CampaignValidator",
    "Severity",
    "ValidationIssue",
    "ValidationReport",
    # Linter
    "CampaignLinter",
    "LintIssue",
    "LintReport",
    # Builder
    "BuildResult",
    "CampaignBuilder",
    # Importer
    "CampaignImporter",
    "CompatibilityResult",
    "ImportResult",
    # Event graph
    "ActionType",
    "EventGraph",
    "EventGraphBuilder",
    "EventNode",
    "EventTrigger",
    "TriggerType",
    # Encounter editor
    "EncounterTable",
    "EncounterTableBuilder",
    "EncounterZone",
    # Templates
    "BattleChallengeTemplate",
    "CampaignTemplate",
    "ClassicTwoRegionTemplate",
    "EventAdventureTemplate",
    "get_template",
    "list_templates",
    # Smoke test
    "CampaignSmokeTest",
    "SmokeCheck",
    "SmokeTestResult",
]

# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Campaign linter — automated lint/validation for custom campaigns.

The linter wraps CampaignValidator and provides:
- A structured, machine-readable lint report.
- A human-readable formatted output suitable for CLI tools and CI pipelines.
- Non-zero exit-code semantics when blocking issues are found.

Implements the §3.3 Quality Gate requirement from ROADMAP.md.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Optional

from tuxemon.campaign.validator import (
    CampaignValidator,
    Severity,
    ValidationReport,
)

logger = logging.getLogger(__name__)

# Lint rule categories (maps to validation check_id prefixes)
LINT_CATEGORIES = {
    "manifest": "Manifest correctness",
    "map": "Map structure",
    "encounter": "Encounter tables",
    "script": "Event scripts",
    "campaign": "Campaign-level integrity",
}


@dataclass
class LintIssue:
    """A single lint issue with full context for reporting."""

    severity: str
    check_id: str
    message: str
    path: Optional[str] = None
    category: str = "general"
    hint: Optional[str] = None


# Actionable hints keyed by check_id for common validation failures.
LINT_HINTS: dict[str, str] = {
    "campaign_dir_missing": (
        "Verify the path passed to the linter points to an existing directory."
    ),
    "manifest_missing": (
        "Create a campaign.yaml file at the root of your campaign directory. "
        "Run the campaign wizard (`campaign-wizard init`) to generate a starter manifest."
    ),
    "manifest_parse_error": (
        "Ensure campaign.yaml is valid YAML. "
        "Check for stray tabs, unquoted special characters, or mismatched indentation."
    ),
    "manifest_not_mapping": (
        "campaign.yaml must start with key-value pairs, not a list or scalar. "
        "Example: `id: my_campaign`."
    ),
    "manifest_field_invalid": (
        "Check the campaign manifest schema. "
        "Required fields include: id, name, version, author, engine_min_version, "
        "description, start_map, entry_script."
    ),
    "engine_version_incompatible": (
        "Update `engine_min_version` in campaign.yaml to match the installed engine "
        "version, or upgrade the engine."
    ),
    "maps_dir_missing": (
        "Create a maps/ subdirectory inside your campaign directory and add at least one .tmx map."
    ),
    "no_maps_found": (
        "Add at least one Tiled map (.tmx) to the maps/ directory."
    ),
    "map_parse_error": (
        "Ensure the .tmx file is valid XML. Re-export from Tiled or check for "
        "encoding issues."
    ),
    "map_id_unique": (
        "Each map must have a unique `slug` property in its Tiled properties panel."
    ),
    "spawn_point_exists": (
        "Open the map in Tiled and add an object of type `spawn_point` to the Events objectgroup."
    ),
    "transition_target_valid": (
        "Ensure the referenced map file exists in the maps/ directory. "
        "Check the teleport trigger's `target` field for typos."
    ),
    "npc_script_valid": (
        "Ensure the referenced script ID exists as a JSON file in scripts/ "
        "and that its `id` field matches the reference."
    ),
    "start_map_reachable": (
        "Set `start_map` in campaign.yaml to a path relative to the campaign root, "
        "e.g. `maps/start.tmx`."
    ),
    "entry_script_missing": (
        "Create a script file in scripts/ whose `id` field matches `entry_script` "
        "in campaign.yaml."
    ),
    "script_parse_error": (
        "Ensure the script file is valid JSON. Use a JSON validator or linter to locate syntax errors."
    ),
    "script_not_object": (
        "Script files must be a JSON object (`{}`), not an array or primitive."
    ),
    "script_id_missing": (
        "Add an `id` string field to the script JSON, e.g. `\"id\": \"my_script\"`."
    ),
    "script_id_unique": (
        "Each script must have a unique `id`. Rename one of the conflicting scripts."
    ),
    "script_action_valid": (
        "Check the action type against the list of supported action types in the campaign docs."
    ),
    "script_loop_detected": (
        "A script calls itself (directly or indirectly). "
        "Restructure the call graph to remove the cycle."
    ),
    "encounter_zone_valid": (
        "Add at least one monster ID to the encounter zone's `monsters` property in Tiled."
    ),
    "monster_id_valid": (
        "Verify the monster ID is spelled correctly and exists in the game database."
    ),
    "ruleset_valid": (
        "Check the `ruleset` block in campaign.yaml against the BattleRules schema. "
        "Valid fields: team_size, level_cap, active_clauses, allow_items_in_battle, allow_held_items."
    ),
    "no_unreachable_maps": (
        "Add a map transition or teleport trigger that connects this map to the rest of the campaign."
    ),
    "layer_naming_convention": (
        "Rename the layer to follow the time-aware naming convention "
        "(`ground_day`, `ground_night`, `ground_morning`, etc.) or remove the "
        "ambiguous prefix."
    ),
}


@dataclass
class LintReport:
    """
    Structured lint report produced by CampaignLinter.

    Attributes
    ----------
    campaign_dir:
        The campaign directory that was linted.
    passed:
        True when no blocking issues were found.
    issues:
        All lint issues ordered by severity (blocking first).
    stats:
        Summary counts by severity.
    """

    campaign_dir: Optional[Path] = None
    passed: bool = True
    issues: list[LintIssue] = field(default_factory=list)
    stats: dict[str, int] = field(default_factory=dict)

    @property
    def blocking(self) -> list[LintIssue]:
        return [
            i for i in self.issues if i.severity == Severity.BLOCKING.value
        ]

    @property
    def warnings(self) -> list[LintIssue]:
        return [i for i in self.issues if i.severity == Severity.WARNING.value]

    @property
    def infos(self) -> list[LintIssue]:
        return [i for i in self.issues if i.severity == Severity.INFO.value]

    def to_json(self, *, indent: int = 2) -> str:
        """Serialize to JSON for machine consumption."""
        data = {
            "campaign_dir": (
                str(self.campaign_dir) if self.campaign_dir else None
            ),
            "passed": self.passed,
            "stats": self.stats,
            "issues": [asdict(i) for i in self.issues],
        }
        return json.dumps(data, indent=indent)

    def format_human(self, *, color: bool = False) -> str:
        """
        Return a human-readable formatted lint report.

        When *color* is True, ANSI escape codes are added for terminal output.
        """
        RESET = "\033[0m" if color else ""
        RED = "\033[91m" if color else ""
        YELLOW = "\033[93m" if color else ""
        CYAN = "\033[96m" if color else ""
        BOLD = "\033[1m" if color else ""
        GREEN = "\033[92m" if color else ""

        lines: list[str] = []
        dir_label = (
            str(self.campaign_dir) if self.campaign_dir else "(unknown)"
        )
        lines.append(f"{BOLD}Campaign Lint Report: {dir_label}{RESET}")
        lines.append("-" * 60)

        if not self.issues:
            lines.append(f"{GREEN}No issues found. Campaign is clean.{RESET}")
        else:
            for issue in self.issues:
                if issue.severity == Severity.BLOCKING.value:
                    prefix = f"{RED}[BLOCKING]{RESET}"
                elif issue.severity == Severity.WARNING.value:
                    prefix = f"{YELLOW}[ WARNING]{RESET}"
                else:
                    prefix = f"{CYAN}[   INFO ]{RESET}"

                loc = f" {issue.path}" if issue.path else ""
                lines.append(
                    f"{prefix} {issue.check_id}{loc}: {issue.message}"
                )
                if issue.hint:
                    hint_color = "\033[2m" if color else ""
                    lines.append(f"  {hint_color}Hint: {issue.hint}{RESET}")

        lines.append("-" * 60)
        b = self.stats.get("blocking", 0)
        w = self.stats.get("warnings", 0)
        i = self.stats.get("info", 0)
        result_color = GREEN if self.passed else RED
        lines.append(
            f"{result_color}{'PASSED' if self.passed else 'FAILED'}{RESET} "
            f"— {b} blocking, {w} warnings, {i} info"
        )
        return "\n".join(lines)


def _categorize(check_id: str) -> str:
    """Map a check_id to a lint category label."""
    if any(check_id.startswith(p) for p in ("manifest", "engine_version")):
        return "manifest"
    if any(
        check_id.startswith(p)
        for p in ("map_", "layer_", "orphan", "spawn", "transition")
    ):
        return "map"
    if any(
        check_id.startswith(p)
        for p in ("encounter", "monster", "time_", "season_", "weekday_")
    ):
        return "encounter"
    if any(
        check_id.startswith(p)
        for p in ("script_", "localization", "entry_script")
    ):
        return "script"
    if any(
        check_id.startswith(p)
        for p in (
            "start_map",
            "no_unreachable",
            "ruleset",
            "weekly_event",
            "trainer",
        )
    ):
        return "campaign"
    return "general"


class CampaignLinter:
    """
    Runs all campaign validation checks and produces a LintReport.

    Usage::

        linter = CampaignLinter()
        report = linter.lint(Path("~/campaigns/my_campaign"))
        print(report.format_human(color=True))
        if not report.passed:
            sys.exit(1)

    Parameters
    ----------
    validator:
        An optional pre-configured CampaignValidator. When None, a default
        validator is created.
    """

    def __init__(self, validator: Optional[CampaignValidator] = None) -> None:
        self._validator = validator or CampaignValidator()

    def lint(self, campaign_dir: Path) -> LintReport:
        """
        Lint the campaign at *campaign_dir* and return a LintReport.
        """
        validation_report: ValidationReport = self._validator.validate(
            campaign_dir
        )
        issues: list[LintIssue] = []

        for vi in validation_report.issues:
            issues.append(
                LintIssue(
                    severity=vi.severity.value,
                    check_id=vi.check_id,
                    message=vi.message,
                    path=vi.path,
                    category=_categorize(vi.check_id),
                    hint=LINT_HINTS.get(vi.check_id),
                )
            )

        # Sort: blocking first, then warnings, then info
        severity_order = {
            Severity.BLOCKING.value: 0,
            Severity.WARNING.value: 1,
            Severity.INFO.value: 2,
        }
        issues.sort(key=lambda i: severity_order.get(i.severity, 3))

        stats = {
            "blocking": len(validation_report.blocking),
            "warnings": len(validation_report.warnings),
            "info": len(validation_report.infos),
        }

        return LintReport(
            campaign_dir=campaign_dir,
            passed=validation_report.is_valid,
            issues=issues,
            stats=stats,
        )

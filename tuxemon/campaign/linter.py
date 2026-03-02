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

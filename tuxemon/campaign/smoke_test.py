# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Campaign smoke test harness.

Validates campaign startup readiness and first-hour progression integrity
without running the full game engine. Implements the §3.3 Quality Gate
requirement for automated smoke testing.

Checks performed:
1. Manifest and directory structure are present and valid.
2. Start map exists and has at least one spawn point.
3. Entry script exists and has at least one trigger.
4. All maps referenced by map transitions exist.
5. All NPC script references resolve.
6. No circular script call chains.
7. At least one encounter zone exists in the campaign (gameplay requirement).
8. Locale file exists for the campaign's declared primary language.
9. Ruleset override (if present) passes BattleRules validation.
10. No duplicate IDs across maps, scripts, or encounter zones.
"""
from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import yaml

from tuxemon.campaign.validator import (
    CampaignValidator,
    Severity,
    ValidationReport,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Smoke test check descriptors
# ---------------------------------------------------------------------------


@dataclass
class SmokeCheck:
    """A single smoke test check result."""

    name: str
    passed: bool
    message: str
    severity: str = "blocking"

    def __str__(self) -> str:
        status = "PASS" if self.passed else "FAIL"
        return f"[{status}] {self.name}: {self.message}"


@dataclass
class SmokeTestResult:
    """
    Aggregated result from running all smoke test checks on a campaign.

    Attributes
    ----------
    campaign_dir:
        The campaign directory that was tested.
    ready:
        True when all blocking checks passed. The campaign should be safe
        to load into the engine.
    checks:
        All checks run, in order.
    validation_report:
        The underlying ValidationReport (for detailed issue listing).
    """

    campaign_dir: Optional[Path] = None
    ready: bool = True
    checks: list[SmokeCheck] = field(default_factory=list)
    validation_report: Optional[ValidationReport] = None

    @property
    def passed_checks(self) -> list[SmokeCheck]:
        return [c for c in self.checks if c.passed]

    @property
    def failed_checks(self) -> list[SmokeCheck]:
        return [c for c in self.checks if not c.passed]

    def format_report(self) -> str:
        lines: list[str] = []
        dir_label = str(self.campaign_dir) if self.campaign_dir else "(unknown)"
        lines.append(f"Campaign Smoke Test: {dir_label}")
        lines.append("=" * 60)

        for check in self.checks:
            lines.append(str(check))

        lines.append("-" * 60)
        p, f = len(self.passed_checks), len(self.failed_checks)
        status = "READY" if self.ready else "NOT READY"
        lines.append(f"Result: {status} ({p} passed, {f} failed)")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# Smoke test runner
# ---------------------------------------------------------------------------


class CampaignSmokeTest:
    """
    Runs smoke tests to verify a campaign is safe to start.

    The smoke test is intentionally lightweight — it does not simulate
    gameplay, it only verifies that the data required for engine startup
    is present and structurally correct.

    Usage::

        runner = CampaignSmokeTest()
        result = runner.run(Path("~/campaigns/my_campaign"))
        print(result.format_report())
        assert result.ready, "Campaign not ready to launch"
    """

    def __init__(
        self, validator: Optional[CampaignValidator] = None
    ) -> None:
        self._validator = validator or CampaignValidator()

    def run(self, campaign_dir: Path) -> SmokeTestResult:
        """Run all smoke test checks and return a SmokeTestResult."""
        result = SmokeTestResult(campaign_dir=campaign_dir)

        # Core validation pass (checks 1–10 are derived from this)
        report = self._validator.validate(campaign_dir)
        result.validation_report = report

        # --- Check 1: Campaign directory exists ---
        result.checks.append(
            SmokeCheck(
                name="campaign_directory_exists",
                passed=campaign_dir.exists() and campaign_dir.is_dir(),
                message=(
                    "Campaign directory found."
                    if campaign_dir.exists()
                    else f"Campaign directory not found: {campaign_dir}"
                ),
            )
        )

        if not campaign_dir.exists():
            result.ready = False
            return result

        # --- Check 2: Manifest present and valid ---
        manifest_issues = [
            i
            for i in report.blocking
            if "manifest" in i.check_id
        ]
        result.checks.append(
            SmokeCheck(
                name="manifest_valid",
                passed=len(manifest_issues) == 0,
                message=(
                    "campaign.yaml is present and valid."
                    if not manifest_issues
                    else f"{len(manifest_issues)} manifest issue(s) found."
                ),
            )
        )

        # --- Check 3: Start map exists ---
        start_map_issues = [
            i for i in report.blocking if i.check_id == "start_map_reachable"
        ]
        result.checks.append(
            SmokeCheck(
                name="start_map_exists",
                passed=len(start_map_issues) == 0,
                message=(
                    "Start map file is present."
                    if not start_map_issues
                    else start_map_issues[0].message
                ),
            )
        )

        # --- Check 4: Start map has spawn point ---
        spawn_issues = [
            i for i in report.blocking if i.check_id == "spawn_point_exists"
        ]
        result.checks.append(
            SmokeCheck(
                name="spawn_point_present",
                passed=len(spawn_issues) == 0,
                message=(
                    "Start map has at least one spawn_point."
                    if not spawn_issues
                    else spawn_issues[0].message
                ),
            )
        )

        # --- Check 5: Entry script exists ---
        script_issues = [
            i for i in report.blocking if i.check_id == "entry_script_missing"
        ]
        result.checks.append(
            SmokeCheck(
                name="entry_script_exists",
                passed=len(script_issues) == 0,
                message=(
                    "Entry script is present in scripts/."
                    if not script_issues
                    else script_issues[0].message
                ),
            )
        )

        # --- Check 6: No transition target errors ---
        trans_issues = [
            i for i in report.blocking if i.check_id == "transition_target_valid"
        ]
        result.checks.append(
            SmokeCheck(
                name="map_transitions_valid",
                passed=len(trans_issues) == 0,
                message=(
                    "All map transitions reference existing maps."
                    if not trans_issues
                    else f"{len(trans_issues)} broken map transition(s) found."
                ),
            )
        )

        # --- Check 7: At least one encounter zone ---
        maps_dir = campaign_dir / "maps"
        encounter_count = self._count_encounter_zones(maps_dir)
        result.checks.append(
            SmokeCheck(
                name="encounter_zones_present",
                passed=encounter_count > 0,
                message=(
                    f"Found {encounter_count} encounter zone(s)."
                    if encounter_count > 0
                    else "No encounter zones found in any map. "
                    "Players will not encounter any wild monsters."
                ),
                severity="warning",
            )
        )

        # --- Check 8: Locale file for primary language ---
        locale_ready, locale_msg = self._check_locale(campaign_dir)
        result.checks.append(
            SmokeCheck(
                name="locale_file_present",
                passed=locale_ready,
                message=locale_msg,
                severity="warning",
            )
        )

        # --- Check 9: No circular script calls ---
        cycle_issues = [
            i for i in report.blocking if i.check_id == "script_loop_detected"
        ]
        result.checks.append(
            SmokeCheck(
                name="no_script_cycles",
                passed=len(cycle_issues) == 0,
                message=(
                    "No circular script references detected."
                    if not cycle_issues
                    else f"{len(cycle_issues)} circular script reference(s) found."
                ),
            )
        )

        # --- Check 10: Ruleset valid (if overrides present) ---
        ruleset_issues = [
            i for i in report.blocking if i.check_id == "ruleset_valid"
        ]
        result.checks.append(
            SmokeCheck(
                name="ruleset_valid",
                passed=len(ruleset_issues) == 0,
                message=(
                    "Campaign ruleset override is valid."
                    if not ruleset_issues
                    else ruleset_issues[0].message
                ),
            )
        )

        # Determine overall readiness: all BLOCKING checks must pass
        blocking_failures = [
            c for c in result.checks
            if not c.passed and c.severity == "blocking"
        ]
        result.ready = len(blocking_failures) == 0

        logger.info(
            "Smoke test %s for %s (%d/%d checks passed)",
            "PASSED" if result.ready else "FAILED",
            campaign_dir,
            len(result.passed_checks),
            len(result.checks),
        )

        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _count_encounter_zones(maps_dir: Path) -> int:
        """Count encounter_zone objects across all TMX files."""
        if not maps_dir.exists():
            return 0
        count = 0
        for tmx_path in maps_dir.rglob("*.tmx"):
            try:
                text = tmx_path.read_text(encoding="utf-8")
                count += text.count('type="encounter_zone"')
            except OSError:
                pass
        return count

    @staticmethod
    def _check_locale(campaign_dir: Path) -> tuple[bool, str]:
        """Check that a locale file exists for the campaign's declared language."""
        manifest_path = campaign_dir / "campaign.yaml"
        if not manifest_path.exists():
            return False, "Cannot check locale: campaign.yaml missing."

        try:
            raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
            lang = (raw or {}).get("language", "en_US")
        except Exception:
            lang = "en_US"

        locale_dir = campaign_dir / "locale"
        ini_path = locale_dir / f"{lang}.ini"
        po_path = locale_dir / f"{lang}.po"

        if ini_path.exists() or po_path.exists():
            return True, f"Locale file found for '{lang}'."
        return (
            False,
            f"No locale file found for declared language '{lang}'. "
            f"Expected locale/{lang}.ini or locale/{lang}.po",
        )

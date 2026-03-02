# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for tuxemon.campaign.linter — CampaignLinter.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from tuxemon.campaign.linter import CampaignLinter, LintReport

VALID_MANIFEST = {
    "id": "lint_test",
    "name": "Lint Test Campaign",
    "version": "1.0.0",
    "author": "Lint Tester",
    "engine_min_version": "0.4.35",
    "description": "A campaign for testing the linter pipeline.",
    "start_map": "maps/start.tmx",
    "entry_script": "main_intro",
}

MINIMAL_TMX = """\
<?xml version="1.0" encoding="UTF-8"?>
<map version="1.10" width="5" height="5" tilewidth="16" tileheight="16"
     nextlayerid="3" nextobjectid="3">
 <properties>
  <property name="slug" value="start"/>
 </properties>
 <layer id="1" name="ground" width="5" height="5">
  <data encoding="csv">1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1,1</data>
 </layer>
 <objectgroup id="2" name="Events">
  <object id="1" type="spawn_point" x="32" y="32" width="16" height="16"/>
 </objectgroup>
</map>
"""

MINIMAL_SCRIPT = {
    "id": "main_intro",
    "triggers": [{"type": "game_start", "args": {}}],
    "nodes": [
        {"id": "n", "action": "dialog", "args": {"text_key": "k"}, "next": None, "branches": {}}
    ],
}


def _make_valid_campaign(tmp_path: Path) -> Path:
    campaign_dir = tmp_path / "lint_test"
    (campaign_dir / "maps").mkdir(parents=True)
    (campaign_dir / "scripts").mkdir(parents=True)
    (campaign_dir / "campaign.yaml").write_text(yaml.dump(VALID_MANIFEST))
    (campaign_dir / "maps" / "start.tmx").write_text(MINIMAL_TMX)
    (campaign_dir / "scripts" / "main_intro.json").write_text(json.dumps(MINIMAL_SCRIPT))
    return campaign_dir


class TestLintReport:
    def test_passed_report_no_issues(self):
        report = LintReport(passed=True)
        assert report.blocking == []
        assert report.warnings == []
        assert report.infos == []

    def test_format_human_pass(self):
        report = LintReport(passed=True, stats={"blocking": 0, "warnings": 0, "info": 0})
        output = report.format_human()
        assert "PASSED" in output

    def test_format_human_fail(self):
        from tuxemon.campaign.linter import LintIssue
        from tuxemon.campaign.validator import Severity

        report = LintReport(
            passed=False,
            stats={"blocking": 1, "warnings": 0, "info": 0},
            issues=[
                LintIssue(
                    severity=Severity.BLOCKING.value,
                    check_id="test_check",
                    message="Something is wrong.",
                    category="manifest",
                )
            ],
        )
        output = report.format_human()
        assert "FAILED" in output
        assert "BLOCKING" in output

    def test_to_json_serializable(self):
        import json as json_mod

        report = LintReport(
            passed=True,
            stats={"blocking": 0, "warnings": 0, "info": 0},
        )
        raw = report.to_json()
        parsed = json_mod.loads(raw)
        assert parsed["passed"] is True
        assert "stats" in parsed

    def test_color_output_flag(self):
        report = LintReport(passed=True, stats={"blocking": 0, "warnings": 0, "info": 0})
        plain = report.format_human(color=False)
        colored = report.format_human(color=True)
        assert "\033[" in colored
        assert "\033[" not in plain


class TestCampaignLinter:
    def test_lint_valid_campaign_passes(self, tmp_path):
        campaign_dir = _make_valid_campaign(tmp_path)
        linter = CampaignLinter()
        report = linter.lint(campaign_dir)
        assert report.passed, report.format_human()

    def test_lint_invalid_campaign_fails(self, tmp_path):
        campaign_dir = tmp_path / "bad_campaign"
        campaign_dir.mkdir()
        (campaign_dir / "campaign.yaml").write_text(
            yaml.dump({"id": "x", "name": "y"}), encoding="utf-8"
        )
        linter = CampaignLinter()
        report = linter.lint(campaign_dir)
        assert not report.passed
        assert len(report.blocking) > 0

    def test_lint_sorts_blocking_first(self, tmp_path):
        campaign_dir = _make_valid_campaign(tmp_path)
        # Add an orphan map to produce a warning
        orphan_tmx = MINIMAL_TMX.replace('value="start"', 'value="orphan"')
        (campaign_dir / "maps" / "orphan.tmx").write_text(orphan_tmx)
        # Replace start.tmx with no spawn to produce a blocking error
        no_spawn = MINIMAL_TMX.replace(
            '<object id="1" type="spawn_point" x="32" y="32" width="16" height="16"/>',
            "",
        )
        (campaign_dir / "maps" / "start.tmx").write_text(no_spawn)

        linter = CampaignLinter()
        report = linter.lint(campaign_dir)
        if report.issues:
            # Blocking should come before warnings
            severities = [i.severity for i in report.issues]
            blocking_idx = [i for i, s in enumerate(severities) if s == "blocking"]
            warning_idx = [i for i, s in enumerate(severities) if s == "warning"]
            if blocking_idx and warning_idx:
                assert max(blocking_idx) < min(warning_idx)

    def test_lint_stats_populated(self, tmp_path):
        campaign_dir = _make_valid_campaign(tmp_path)
        linter = CampaignLinter()
        report = linter.lint(campaign_dir)
        assert "blocking" in report.stats
        assert "warnings" in report.stats
        assert "info" in report.stats

    def test_lint_nonexistent_dir(self, tmp_path):
        linter = CampaignLinter()
        report = linter.lint(tmp_path / "ghost")
        assert not report.passed

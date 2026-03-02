# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for tuxemon.campaign.smoke_test — CampaignSmokeTest.
"""

from __future__ import annotations

import json
import textwrap
from pathlib import Path

import yaml

from tuxemon.campaign.smoke_test import (
    CampaignSmokeTest,
    SmokeCheck,
    SmokeTestResult,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_MANIFEST = {
    "id": "smoke_test_campaign",
    "name": "Smoke Test Campaign",
    "version": "1.0.0",
    "author": "Smoke Tester",
    "engine_min_version": "0.4.35",
    "description": "A campaign for testing the smoke test harness.",
    "start_map": "maps/start.tmx",
    "entry_script": "main_intro",
    "language": "en_US",
}

MINIMAL_TMX_WITH_SPAWN = textwrap.dedent("""\
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
      <object id="2" type="encounter_zone" x="0" y="0" width="80" height="80">
       <properties>
        <property name="monster_ids" value="porcupinito"/>
       </properties>
      </object>
     </objectgroup>
    </map>
    """)

MINIMAL_SCRIPT = {
    "id": "main_intro",
    "triggers": [{"type": "game_start", "args": {}}],
    "nodes": [
        {
            "id": "n",
            "action": "dialog",
            "args": {"text_key": "intro.greeting"},
            "next": None,
            "branches": {},
        }
    ],
}


def _make_campaign(tmp_path: Path, **opts) -> Path:
    campaign_dir = tmp_path / "smoke_test_campaign"
    maps_dir = campaign_dir / "maps"
    scripts_dir = campaign_dir / "scripts"
    locale_dir = campaign_dir / "locale"

    for d in [campaign_dir, maps_dir, scripts_dir, locale_dir]:
        d.mkdir(parents=True, exist_ok=True)

    manifest = {**VALID_MANIFEST, **opts.get("manifest", {})}
    (campaign_dir / "campaign.yaml").write_text(
        yaml.dump(manifest), encoding="utf-8"
    )

    tmx_content = opts.get("tmx", MINIMAL_TMX_WITH_SPAWN)
    (maps_dir / "start.tmx").write_text(tmx_content, encoding="utf-8")

    if opts.get("write_script", True):
        (scripts_dir / "main_intro.json").write_text(
            json.dumps(MINIMAL_SCRIPT), encoding="utf-8"
        )

    if opts.get("write_locale", True):
        (locale_dir / "en_US.ini").write_text(
            '[strings]\nintro.greeting = "Hello!"\n', encoding="utf-8"
        )

    return campaign_dir


# ---------------------------------------------------------------------------
# SmokeCheck tests
# ---------------------------------------------------------------------------


class TestSmokeCheck:
    def test_str_pass(self):
        c = SmokeCheck(name="my_check", passed=True, message="All good.")
        assert "[PASS]" in str(c)
        assert "my_check" in str(c)

    def test_str_fail(self):
        c = SmokeCheck(
            name="my_check", passed=False, message="Something wrong."
        )
        assert "[FAIL]" in str(c)


class TestSmokeTestResult:
    def test_format_report_ready(self):
        result = SmokeTestResult(ready=True)
        result.checks.append(SmokeCheck("check_a", True, "Passed!"))
        report = result.format_report()
        assert "READY" in report

    def test_format_report_not_ready(self):
        result = SmokeTestResult(ready=False)
        result.checks.append(SmokeCheck("check_a", False, "Failed!"))
        report = result.format_report()
        assert "NOT READY" in report

    def test_passed_checks_filtered(self):
        result = SmokeTestResult()
        result.checks = [
            SmokeCheck("a", True, "ok"),
            SmokeCheck("b", False, "fail"),
            SmokeCheck("c", True, "ok"),
        ]
        assert len(result.passed_checks) == 2
        assert len(result.failed_checks) == 1


# ---------------------------------------------------------------------------
# CampaignSmokeTest tests
# ---------------------------------------------------------------------------


class TestCampaignSmokeTest:
    def test_valid_campaign_is_ready(self, tmp_path):
        campaign_dir = _make_campaign(tmp_path)
        runner = CampaignSmokeTest()
        result = runner.run(campaign_dir)
        assert result.ready, result.format_report()

    def test_all_checks_run(self, tmp_path):
        campaign_dir = _make_campaign(tmp_path)
        runner = CampaignSmokeTest()
        result = runner.run(campaign_dir)
        assert len(result.checks) >= 10

    def test_missing_dir_not_ready(self, tmp_path):
        runner = CampaignSmokeTest()
        result = runner.run(tmp_path / "ghost_campaign")
        assert not result.ready

    def test_missing_dir_stops_early(self, tmp_path):
        runner = CampaignSmokeTest()
        result = runner.run(tmp_path / "ghost_campaign")
        # Should have checked for dir existence and returned early
        assert any(
            c.name == "campaign_directory_exists" for c in result.checks
        )

    def test_invalid_manifest_not_ready(self, tmp_path):
        campaign_dir = _make_campaign(tmp_path, manifest={"id": "bad id!"})
        runner = CampaignSmokeTest()
        result = runner.run(campaign_dir)
        assert not result.ready
        assert any(
            c.name == "manifest_valid" and not c.passed for c in result.checks
        )

    def test_missing_start_map_not_ready(self, tmp_path):
        campaign_dir = _make_campaign(
            tmp_path, manifest={"start_map": "maps/ghost.tmx"}
        )
        runner = CampaignSmokeTest()
        result = runner.run(campaign_dir)
        assert not result.ready
        assert any(
            c.name == "start_map_exists" and not c.passed
            for c in result.checks
        )

    def test_missing_spawn_point_not_ready(self, tmp_path):
        no_spawn_tmx = MINIMAL_TMX_WITH_SPAWN.replace(
            '<object id="1" type="spawn_point" x="32" y="32" width="16" height="16"/>',
            "",
        )
        campaign_dir = _make_campaign(tmp_path, tmx=no_spawn_tmx)
        runner = CampaignSmokeTest()
        result = runner.run(campaign_dir)
        assert not result.ready
        assert any(
            c.name == "spawn_point_present" and not c.passed
            for c in result.checks
        )

    def test_encounter_zone_present_passes(self, tmp_path):
        campaign_dir = _make_campaign(tmp_path)
        runner = CampaignSmokeTest()
        result = runner.run(campaign_dir)
        enc_check = next(
            (c for c in result.checks if c.name == "encounter_zones_present"),
            None,
        )
        assert enc_check is not None
        assert enc_check.passed

    def test_locale_present_passes(self, tmp_path):
        campaign_dir = _make_campaign(tmp_path)
        runner = CampaignSmokeTest()
        result = runner.run(campaign_dir)
        locale_check = next(
            (c for c in result.checks if c.name == "locale_file_present"), None
        )
        assert locale_check is not None
        assert locale_check.passed

    def test_locale_missing_does_not_fail_ready(self, tmp_path):
        """Missing locale is a warning-severity check — campaign should still be ready."""
        campaign_dir = _make_campaign(tmp_path, write_locale=False)
        runner = CampaignSmokeTest()
        result = runner.run(campaign_dir)
        locale_check = next(
            (c for c in result.checks if c.name == "locale_file_present"), None
        )
        assert locale_check is not None
        assert not locale_check.passed
        assert locale_check.severity == "warning"
        # Campaign is still ready (locale is a warning, not blocking)
        assert result.ready

    def test_entry_script_missing_not_ready(self, tmp_path):
        campaign_dir = _make_campaign(
            tmp_path,
            manifest={"entry_script": "nonexistent_script"},
        )
        runner = CampaignSmokeTest()
        result = runner.run(campaign_dir)
        assert not result.ready
        assert any(
            c.name == "entry_script_exists" and not c.passed
            for c in result.checks
        )

    def test_validation_report_attached(self, tmp_path):
        campaign_dir = _make_campaign(tmp_path)
        runner = CampaignSmokeTest()
        result = runner.run(campaign_dir)
        assert result.validation_report is not None

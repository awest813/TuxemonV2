# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for tuxemon.campaign.builder — CampaignBuilder.
"""

from __future__ import annotations

import json
import textwrap
import zipfile
from pathlib import Path

import yaml

from tuxemon.campaign.builder import (
    CAPSULE_EXTENSION,
    BuildResult,
    CampaignBuilder,
)

# ---------------------------------------------------------------------------
# Helpers (shared with test_validator)
# ---------------------------------------------------------------------------

VALID_MANIFEST = {
    "id": "build_test",
    "name": "Build Test Campaign",
    "version": "1.0.0",
    "author": "Builder Tester",
    "engine_min_version": "0.4.35",
    "description": "A campaign for testing the builder pipeline.",
    "start_map": "maps/start.tmx",
    "entry_script": "main_intro",
}

MINIMAL_TMX = textwrap.dedent("""\
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


def _make_valid_campaign(tmp_path: Path) -> Path:
    campaign_dir = tmp_path / "build_test"
    (campaign_dir / "maps").mkdir(parents=True)
    (campaign_dir / "scripts").mkdir(parents=True)

    (campaign_dir / "campaign.yaml").write_text(
        yaml.dump(VALID_MANIFEST), encoding="utf-8"
    )
    (campaign_dir / "maps" / "start.tmx").write_text(
        MINIMAL_TMX, encoding="utf-8"
    )
    (campaign_dir / "scripts" / "main_intro.json").write_text(
        json.dumps(MINIMAL_SCRIPT), encoding="utf-8"
    )
    return campaign_dir


# ---------------------------------------------------------------------------
# BuildResult tests
# ---------------------------------------------------------------------------


class TestBuildResult:
    def test_success_human_summary(self):
        result = BuildResult(
            success=True,
            output_path=Path("/tmp/test.capsule"),
            sha256="abc123" * 5 + "xyz",
            file_count=3,
        )
        summary = result.human_summary()
        assert "succeeded" in summary.lower()
        assert "test.capsule" in summary

    def test_failure_human_summary(self):
        from tuxemon.campaign.validator import ValidationReport

        report = ValidationReport()
        report.add_blocking("test_check", "Something is wrong.")
        result = BuildResult(
            success=False, report=report, error="Validation failed."
        )
        summary = result.human_summary()
        assert "failed" in summary.lower()
        assert "test_check" in summary


# ---------------------------------------------------------------------------
# CampaignBuilder tests
# ---------------------------------------------------------------------------


class TestCampaignBuilder:
    def test_build_valid_campaign_succeeds(self, tmp_path):
        campaign_dir = _make_valid_campaign(tmp_path)
        builder = CampaignBuilder()
        result = builder.build(campaign_dir)
        assert result.success, result.human_summary()
        assert result.output_path is not None
        assert result.output_path.exists()
        assert result.sha256
        assert result.file_count > 0

    def test_build_produces_capsule_extension(self, tmp_path):
        campaign_dir = _make_valid_campaign(tmp_path)
        builder = CampaignBuilder()
        result = builder.build(campaign_dir)
        assert result.output_path.suffix == CAPSULE_EXTENSION

    def test_build_produces_valid_zip(self, tmp_path):
        campaign_dir = _make_valid_campaign(tmp_path)
        builder = CampaignBuilder()
        result = builder.build(campaign_dir)
        assert zipfile.is_zipfile(result.output_path)

    def test_capsule_contains_manifest(self, tmp_path):
        campaign_dir = _make_valid_campaign(tmp_path)
        builder = CampaignBuilder()
        result = builder.build(campaign_dir)
        with zipfile.ZipFile(result.output_path) as zf:
            names = zf.namelist()
        assert any("campaign.yaml" in n for n in names)

    def test_capsule_contains_map_and_script(self, tmp_path):
        campaign_dir = _make_valid_campaign(tmp_path)
        builder = CampaignBuilder()
        result = builder.build(campaign_dir)
        with zipfile.ZipFile(result.output_path) as zf:
            names = zf.namelist()
        assert any("start.tmx" in n for n in names)
        assert any("main_intro.json" in n for n in names)

    def test_build_is_deterministic(self, tmp_path):
        campaign_dir = _make_valid_campaign(tmp_path)
        builder = CampaignBuilder()
        r1 = builder.build(campaign_dir, dry_run=True)
        r2 = builder.build(campaign_dir, dry_run=True)
        assert r1.sha256 == r2.sha256

    def test_dry_run_does_not_write_file(self, tmp_path):
        campaign_dir = _make_valid_campaign(tmp_path)
        builder = CampaignBuilder()
        result = builder.build(campaign_dir, dry_run=True)
        assert result.success
        assert result.output_path is None
        capsule = campaign_dir.parent / "build_test.capsule"
        assert not capsule.exists()

    def test_dry_run_computes_sha256(self, tmp_path):
        campaign_dir = _make_valid_campaign(tmp_path)
        builder = CampaignBuilder()
        result = builder.build(campaign_dir, dry_run=True)
        assert result.sha256 != ""

    def test_custom_output_path(self, tmp_path):
        campaign_dir = _make_valid_campaign(tmp_path)
        output = tmp_path / "custom_output.capsule"
        builder = CampaignBuilder()
        result = builder.build(campaign_dir, output_path=output)
        assert result.success
        assert result.output_path == output
        assert output.exists()

    def test_invalid_campaign_fails(self, tmp_path):
        campaign_dir = tmp_path / "bad_campaign"
        campaign_dir.mkdir()
        (campaign_dir / "campaign.yaml").write_text(
            yaml.dump({"id": "bad", "name": "x"}), encoding="utf-8"
        )
        builder = CampaignBuilder()
        result = builder.build(campaign_dir)
        assert not result.success
        assert result.report is not None

    def test_nonexistent_dir_fails(self, tmp_path):
        builder = CampaignBuilder()
        result = builder.build(tmp_path / "ghost_campaign")
        assert not result.success
        assert "does not exist" in result.error

    def test_file_count_matches_actual_files(self, tmp_path):
        campaign_dir = _make_valid_campaign(tmp_path)
        builder = CampaignBuilder()
        result = builder.build(campaign_dir, dry_run=True)
        actual_count = sum(1 for _ in campaign_dir.rglob("*") if _.is_file())
        assert result.file_count == actual_count

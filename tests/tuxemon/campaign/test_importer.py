# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for tuxemon.campaign.importer — CampaignImporter.
"""
from __future__ import annotations

import io
import json
import textwrap
import zipfile
from pathlib import Path

import pytest
import yaml

from tuxemon.campaign.importer import CampaignImporter, CompatibilityResult, ImportResult
from tuxemon.campaign.models import CampaignManifest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

VALID_MANIFEST_DICT = {
    "id": "import_test",
    "name": "Import Test Campaign",
    "version": "1.0.0",
    "author": "Importer Tester",
    "engine_min_version": "0.4.35",
    "description": "A campaign for testing the importer.",
    "start_map": "maps/start.tmx",
    "entry_script": "main_intro",
}


def _make_capsule(tmp_path: Path, manifest_override: dict | None = None) -> Path:
    """Create a minimal .capsule archive in tmp_path."""
    manifest = {**VALID_MANIFEST_DICT, **(manifest_override or {})}
    manifest_yaml = yaml.dump(manifest)

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        campaign_id = manifest["id"]
        zf.writestr(f"{campaign_id}/campaign.yaml", manifest_yaml)
        zf.writestr(f"{campaign_id}/maps/start.tmx", "<map/>")
        zf.writestr(
            f"{campaign_id}/scripts/main_intro.json",
            json.dumps({"id": "main_intro", "triggers": [], "nodes": []}),
        )

    capsule_path = tmp_path / f"{manifest['id']}.capsule"
    capsule_path.write_bytes(buf.getvalue())
    return capsule_path


# ---------------------------------------------------------------------------
# CompatibilityResult tests
# ---------------------------------------------------------------------------


class TestCompatibilityResult:
    def test_human_summary_compatible(self):
        result = CompatibilityResult(
            is_compatible=True,
            campaign_id="my_campaign",
            campaign_name="My Campaign",
            campaign_version="1.0.0",
            engine_min_version="0.4.35",
            current_engine_version="0.4.35",
        )
        summary = result.human_summary()
        assert "YES" in summary
        assert "my_campaign" in summary

    def test_human_summary_incompatible(self):
        result = CompatibilityResult(
            is_compatible=False,
            campaign_id="my_campaign",
            campaign_name="My Campaign",
            campaign_version="2.0.0",
            engine_min_version="9.0.0",
            current_engine_version="0.4.35",
            incompatibilities=["Requires engine >= 9.0.0"],
        )
        summary = result.human_summary()
        assert "NO" in summary
        assert "Requires engine" in summary


# ---------------------------------------------------------------------------
# ImportResult tests
# ---------------------------------------------------------------------------


class TestImportResult:
    def test_success_summary(self):
        result = ImportResult(
            success=True,
            install_dir=Path("/campaigns/my_campaign"),
            compatibility=CompatibilityResult(
                is_compatible=True,
                campaign_id="my_campaign",
                campaign_name="My Campaign",
                campaign_version="1.0.0",
                engine_min_version="0.4.35",
                current_engine_version="0.4.35",
            ),
        )
        summary = result.human_summary()
        assert "Installed to" in summary

    def test_failure_summary(self):
        result = ImportResult(success=False, error="Engine too old.")
        summary = result.human_summary()
        assert "failed" in summary.lower()


# ---------------------------------------------------------------------------
# CampaignImporter tests
# ---------------------------------------------------------------------------


class TestCampaignImporter:
    def test_check_compatibility_valid(self, tmp_path):
        capsule = _make_capsule(tmp_path)
        importer = CampaignImporter(engine_version="0.4.35")
        result = importer.check_compatibility(capsule)
        assert result.is_compatible
        assert result.campaign_id == "import_test"

    def test_check_compatibility_too_new(self, tmp_path):
        capsule = _make_capsule(tmp_path, {"engine_min_version": "9.0.0"})
        importer = CampaignImporter(engine_version="0.4.35")
        result = importer.check_compatibility(capsule)
        assert not result.is_compatible
        assert len(result.incompatibilities) > 0

    def test_check_compatibility_exact_match(self, tmp_path):
        capsule = _make_capsule(tmp_path, {"engine_min_version": "1.0.0"})
        importer = CampaignImporter(engine_version="1.0.0")
        result = importer.check_compatibility(capsule)
        assert result.is_compatible

    def test_check_compatibility_higher_engine(self, tmp_path):
        capsule = _make_capsule(tmp_path, {"engine_min_version": "0.3.0"})
        importer = CampaignImporter(engine_version="1.0.0")
        result = importer.check_compatibility(capsule)
        assert result.is_compatible

    def test_nonexistent_capsule(self, tmp_path):
        importer = CampaignImporter()
        result = importer.check_compatibility(tmp_path / "ghost.capsule")
        assert not result.is_compatible
        assert len(result.incompatibilities) > 0

    def test_not_a_zip_file(self, tmp_path):
        bad_file = tmp_path / "bad.capsule"
        bad_file.write_text("not a zip file", encoding="utf-8")
        importer = CampaignImporter()
        result = importer.check_compatibility(bad_file)
        assert not result.is_compatible

    def test_install_extracts_files(self, tmp_path):
        capsule = _make_capsule(tmp_path)
        install_dir = tmp_path / "campaigns"
        install_dir.mkdir()
        importer = CampaignImporter(engine_version="0.4.35")
        result = importer.install(capsule, install_dir)
        assert result.success, result.human_summary()
        assert result.install_dir is not None
        assert result.install_dir.exists()

    def test_install_creates_campaign_subdir(self, tmp_path):
        capsule = _make_capsule(tmp_path)
        install_dir = tmp_path / "campaigns"
        install_dir.mkdir()
        importer = CampaignImporter(engine_version="0.4.35")
        result = importer.install(capsule, install_dir)
        assert (result.install_dir / "campaign.yaml").exists()

    def test_install_fails_if_incompatible(self, tmp_path):
        capsule = _make_capsule(tmp_path, {"engine_min_version": "99.0.0"})
        install_dir = tmp_path / "campaigns"
        install_dir.mkdir()
        importer = CampaignImporter(engine_version="0.4.35")
        result = importer.install(capsule, install_dir)
        assert not result.success

    def test_install_fails_if_already_installed(self, tmp_path):
        capsule = _make_capsule(tmp_path)
        install_dir = tmp_path / "campaigns"
        install_dir.mkdir()
        importer = CampaignImporter(engine_version="0.4.35")
        importer.install(capsule, install_dir)
        result = importer.install(capsule, install_dir)
        assert not result.success
        assert "already installed" in result.error

    def test_install_overwrite_replaces_existing(self, tmp_path):
        capsule = _make_capsule(tmp_path)
        install_dir = tmp_path / "campaigns"
        install_dir.mkdir()
        importer = CampaignImporter(engine_version="0.4.35")
        importer.install(capsule, install_dir)
        result = importer.install(capsule, install_dir, overwrite=True)
        assert result.success

    def test_read_manifest_returns_model(self, tmp_path):
        capsule = _make_capsule(tmp_path)
        importer = CampaignImporter()
        manifest = importer.read_manifest(capsule)
        assert isinstance(manifest, CampaignManifest)
        assert manifest.id == "import_test"

    def test_read_manifest_nonexistent_returns_none(self, tmp_path):
        importer = CampaignImporter()
        manifest = importer.read_manifest(tmp_path / "ghost.capsule")
        assert manifest is None

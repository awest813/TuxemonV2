# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for tuxemon.campaign.validator — CampaignValidator and ValidationReport.
"""
from __future__ import annotations

import json
import textwrap
from pathlib import Path

import pytest
import yaml

from tuxemon.campaign.validator import (
    CampaignValidator,
    Severity,
    ValidationIssue,
    ValidationReport,
)

# ---------------------------------------------------------------------------
# Fixtures and helpers
# ---------------------------------------------------------------------------

VALID_MANIFEST = {
    "id": "test_campaign",
    "name": "Test Campaign",
    "version": "1.0.0",
    "author": "Test Author",
    "engine_min_version": "0.4.35",
    "description": "A test campaign for unit testing the validator.",
    "start_map": "maps/start.tmx",
    "entry_script": "main_intro",
}

MINIMAL_TMX_WITH_SPAWN = textwrap.dedent("""\
    <?xml version="1.0" encoding="UTF-8"?>
    <map version="1.10" width="10" height="10" tilewidth="16" tileheight="16"
         nextlayerid="3" nextobjectid="5">
     <properties>
      <property name="slug" value="{slug}"/>
     </properties>
     <layer id="1" name="ground" width="10" height="10">
      <data encoding="csv">1,1,1,1,1,1,1,1,1,1,
    1,1,1,1,1,1,1,1,1,1,
    1,1,1,1,1,1,1,1,1,1,
    1,1,1,1,1,1,1,1,1,1,
    1,1,1,1,1,1,1,1,1,1,
    1,1,1,1,1,1,1,1,1,1,
    1,1,1,1,1,1,1,1,1,1,
    1,1,1,1,1,1,1,1,1,1,
    1,1,1,1,1,1,1,1,1,1,
    1,1,1,1,1,1,1,1,1,1
      </data>
     </layer>
     <objectgroup id="2" name="Events">
      {events}
     </objectgroup>
    </map>
    """)

SPAWN_POINT_XML = '<object id="1" type="spawn_point" x="32" y="32" width="16" height="16"/>'

ENCOUNTER_ZONE_XML = """\
<object id="2" type="encounter_zone" x="0" y="0" width="100" height="100">
 <properties>
  <property name="monster_ids" value="{monster_ids}"/>
 </properties>
</object>"""

NPC_XML = """\
<object id="3" type="npc" x="50" y="50" width="16" height="32">
 <properties>
  <property name="script_id" value="{script_id}"/>
 </properties>
</object>"""

TRANSITION_XML = """\
<object id="4" type="map_transition" x="140" y="50" width="16" height="16">
 <properties>
  <property name="target_map" value="{target_map}"/>
 </properties>
</object>"""

MINIMAL_SCRIPT = {
    "id": "main_intro",
    "description": "Intro script",
    "triggers": [{"type": "game_start", "args": {}}],
    "nodes": [
        {
            "id": "node_start",
            "action": "dialog",
            "args": {"text_key": "intro.greeting"},
            "next": None,
            "branches": {},
        }
    ],
    "entry_node": "node_start",
}


def _make_campaign(tmp_path: Path, **kwargs) -> Path:
    """Create a minimal valid campaign directory."""
    campaign_dir = tmp_path / "test_campaign"
    maps_dir = campaign_dir / "maps"
    scripts_dir = campaign_dir / "scripts"
    locale_dir = campaign_dir / "locale"

    for d in [campaign_dir, maps_dir, scripts_dir, locale_dir]:
        d.mkdir(parents=True, exist_ok=True)

    manifest = {**VALID_MANIFEST, **kwargs.get("manifest_overrides", {})}
    (campaign_dir / "campaign.yaml").write_text(
        yaml.dump(manifest), encoding="utf-8"
    )

    # Start map with spawn point
    tmx = MINIMAL_TMX_WITH_SPAWN.format(
        slug="start",
        events=SPAWN_POINT_XML,
    )
    (maps_dir / "start.tmx").write_text(tmx, encoding="utf-8")

    # Entry script
    script = {**MINIMAL_SCRIPT, **kwargs.get("script_overrides", {})}
    (scripts_dir / "main_intro.json").write_text(
        json.dumps(script), encoding="utf-8"
    )

    return campaign_dir


# ---------------------------------------------------------------------------
# ValidationReport tests
# ---------------------------------------------------------------------------


class TestValidationReport:
    def test_empty_report_is_valid(self):
        report = ValidationReport()
        assert report.is_valid is True
        assert report.blocking == []
        assert report.warnings == []
        assert report.infos == []

    def test_blocking_makes_invalid(self):
        report = ValidationReport()
        report.add_blocking("test_check", "A blocking error.")
        assert report.is_valid is False
        assert len(report.blocking) == 1

    def test_warning_does_not_make_invalid(self):
        report = ValidationReport()
        report.add_warning("test_warn", "A warning.")
        assert report.is_valid is True
        assert len(report.warnings) == 1

    def test_summary_contains_result(self):
        report = ValidationReport(campaign_dir=Path("/fake/path"))
        report.add_blocking("check_a", "Error!")
        summary = report.summary()
        assert "INVALID" in summary
        assert "check_a" in summary

    def test_grouped_report(self):
        report = ValidationReport()
        report.add_blocking("block_check", "A blocking error.")
        report.add_warning("warn_check", "A warning.")
        report.add_info("info_check", "Info message.")
        grouped = report.grouped_report()
        assert len(grouped["blocking"]) == 1
        assert len(grouped["warnings"]) == 1
        assert len(grouped["info"]) == 1

    def test_issue_str(self):
        issue = ValidationIssue(
            Severity.BLOCKING, "my_check", "Error message.", path="maps/x.tmx"
        )
        s = str(issue)
        assert "BLOCKING" in s
        assert "my_check" in s
        assert "maps/x.tmx" in s


# ---------------------------------------------------------------------------
# CampaignValidator — manifest checks
# ---------------------------------------------------------------------------


class TestManifestValidation:
    def test_valid_campaign_passes(self, tmp_path):
        campaign_dir = _make_campaign(tmp_path)
        v = CampaignValidator()
        report = v.validate(campaign_dir)
        assert report.is_valid, report.summary()

    def test_missing_dir_blocking(self, tmp_path):
        v = CampaignValidator()
        report = v.validate(tmp_path / "nonexistent")
        assert not report.is_valid
        assert any(i.check_id == "campaign_dir_missing" for i in report.blocking)

    def test_missing_manifest_blocking(self, tmp_path):
        campaign_dir = tmp_path / "c"
        campaign_dir.mkdir()
        v = CampaignValidator()
        report = v.validate(campaign_dir)
        assert not report.is_valid
        assert any(i.check_id == "manifest_missing" for i in report.blocking)

    def test_bad_yaml_blocking(self, tmp_path):
        campaign_dir = tmp_path / "c"
        campaign_dir.mkdir()
        (campaign_dir / "campaign.yaml").write_text(
            "id: [unclosed bracket", encoding="utf-8"
        )
        v = CampaignValidator()
        report = v.validate(campaign_dir)
        assert not report.is_valid
        assert any(i.check_id == "manifest_parse_error" for i in report.blocking)

    def test_invalid_manifest_field_blocking(self, tmp_path):
        campaign_dir = _make_campaign(
            tmp_path, manifest_overrides={"id": "Bad ID With Spaces"}
        )
        v = CampaignValidator()
        report = v.validate(campaign_dir)
        assert not report.is_valid
        assert any(i.check_id == "manifest_field_invalid" for i in report.blocking)

    def test_engine_version_too_new_blocking(self, tmp_path):
        campaign_dir = _make_campaign(
            tmp_path, manifest_overrides={"engine_min_version": "9.0.0"}
        )
        v = CampaignValidator()
        report = v.validate(campaign_dir)
        assert not report.is_valid
        assert any(
            i.check_id == "engine_version_incompatible" for i in report.blocking
        )

    def test_engine_version_equal_passes(self, tmp_path):
        campaign_dir = _make_campaign(
            tmp_path, manifest_overrides={"engine_min_version": "0.4.35"}
        )
        v = CampaignValidator(engine_version="0.4.35")
        report = v.validate(campaign_dir)
        assert report.is_valid, report.summary()

    def test_semver_lte(self):
        assert CampaignValidator._semver_lte("0.4.35", "0.4.35") is True
        assert CampaignValidator._semver_lte("0.4.0", "0.4.35") is True
        assert CampaignValidator._semver_lte("9.0.0", "0.4.35") is False


# ---------------------------------------------------------------------------
# CampaignValidator — map checks
# ---------------------------------------------------------------------------


class TestMapValidation:
    def test_no_maps_dir_warning(self, tmp_path):
        campaign_dir = tmp_path / "c"
        campaign_dir.mkdir()
        (campaign_dir / "campaign.yaml").write_text(
            yaml.dump(VALID_MANIFEST), encoding="utf-8"
        )
        v = CampaignValidator()
        report = v.validate(campaign_dir)
        assert any(i.check_id == "maps_dir_missing" for i in report.warnings)

    def test_duplicate_map_id_blocking(self, tmp_path):
        campaign_dir = _make_campaign(tmp_path)
        maps_dir = campaign_dir / "maps"
        # Create second map with same slug
        tmx = MINIMAL_TMX_WITH_SPAWN.format(slug="start", events=SPAWN_POINT_XML)
        (maps_dir / "start_copy.tmx").write_text(tmx, encoding="utf-8")
        v = CampaignValidator()
        report = v.validate(campaign_dir)
        assert any(i.check_id == "map_id_unique" for i in report.blocking)

    def test_encounter_zone_no_monsters_blocking(self, tmp_path):
        campaign_dir = _make_campaign(tmp_path)
        maps_dir = campaign_dir / "maps"
        tmx = MINIMAL_TMX_WITH_SPAWN.format(
            slug="extra",
            events=SPAWN_POINT_XML
            + "\n"
            + ENCOUNTER_ZONE_XML.format(monster_ids=""),
        )
        (maps_dir / "extra.tmx").write_text(tmx, encoding="utf-8")
        v = CampaignValidator()
        report = v.validate(campaign_dir)
        assert any(i.check_id == "encounter_zone_valid" for i in report.blocking)

    def test_encounter_zone_valid_monsters(self, tmp_path):
        campaign_dir = _make_campaign(tmp_path)
        maps_dir = campaign_dir / "maps"
        tmx = MINIMAL_TMX_WITH_SPAWN.format(
            slug="extra",
            events=SPAWN_POINT_XML
            + "\n"
            + ENCOUNTER_ZONE_XML.format(monster_ids="porcupinito,iguana_evo"),
        )
        (maps_dir / "extra.tmx").write_text(tmx, encoding="utf-8")
        v = CampaignValidator()
        report = v.validate(campaign_dir)
        assert report.is_valid, report.summary()

    def test_unknown_monster_id_blocking_when_whitelist_given(self, tmp_path):
        campaign_dir = _make_campaign(tmp_path)
        maps_dir = campaign_dir / "maps"
        tmx = MINIMAL_TMX_WITH_SPAWN.format(
            slug="extra",
            events=SPAWN_POINT_XML
            + "\n"
            + ENCOUNTER_ZONE_XML.format(monster_ids="unknown_monster_xyz"),
        )
        (maps_dir / "extra.tmx").write_text(tmx, encoding="utf-8")
        v = CampaignValidator(known_monster_ids=frozenset({"porcupinito"}))
        report = v.validate(campaign_dir)
        assert any(i.check_id == "monster_id_valid" for i in report.blocking)

    def test_known_monster_id_passes_whitelist(self, tmp_path):
        campaign_dir = _make_campaign(tmp_path)
        maps_dir = campaign_dir / "maps"
        tmx = MINIMAL_TMX_WITH_SPAWN.format(
            slug="extra",
            events=SPAWN_POINT_XML
            + "\n"
            + ENCOUNTER_ZONE_XML.format(monster_ids="porcupinito"),
        )
        (maps_dir / "extra.tmx").write_text(tmx, encoding="utf-8")
        v = CampaignValidator(known_monster_ids=frozenset({"porcupinito"}))
        report = v.validate(campaign_dir)
        assert report.is_valid, report.summary()

    def test_transition_to_nonexistent_map_blocking(self, tmp_path):
        campaign_dir = _make_campaign(tmp_path)
        maps_dir = campaign_dir / "maps"
        tmx = MINIMAL_TMX_WITH_SPAWN.format(
            slug="extra",
            events=SPAWN_POINT_XML
            + "\n"
            + TRANSITION_XML.format(target_map="maps/ghost.tmx"),
        )
        (maps_dir / "extra.tmx").write_text(tmx, encoding="utf-8")
        v = CampaignValidator()
        report = v.validate(campaign_dir)
        assert any(i.check_id == "transition_target_valid" for i in report.blocking)

    def test_orphan_layer_info(self, tmp_path):
        campaign_dir = _make_campaign(tmp_path)
        maps_dir = campaign_dir / "maps"
        # Add a layer with all zeros (empty)
        tmx_with_empty = textwrap.dedent("""\
            <?xml version="1.0" encoding="UTF-8"?>
            <map version="1.10" width="5" height="5" tilewidth="16" tileheight="16"
                 nextlayerid="3" nextobjectid="3">
             <properties>
              <property name="slug" value="empty_layer_test"/>
             </properties>
             <layer id="1" name="ground" width="5" height="5">
              <data encoding="csv">0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0</data>
             </layer>
             <objectgroup id="2" name="Events">
              <object id="1" type="spawn_point" x="32" y="32"/>
             </objectgroup>
            </map>
            """)
        (maps_dir / "empty_layer.tmx").write_text(tmx_with_empty, encoding="utf-8")
        v = CampaignValidator()
        report = v.validate(campaign_dir)
        assert any(i.check_id == "orphan_layer" for i in report.infos)

    def test_npc_invalid_script_blocking(self, tmp_path):
        campaign_dir = _make_campaign(tmp_path)
        maps_dir = campaign_dir / "maps"
        tmx = MINIMAL_TMX_WITH_SPAWN.format(
            slug="npc_map",
            events=SPAWN_POINT_XML
            + "\n"
            + NPC_XML.format(script_id="nonexistent_script"),
        )
        (maps_dir / "npc_map.tmx").write_text(tmx, encoding="utf-8")
        v = CampaignValidator()
        report = v.validate(campaign_dir)
        assert any(i.check_id == "npc_script_valid" for i in report.blocking)


# ---------------------------------------------------------------------------
# CampaignValidator — script checks
# ---------------------------------------------------------------------------


class TestScriptValidation:
    def test_valid_script_passes(self, tmp_path):
        campaign_dir = _make_campaign(tmp_path)
        v = CampaignValidator()
        report = v.validate(campaign_dir)
        assert report.is_valid, report.summary()

    def test_duplicate_script_id_blocking(self, tmp_path):
        campaign_dir = _make_campaign(tmp_path)
        scripts_dir = campaign_dir / "scripts"
        # Write a second file with same script ID
        (scripts_dir / "main_intro_copy.json").write_text(
            json.dumps(MINIMAL_SCRIPT), encoding="utf-8"
        )
        v = CampaignValidator()
        report = v.validate(campaign_dir)
        assert any(i.check_id == "script_id_unique" for i in report.blocking)

    def test_invalid_action_type_blocking(self, tmp_path):
        campaign_dir = _make_campaign(
            tmp_path,
            script_overrides={
                "nodes": [
                    {
                        "id": "node_start",
                        "action": "do_the_hokey_pokey",
                        "args": {},
                        "next": None,
                        "branches": {},
                    }
                ]
            },
        )
        v = CampaignValidator()
        report = v.validate(campaign_dir)
        assert any(i.check_id == "script_action_valid" for i in report.blocking)

    def test_circular_script_reference_blocking(self, tmp_path):
        campaign_dir = _make_campaign(tmp_path)
        scripts_dir = campaign_dir / "scripts"

        # script A calls script B, script B calls script A
        script_a = {
            "id": "script_a",
            "triggers": [{"type": "game_start", "args": {}}],
            "nodes": [
                {
                    "id": "n",
                    "action": "call_script",
                    "args": {"script_id": "script_b"},
                    "next": None,
                    "branches": {},
                }
            ],
        }
        script_b = {
            "id": "script_b",
            "triggers": [{"type": "game_start", "args": {}}],
            "nodes": [
                {
                    "id": "n",
                    "action": "call_script",
                    "args": {"script_id": "script_a"},
                    "next": None,
                    "branches": {},
                }
            ],
        }
        (scripts_dir / "script_a.json").write_text(json.dumps(script_a))
        (scripts_dir / "script_b.json").write_text(json.dumps(script_b))

        v = CampaignValidator()
        report = v.validate(campaign_dir)
        assert any(i.check_id == "script_loop_detected" for i in report.blocking)

    def test_non_circular_call_chain_passes(self, tmp_path):
        campaign_dir = _make_campaign(tmp_path)
        scripts_dir = campaign_dir / "scripts"

        # A -> B -> C (no cycle)
        for sid, target in [("script_b", "script_c"), ("script_c", None)]:
            nodes = [
                {
                    "id": "n",
                    "action": "call_script" if target else "dialog",
                    "args": {"script_id": target} if target else {"text_key": "k"},
                    "next": None,
                    "branches": {},
                }
            ]
            data = {
                "id": sid,
                "triggers": [{"type": "game_start", "args": {}}],
                "nodes": nodes,
            }
            (scripts_dir / f"{sid}.json").write_text(json.dumps(data))

        v = CampaignValidator()
        report = v.validate(campaign_dir)
        assert report.is_valid, report.summary()

    def test_missing_script_id_blocking(self, tmp_path):
        campaign_dir = _make_campaign(tmp_path)
        scripts_dir = campaign_dir / "scripts"
        bad_script = {**MINIMAL_SCRIPT}
        del bad_script["id"]
        (scripts_dir / "no_id.json").write_text(json.dumps(bad_script))
        v = CampaignValidator()
        report = v.validate(campaign_dir)
        assert any(i.check_id == "script_id_missing" for i in report.blocking)


# ---------------------------------------------------------------------------
# CampaignValidator — campaign-level checks
# ---------------------------------------------------------------------------


class TestCampaignLevelChecks:
    def test_start_map_missing_blocking(self, tmp_path):
        campaign_dir = _make_campaign(
            tmp_path,
            manifest_overrides={"start_map": "maps/ghost.tmx"},
        )
        v = CampaignValidator()
        report = v.validate(campaign_dir)
        assert any(i.check_id == "start_map_reachable" for i in report.blocking)

    def test_start_map_no_spawn_blocking(self, tmp_path):
        campaign_dir = _make_campaign(tmp_path)
        maps_dir = campaign_dir / "maps"
        # Replace start.tmx with a version without spawn point
        tmx = MINIMAL_TMX_WITH_SPAWN.format(slug="start", events="")
        (maps_dir / "start.tmx").write_text(tmx, encoding="utf-8")
        v = CampaignValidator()
        report = v.validate(campaign_dir)
        assert any(i.check_id == "spawn_point_exists" for i in report.blocking)

    def test_entry_script_missing_blocking(self, tmp_path):
        campaign_dir = _make_campaign(
            tmp_path,
            manifest_overrides={"entry_script": "nonexistent_script"},
        )
        v = CampaignValidator()
        report = v.validate(campaign_dir)
        assert any(i.check_id == "entry_script_missing" for i in report.blocking)

    def test_unreachable_map_warning(self, tmp_path):
        campaign_dir = _make_campaign(tmp_path)
        maps_dir = campaign_dir / "maps"
        # Add an isolated map not reachable from start.tmx
        tmx = MINIMAL_TMX_WITH_SPAWN.format(slug="orphan_island", events=SPAWN_POINT_XML)
        (maps_dir / "orphan_island.tmx").write_text(tmx, encoding="utf-8")
        v = CampaignValidator()
        report = v.validate(campaign_dir)
        assert any(i.check_id == "no_unreachable_maps" for i in report.warnings)

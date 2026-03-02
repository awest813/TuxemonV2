# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for tuxemon.campaign.templates — starter template generation.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tuxemon.campaign.templates import (
    BattleChallengeTemplate,
    CampaignTemplate,
    ClassicTwoRegionTemplate,
    EventAdventureTemplate,
    get_template,
    list_templates,
)

# ---------------------------------------------------------------------------
# Registry tests
# ---------------------------------------------------------------------------


class TestTemplateRegistry:
    def test_get_known_template(self):
        t = get_template("blank")
        assert isinstance(t, CampaignTemplate)
        assert t.name == "blank"

    def test_get_classic_two_region(self):
        t = get_template("classic_two_region")
        assert isinstance(t, ClassicTwoRegionTemplate)

    def test_get_battle_challenge(self):
        t = get_template("battle_challenge")
        assert isinstance(t, BattleChallengeTemplate)

    def test_get_event_adventure(self):
        t = get_template("event_adventure")
        assert isinstance(t, EventAdventureTemplate)

    def test_get_unknown_template_raises(self):
        with pytest.raises(KeyError, match="Unknown template"):
            get_template("nonexistent_template")

    def test_list_templates_returns_all(self):
        templates = list_templates()
        names = {t["name"] for t in templates}
        assert "blank" in names
        assert "classic_two_region" in names
        assert "battle_challenge" in names
        assert "event_adventure" in names

    def test_list_templates_fields(self):
        for t in list_templates():
            assert "name" in t
            assert "display_name" in t
            assert "description" in t
            assert "features" in t


# ---------------------------------------------------------------------------
# Blank template
# ---------------------------------------------------------------------------


class TestBlankTemplate:
    def test_apply_writes_nothing(self, tmp_path):
        scaffold = tmp_path / "blank_campaign"
        scaffold.mkdir()
        (scaffold / "maps").mkdir()
        (scaffold / "scripts").mkdir()
        (scaffold / "locale").mkdir()

        t = get_template("blank")
        written = t.apply(scaffold, "blank_campaign", "Blank", "Me")
        assert written == []


# ---------------------------------------------------------------------------
# Classic Two-Region template
# ---------------------------------------------------------------------------


class TestClassicTwoRegionTemplate:
    def _apply(self, tmp_path: Path):
        scaffold = tmp_path / "my_campaign"
        for d in ["maps", "scripts", "locale"]:
            (scaffold / d).mkdir(parents=True)
        t = ClassicTwoRegionTemplate()
        written = t.apply(scaffold, "my_campaign", "My Campaign", "Author")
        return scaffold, written

    def test_applies_without_error(self, tmp_path):
        scaffold, written = self._apply(tmp_path)
        assert len(written) > 0

    def test_creates_region1_town_map(self, tmp_path):
        scaffold, _ = self._apply(tmp_path)
        assert (scaffold / "maps" / "region1_town.tmx").exists()

    def test_creates_region2_gym_map(self, tmp_path):
        scaffold, _ = self._apply(tmp_path)
        assert (scaffold / "maps" / "region2_gym.tmx").exists()

    def test_creates_main_intro_script(self, tmp_path):
        scaffold, _ = self._apply(tmp_path)
        assert (scaffold / "scripts" / "main_intro.json").exists()

    def test_creates_gym_leader_scripts(self, tmp_path):
        scaffold, _ = self._apply(tmp_path)
        assert (scaffold / "scripts" / "gym1_leader.json").exists()
        assert (scaffold / "scripts" / "gym2_leader.json").exists()

    def test_creates_locale_file(self, tmp_path):
        scaffold, _ = self._apply(tmp_path)
        assert (scaffold / "locale" / "en_US.ini").exists()

    def test_locale_contains_gym_strings(self, tmp_path):
        scaffold, _ = self._apply(tmp_path)
        content = (scaffold / "locale" / "en_US.ini").read_text()
        assert "gym1.leader_challenge" in content

    def test_all_tmx_files_are_valid_xml(self, tmp_path):
        import xml.etree.ElementTree as ET

        scaffold, _ = self._apply(tmp_path)
        for tmx in (scaffold / "maps").glob("*.tmx"):
            ET.parse(tmx)  # raises on invalid XML

    def test_all_scripts_are_valid_json(self, tmp_path):
        scaffold, _ = self._apply(tmp_path)
        for js in (scaffold / "scripts").glob("*.json"):
            data = json.loads(js.read_text())
            assert "id" in data

    def test_region1_town_has_spawn_point(self, tmp_path):
        scaffold, _ = self._apply(tmp_path)
        content = (scaffold / "maps" / "region1_town.tmx").read_text()
        assert 'type="spawn_point"' in content

    def test_route_has_encounter_zones(self, tmp_path):
        scaffold, _ = self._apply(tmp_path)
        content = (scaffold / "maps" / "region1_route1.tmx").read_text()
        assert 'type="encounter_zone"' in content

    def test_features_list_not_empty(self):
        t = ClassicTwoRegionTemplate()
        assert len(t.features) > 0


# ---------------------------------------------------------------------------
# Battle Challenge template
# ---------------------------------------------------------------------------


class TestBattleChallengeTemplate:
    def _apply(self, tmp_path: Path):
        scaffold = tmp_path / "challenge"
        for d in ["maps", "scripts", "locale"]:
            (scaffold / d).mkdir(parents=True)
        t = BattleChallengeTemplate()
        written = t.apply(scaffold, "challenge", "Battle Challenge", "Author")
        return scaffold, written

    def test_creates_lobby_map(self, tmp_path):
        scaffold, _ = self._apply(tmp_path)
        assert (scaffold / "maps" / "lobby.tmx").exists()

    def test_creates_all_five_tier_maps(self, tmp_path):
        scaffold, _ = self._apply(tmp_path)
        for i in range(1, 6):
            assert (scaffold / "maps" / f"tier{i}_floor.tmx").exists()

    def test_lobby_has_spawn_point(self, tmp_path):
        scaffold, _ = self._apply(tmp_path)
        content = (scaffold / "maps" / "lobby.tmx").read_text()
        assert 'type="spawn_point"' in content

    def test_tier_floors_have_encounter_zones(self, tmp_path):
        scaffold, _ = self._apply(tmp_path)
        for i in range(1, 6):
            content = (scaffold / "maps" / f"tier{i}_floor.tmx").read_text()
            assert (
                'type="encounter_zone"' in content
            ), f"tier{i}_floor missing encounter zone"

    def test_creates_facility_scripts(self, tmp_path):
        scaffold, _ = self._apply(tmp_path)
        assert (scaffold / "scripts" / "main_intro.json").exists()
        assert (scaffold / "scripts" / "tier_transition.json").exists()

    def test_all_tmx_files_valid_xml(self, tmp_path):
        import xml.etree.ElementTree as ET

        scaffold, _ = self._apply(tmp_path)
        for tmx in (scaffold / "maps").glob("*.tmx"):
            ET.parse(tmx)


# ---------------------------------------------------------------------------
# Event Adventure template
# ---------------------------------------------------------------------------


class TestEventAdventureTemplate:
    def _apply(self, tmp_path: Path):
        scaffold = tmp_path / "adventure"
        for d in ["maps", "scripts", "locale"]:
            (scaffold / d).mkdir(parents=True)
        t = EventAdventureTemplate()
        written = t.apply(scaffold, "adventure", "Event Adventure", "Author")
        return scaffold, written

    def test_creates_village_start_map(self, tmp_path):
        scaffold, _ = self._apply(tmp_path)
        assert (scaffold / "maps" / "village_start.tmx").exists()

    def test_creates_forest_path_map(self, tmp_path):
        scaffold, _ = self._apply(tmp_path)
        assert (scaffold / "maps" / "forest_path.tmx").exists()

    def test_creates_ancient_shrine_map(self, tmp_path):
        scaffold, _ = self._apply(tmp_path)
        assert (scaffold / "maps" / "ancient_shrine.tmx").exists()

    def test_village_has_spawn_point(self, tmp_path):
        scaffold, _ = self._apply(tmp_path)
        content = (scaffold / "maps" / "village_start.tmx").read_text()
        assert 'type="spawn_point"' in content

    def test_forest_has_encounter_zones(self, tmp_path):
        scaffold, _ = self._apply(tmp_path)
        content = (scaffold / "maps" / "forest_path.tmx").read_text()
        assert 'type="encounter_zone"' in content

    def test_creates_dawn_event_script(self, tmp_path):
        scaffold, _ = self._apply(tmp_path)
        assert (scaffold / "scripts" / "dawn_event.json").exists()

    def test_shrine_guardian_script(self, tmp_path):
        scaffold, _ = self._apply(tmp_path)
        assert (scaffold / "scripts" / "shrine_guardian.json").exists()

    def test_locale_contains_story_strings(self, tmp_path):
        scaffold, _ = self._apply(tmp_path)
        content = (scaffold / "locale" / "en_US.ini").read_text()
        assert "story.elder_intro" in content

    def test_all_tmx_files_valid_xml(self, tmp_path):
        import xml.etree.ElementTree as ET

        scaffold, _ = self._apply(tmp_path)
        for tmx in (scaffold / "maps").glob("*.tmx"):
            ET.parse(tmx)

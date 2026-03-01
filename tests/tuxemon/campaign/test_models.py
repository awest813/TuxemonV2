# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for tuxemon.campaign.models — schema validation.
"""
import pytest
from pydantic import ValidationError

from tuxemon.campaign.models import (
    CampaignManifest,
    CampaignRulesetOverride,
    EncounterEntry,
    ScaffoldDirectory,
    WizardStep1,
    WizardStep2,
    WizardStep3,
)
from tuxemon.rules.models import ClauseID, DifficultyPreset


class TestCampaignManifest:
    def _valid_manifest(self, **overrides) -> dict:
        base = dict(
            id="test_campaign",
            name="Test Campaign",
            version="1.0.0",
            author="Author Name",
            engine_min_version="0.4.35",
            description="A test campaign for unit tests.",
            start_map="maps/start.tmx",
            entry_script="main_intro",
        )
        base.update(overrides)
        return base

    def test_valid_manifest(self):
        m = CampaignManifest(**self._valid_manifest())
        assert m.id == "test_campaign"
        assert m.version == "1.0.0"

    def test_id_must_start_with_lowercase(self):
        with pytest.raises(ValidationError):
            CampaignManifest(**self._valid_manifest(id="1bad_id"))

    def test_id_no_uppercase(self):
        with pytest.raises(ValidationError):
            CampaignManifest(**self._valid_manifest(id="Bad_Id"))

    def test_id_no_spaces(self):
        with pytest.raises(ValidationError):
            CampaignManifest(**self._valid_manifest(id="bad id"))

    def test_id_too_short(self):
        with pytest.raises(ValidationError):
            CampaignManifest(**self._valid_manifest(id="ab"))

    def test_id_too_long(self):
        with pytest.raises(ValidationError):
            CampaignManifest(**self._valid_manifest(id="a" * 65))

    def test_version_invalid(self):
        with pytest.raises(ValidationError):
            CampaignManifest(**self._valid_manifest(version="1.0"))

    def test_engine_version_invalid(self):
        with pytest.raises(ValidationError):
            CampaignManifest(**self._valid_manifest(engine_min_version="0.4"))

    def test_start_map_must_be_tmx(self):
        with pytest.raises(ValidationError):
            CampaignManifest(**self._valid_manifest(start_map="maps/start.json"))

    def test_description_too_short(self):
        with pytest.raises(ValidationError):
            CampaignManifest(**self._valid_manifest(description="Short"))

    def test_description_too_long(self):
        with pytest.raises(ValidationError):
            CampaignManifest(**self._valid_manifest(description="x" * 501))

    def test_name_too_short(self):
        with pytest.raises(ValidationError):
            CampaignManifest(**self._valid_manifest(name="ab"))

    def test_optional_fields_default(self):
        m = CampaignManifest(**self._valid_manifest())
        assert m.tags == []
        assert m.license is None
        assert m.language == "en_US"
        assert m.ruleset.permadeath is False

    def test_ruleset_embedded(self):
        ruleset = CampaignRulesetOverride(permadeath=True, nuzlocke_mode=True)
        m = CampaignManifest(**self._valid_manifest(), ruleset=ruleset)
        assert m.ruleset.permadeath is True
        assert m.ruleset.nuzlocke_mode is True


class TestEncounterEntry:
    def test_valid_entry(self):
        e = EncounterEntry(monster_id="porcupinito", weight=5, level_min=3, level_max=8)
        assert e.monster_id == "porcupinito"
        assert e.weight == 5

    def test_level_min_greater_than_max(self):
        with pytest.raises(ValidationError):
            EncounterEntry(monster_id="porcupinito", level_min=10, level_max=5)

    def test_invalid_time_restriction(self):
        with pytest.raises(ValidationError):
            EncounterEntry(monster_id="porcupinito", time_restrictions=["lunchtime"])

    def test_valid_time_restrictions(self):
        e = EncounterEntry(
            monster_id="porcupinito",
            time_restrictions=["dawn", "night", "any"],
        )
        assert "dawn" in e.time_restrictions

    def test_invalid_season_restriction(self):
        with pytest.raises(ValidationError):
            EncounterEntry(monster_id="porcupinito", season_restrictions=["monsoon"])

    def test_valid_season_restrictions(self):
        e = EncounterEntry(monster_id="porcupinito", season_restrictions=["winter", "spring"])
        assert "winter" in e.season_restrictions

    def test_invalid_weekday_restriction(self):
        with pytest.raises(ValidationError):
            EncounterEntry(monster_id="porcupinito", weekday_restrictions=["funday"])

    def test_valid_weekday_restrictions(self):
        e = EncounterEntry(
            monster_id="porcupinito", weekday_restrictions=["monday", "friday"]
        )
        assert "friday" in e.weekday_restrictions

    def test_weight_minimum(self):
        with pytest.raises(ValidationError):
            EncounterEntry(monster_id="porcupinito", weight=0)


class TestWizardStep1:
    def test_valid_step1(self):
        s = WizardStep1(
            id="my_campaign",
            name="My Campaign",
            author="Me",
            description="A ten-character description.",
        )
        assert s.id == "my_campaign"

    def test_bad_id_uppercase(self):
        with pytest.raises(ValidationError):
            WizardStep1(
                id="MyCampaign",
                name="My Campaign",
                author="Me",
                description="A ten-character description.",
            )

    def test_description_min_length(self):
        with pytest.raises(ValidationError):
            WizardStep1(id="my_campaign", name="My Campaign", author="Me", description="Short")


class TestWizardStep2:
    def test_blank_template(self):
        assert WizardStep2(template="blank").template == "blank"

    def test_valid_templates(self):
        for t in ("blank", "classic_two_region", "battle_challenge", "event_adventure"):
            assert WizardStep2(template=t).template == t

    def test_invalid_template(self):
        with pytest.raises(ValidationError):
            WizardStep2(template="nonexistent_template")


class TestWizardStep3:
    def test_defaults(self):
        s = WizardStep3()
        assert s.default_difficulty == DifficultyPreset.NORMAL
        assert s.permadeath is False
        assert s.nuzlocke_mode is False
        assert s.active_clauses == []

    def test_clauses(self):
        s = WizardStep3(active_clauses=[ClauseID.DUPLICATE_SPECIES])
        assert ClauseID.DUPLICATE_SPECIES in s.active_clauses

    def test_hard_difficulty(self):
        s = WizardStep3(default_difficulty="hard")
        assert s.default_difficulty == DifficultyPreset.HARD


class TestScaffoldDirectory:
    def test_from_root(self, tmp_path):
        scaffold = ScaffoldDirectory.from_root(tmp_path / "my_campaign")
        assert scaffold.maps_dir == tmp_path / "my_campaign" / "maps"
        assert scaffold.scripts_dir == tmp_path / "my_campaign" / "scripts"
        assert scaffold.manifest_path == tmp_path / "my_campaign" / "campaign.yaml"

# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for tuxemon.campaign.wizard — CampaignWizard step-by-step validation
and scaffold generation.
"""
import pytest

from tuxemon.campaign.models import CampaignManifest
from tuxemon.campaign.wizard import CampaignWizard, WizardValidationError
from tuxemon.rules.models import ClauseID, DifficultyPreset


@pytest.fixture()
def wizard() -> CampaignWizard:
    return CampaignWizard()


def _complete_wizard(wizard: CampaignWizard, **overrides) -> CampaignManifest:
    """Helper: submit all three steps with valid defaults and return manifest."""
    step1_kwargs = dict(
        id="test_campaign",
        name="Test Campaign",
        author="Test Author",
        description="A complete campaign for automated testing.",
    )
    step2_kwargs = dict(template="blank")
    step3_kwargs = dict(default_difficulty="normal")

    step1_kwargs.update(overrides.get("step1", {}))
    step2_kwargs.update(overrides.get("step2", {}))
    step3_kwargs.update(overrides.get("step3", {}))

    wizard.submit_step1(**step1_kwargs)
    wizard.submit_step2(**step2_kwargs)
    wizard.submit_step3(**step3_kwargs)
    return wizard.build_manifest()


class TestWizardStepOrder:
    def test_initial_state(self, wizard):
        assert wizard.completed_steps == []

    def test_after_step1(self, wizard):
        wizard.submit_step1(
            id="my_campaign",
            name="My Campaign",
            author="Me",
            description="A description long enough.",
        )
        assert wizard.completed_steps == [1]

    def test_cannot_skip_to_step2(self, wizard):
        with pytest.raises(RuntimeError, match="Step 1 has not been submitted"):
            wizard.submit_step2()

    def test_cannot_skip_to_step3(self, wizard):
        with pytest.raises(RuntimeError, match="Step 2 has not been submitted"):
            wizard.submit_step3()

    def test_cannot_build_without_step3(self, wizard):
        wizard.submit_step1(
            id="my_campaign",
            name="My Campaign",
            author="Me",
            description="A description long enough.",
        )
        wizard.submit_step2()
        with pytest.raises(RuntimeError, match="Step 3 has not been submitted"):
            wizard.build_manifest()


class TestWizardStep1Validation:
    def test_valid_step1(self, wizard):
        step = wizard.submit_step1(
            id="my_campaign",
            name="My Campaign",
            author="Creator",
            description="A long enough description.",
        )
        assert step.id == "my_campaign"

    def test_invalid_id_raises_wizard_error(self, wizard):
        with pytest.raises(WizardValidationError) as exc_info:
            wizard.submit_step1(
                id="Bad ID",
                name="Good Name",
                author="Me",
                description="A long enough description.",
            )
        assert exc_info.value.step == 1
        assert len(exc_info.value.errors) > 0

    def test_description_too_short(self, wizard):
        with pytest.raises(WizardValidationError) as exc_info:
            wizard.submit_step1(
                id="my_campaign",
                name="My Campaign",
                author="Me",
                description="Short",
            )
        assert exc_info.value.step == 1


class TestWizardStep2Validation:
    def test_valid_template(self, wizard):
        wizard.submit_step1(
            id="my_campaign",
            name="My Campaign",
            author="Me",
            description="A description long enough.",
        )
        step = wizard.submit_step2(template="classic_two_region")
        assert step.template == "classic_two_region"

    def test_invalid_template(self, wizard):
        wizard.submit_step1(
            id="my_campaign",
            name="My Campaign",
            author="Me",
            description="A description long enough.",
        )
        with pytest.raises(WizardValidationError) as exc_info:
            wizard.submit_step2(template="garbage_template")
        assert exc_info.value.step == 2

    def test_default_template_blank(self, wizard):
        wizard.submit_step1(
            id="my_campaign",
            name="My Campaign",
            author="Me",
            description="A description long enough.",
        )
        step = wizard.submit_step2()
        assert step.template == "blank"


class TestWizardStep3Validation:
    def _submit_steps_1_and_2(self, wizard):
        wizard.submit_step1(
            id="my_campaign",
            name="My Campaign",
            author="Me",
            description="A description long enough.",
        )
        wizard.submit_step2()

    def test_default_step3(self, wizard):
        self._submit_steps_1_and_2(wizard)
        step = wizard.submit_step3()
        assert step.default_difficulty == DifficultyPreset.NORMAL
        assert step.permadeath is False

    def test_permadeath_enabled(self, wizard):
        self._submit_steps_1_and_2(wizard)
        step = wizard.submit_step3(permadeath=True)
        assert step.permadeath is True

    def test_clauses_passed_through(self, wizard):
        self._submit_steps_1_and_2(wizard)
        step = wizard.submit_step3(
            active_clauses=[ClauseID.DUPLICATE_SPECIES, ClauseID.SLEEP_LIMIT]
        )
        assert ClauseID.DUPLICATE_SPECIES in step.active_clauses
        assert ClauseID.SLEEP_LIMIT in step.active_clauses

    def test_hard_difficulty(self, wizard):
        self._submit_steps_1_and_2(wizard)
        step = wizard.submit_step3(default_difficulty="hard")
        assert step.default_difficulty == DifficultyPreset.HARD


class TestManifestConstruction:
    def test_manifest_fields_from_steps(self, wizard):
        manifest = _complete_wizard(wizard)
        assert manifest.id == "test_campaign"
        assert manifest.name == "Test Campaign"
        assert manifest.author == "Test Author"
        assert manifest.version == "1.0.0"
        assert manifest.engine_min_version == "0.4.35"
        assert manifest.start_map.endswith(".tmx")
        assert manifest.entry_script == "main_intro"

    def test_manifest_ruleset_defaults(self, wizard):
        manifest = _complete_wizard(wizard)
        assert manifest.ruleset.permadeath is False
        assert manifest.ruleset.nuzlocke_mode is False
        assert manifest.ruleset.default_difficulty == DifficultyPreset.NORMAL

    def test_manifest_ruleset_with_permadeath(self, wizard):
        manifest = _complete_wizard(wizard, step3={"permadeath": True})
        assert manifest.ruleset.permadeath is True

    def test_manifest_ruleset_with_clauses(self, wizard):
        manifest = _complete_wizard(
            wizard,
            step3={"active_clauses": [ClauseID.DUPLICATE_SPECIES]},
        )
        assert ClauseID.DUPLICATE_SPECIES in manifest.ruleset.active_clauses

    def test_manifest_hard_difficulty(self, wizard):
        manifest = _complete_wizard(wizard, step3={"default_difficulty": "hard"})
        assert manifest.ruleset.default_difficulty == DifficultyPreset.HARD

    def test_manifest_is_campaign_manifest_instance(self, wizard):
        manifest = _complete_wizard(wizard)
        assert isinstance(manifest, CampaignManifest)


class TestScaffoldGeneration:
    def test_dry_run_returns_scaffold(self, wizard, tmp_path):
        _complete_wizard(wizard)
        output = tmp_path / "my_campaign"
        scaffold = wizard.generate_scaffold(output, dry_run=True)
        assert scaffold.root == output
        assert scaffold.maps_dir == output / "maps"
        assert scaffold.manifest_path == output / "campaign.yaml"
        assert not output.exists()

    def test_generate_creates_directory_structure(self, wizard, tmp_path):
        _complete_wizard(wizard)
        output = tmp_path / "my_campaign"
        wizard.generate_scaffold(output)
        assert output.is_dir()
        assert (output / "maps").is_dir()
        assert (output / "scripts").is_dir()
        assert (output / "monsters").is_dir()
        assert (output / "items").is_dir()
        assert (output / "music").is_dir()
        assert (output / "sounds").is_dir()
        assert (output / "gfx").is_dir()
        assert (output / "locale").is_dir()
        assert (output / "campaign.yaml").is_file()

    def test_generate_writes_manifest_yaml(self, wizard, tmp_path):
        _complete_wizard(wizard)
        output = tmp_path / "my_campaign"
        wizard.generate_scaffold(output)
        content = (output / "campaign.yaml").read_text()
        assert "test_campaign" in content
        assert "Test Campaign" in content
        assert "Test Author" in content

    def test_generate_raises_if_dir_exists(self, wizard, tmp_path):
        _complete_wizard(wizard)
        output = tmp_path / "my_campaign"
        output.mkdir()
        with pytest.raises(FileExistsError):
            wizard.generate_scaffold(output)

    def test_second_manifest_build_is_idempotent(self, wizard):
        """build_manifest() may be called multiple times without error."""
        _complete_wizard(wizard)
        m1 = wizard.build_manifest()
        m2 = wizard.build_manifest()
        assert m1.id == m2.id
        assert m1.name == m2.name


class TestWizardReset:
    def test_reset_clears_all_steps(self, wizard):
        _complete_wizard(wizard)
        wizard.reset()
        assert wizard.completed_steps == []

    def test_can_reuse_after_reset(self, wizard, tmp_path):
        _complete_wizard(wizard)
        wizard.reset()
        manifest = _complete_wizard(wizard, step1={"id": "second_campaign", "name": "Second"})
        assert manifest.id == "second_campaign"

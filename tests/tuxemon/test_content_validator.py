# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
import json
from pathlib import Path

import pytest

from tuxemon.database.content_validator import (
    validate_content,
    validate_locale_coverage,
    validate_monster_evolution_refs,
    validate_monster_history_refs,
    validate_monster_technique_refs,
    validate_npc_monster_refs,
)


@pytest.fixture
def mod_root(tmp_path: Path) -> Path:
    """Create a minimal mod structure for testing."""
    db = tmp_path / "db"
    (db / "monster").mkdir(parents=True)
    (db / "technique").mkdir(parents=True)
    (db / "item").mkdir(parents=True)
    (db / "npc").mkdir(parents=True)

    locale_dir = tmp_path / "l18n" / "en_US" / "LC_MESSAGES"
    locale_dir.mkdir(parents=True)

    (db / "technique" / "scratch.json").write_text(
        json.dumps({"slug": "scratch"})
    )
    (db / "technique" / "splash.json").write_text(
        json.dumps({"slug": "splash"})
    )

    (db / "monster" / "alpha.json").write_text(
        json.dumps(
            {
                "slug": "alpha",
                "moveset": [{"technique": "scratch", "level_learned": 1}],
                "evolutions": [],
                "history": [],
            }
        )
    )
    (db / "monster" / "beta.json").write_text(
        json.dumps(
            {
                "slug": "beta",
                "moveset": [{"technique": "splash", "level_learned": 1}],
                "evolutions": [{"monster_slug": "alpha"}],
                "history": [{"mon_slug": "alpha"}],
            }
        )
    )

    (db / "item" / "potion.json").write_text(json.dumps({"slug": "potion"}))

    (db / "npc" / "trainer.json").write_text(
        json.dumps(
            {
                "slug": "trainer",
                "monsters": [{"monster_slug": "alpha"}],
            }
        )
    )

    po_content = "\n".join(
        [
            'msgid ""',
            'msgstr ""',
            "",
            'msgid "alpha"',
            'msgstr "Alpha"',
            "",
            'msgid "alpha_description"',
            'msgstr "A test monster."',
            "",
            'msgid "beta"',
            'msgstr "Beta"',
            "",
            'msgid "beta_description"',
            'msgstr "Another test monster."',
            "",
            'msgid "scratch"',
            'msgstr "Scratch"',
            "",
            'msgid "splash"',
            'msgstr "Splash"',
            "",
            'msgid "potion"',
            'msgstr "Potion"',
            "",
        ]
    )
    (locale_dir / "base.po").write_text(po_content)

    return tmp_path


def test_valid_mod_passes(mod_root: Path) -> None:
    errors = validate_content(mod_root, strict=True)
    assert errors == []


def test_missing_technique_ref(mod_root: Path) -> None:
    monster_file = mod_root / "db" / "monster" / "alpha.json"
    monster_file.write_text(
        json.dumps(
            {
                "slug": "alpha",
                "moveset": [
                    {"technique": "scratch", "level_learned": 1},
                    {"technique": "nonexistent_move", "level_learned": 5},
                ],
                "evolutions": [],
                "history": [],
            }
        )
    )
    errors = validate_monster_technique_refs(mod_root)
    assert len(errors) == 1
    assert "nonexistent_move" in errors[0]


def test_missing_evolution_target(mod_root: Path) -> None:
    monster_file = mod_root / "db" / "monster" / "alpha.json"
    monster_file.write_text(
        json.dumps(
            {
                "slug": "alpha",
                "moveset": [{"technique": "scratch", "level_learned": 1}],
                "evolutions": [{"monster_slug": "gamma"}],
                "history": [],
            }
        )
    )
    errors = validate_monster_evolution_refs(mod_root)
    assert len(errors) == 1
    assert "gamma" in errors[0]


def test_missing_history_ref(mod_root: Path) -> None:
    monster_file = mod_root / "db" / "monster" / "beta.json"
    monster_file.write_text(
        json.dumps(
            {
                "slug": "beta",
                "moveset": [{"technique": "splash", "level_learned": 1}],
                "evolutions": [],
                "history": [{"mon_slug": "delta"}],
            }
        )
    )
    errors = validate_monster_history_refs(mod_root)
    assert len(errors) == 1
    assert "delta" in errors[0]


def test_missing_npc_monster_ref(mod_root: Path) -> None:
    npc_file = mod_root / "db" / "npc" / "trainer.json"
    npc_file.write_text(
        json.dumps(
            {
                "slug": "trainer",
                "monsters": [{"monster_slug": "unknown_mon"}],
            }
        )
    )
    errors = validate_npc_monster_refs(mod_root)
    assert len(errors) == 1
    assert "unknown_mon" in errors[0]


def test_missing_locale_entry(mod_root: Path) -> None:
    (mod_root / "db" / "monster" / "gamma.json").write_text(
        json.dumps(
            {
                "slug": "gamma",
                "moveset": [],
                "evolutions": [],
                "history": [],
            }
        )
    )
    errors = validate_locale_coverage(mod_root)
    assert any("gamma" in e and "slug" in e for e in errors)
    assert any("gamma_description" in e for e in errors)


def test_real_mod_cross_refs_pass() -> None:
    """Validate actual mod data has no broken cross-references."""
    errors = validate_content(strict=False)
    assert errors == [], f"Cross-reference errors: {errors}"

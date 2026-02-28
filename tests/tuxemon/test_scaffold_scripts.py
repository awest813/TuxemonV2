# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""Tests for content scaffolding scripts."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest


SCAFFOLD_MONSTER = Path("scripts/scaffold_monster.py")
SCAFFOLD_LOCALE = Path("scripts/scaffold_locale.py")


class TestScaffoldMonster:
    def test_dry_run_produces_valid_json(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SCAFFOLD_MONSTER),
                "--slug", "test_drymon",
                "--name", "Test Drymon",
                "--species", "reptile",
                "--types", "fire",
                "--stage", "basic",
                "--description", "A dry run monster.",
                "--dry-run",
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["dry_run"] is True
        monster = output["monster_data"]
        assert monster["slug"] == "test_drymon"
        assert monster["types"] == ["fire"]
        assert monster["stage"] == "basic"
        assert isinstance(monster["txmn_id"], int)
        assert monster["txmn_id"] > 0

    def test_dry_run_includes_locale_entries(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SCAFFOLD_MONSTER),
                "--slug", "locmon",
                "--name", "Loc Mon",
                "--species", "bird",
                "--types", "sky",
                "--description", "A locale test.",
                "--dry-run",
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        output = json.loads(result.stdout)
        entries = output["locale_entries"]
        assert any("locmon" in e for e in entries)
        assert any("locmon_description" in e for e in entries)

    def test_multiple_types_parsed(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SCAFFOLD_MONSTER),
                "--slug", "multimon",
                "--name", "Multi Mon",
                "--species", "hybrid",
                "--types", "fire,water,earth",
                "--dry-run",
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        output = json.loads(result.stdout)
        assert output["monster_data"]["types"] == ["fire", "water", "earth"]

    def test_custom_parameters(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SCAFFOLD_MONSTER),
                "--slug", "bigmon",
                "--name", "Big Mon",
                "--species", "giant",
                "--types", "earth",
                "--height", "500",
                "--weight", "200",
                "--catch-rate", "50",
                "--shape", "brute",
                "--dry-run",
                "--json",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        monster = json.loads(result.stdout)["monster_data"]
        assert monster["height"] == 500.0
        assert monster["weight"] == 200.0
        assert monster["catch_rate"] == 50.0
        assert monster["shape"] == "brute"


class TestScaffoldLocale:
    def test_check_existing_key(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SCAFFOLD_LOCALE),
                "check",
                "--key", "tux",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "FOUND" in result.stdout

    def test_check_missing_key(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SCAFFOLD_LOCALE),
                "check",
                "--key", "completely_nonexistent_key_xyz",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "MISSING" in result.stdout

    def test_add_dry_run(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SCAFFOLD_LOCALE),
                "add",
                "--key", "scaffold_test_key",
                "--value", "Scaffold Test Value",
                "--dry-run",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "Would add" in result.stdout

    def test_add_duplicate_key_fails(self):
        result = subprocess.run(
            [
                sys.executable,
                str(SCAFFOLD_LOCALE),
                "add",
                "--key", "tux",
                "--value", "Tux",
            ],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "already exists" in result.stderr

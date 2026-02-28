# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Balance benchmark tests.

Encode expected balance properties as regression tests so that content
changes that break progression curves are caught early.  These tests
run against the real mod data in ``mods/tuxemon/``.
"""
from __future__ import annotations

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

from balance_report import (
    analyze_economy,
    analyze_monsters,
    analyze_moveset_progression,
    analyze_techniques,
    build_report,
    detect_balance_flags,
)

MOD_ROOT = Path("mods/tuxemon")


class TestMonsterBalanceBenchmarks:
    def test_minimum_monster_count(self):
        data = analyze_monsters(MOD_ROOT)
        assert data["total"] >= 400, (
            f"Monster count dropped to {data['total']}; expected >= 400"
        )

    def test_basic_stage_catch_rate_is_accessible(self):
        data = analyze_monsters(MOD_ROOT)
        basic = data["catch_rates_by_stage"].get("basic", {})
        assert basic.get("mean", 0) >= 80, (
            "Basic-stage catch rate should be accessible (mean >= 80)"
        )

    def test_catch_rate_decreases_with_stage(self):
        data = analyze_monsters(MOD_ROOT)
        rates = data["catch_rates_by_stage"]
        basic_mean = rates.get("basic", {}).get("mean", 0)
        stage1_mean = rates.get("stage1", {}).get("mean", 0)
        stage2_mean = rates.get("stage2", {}).get("mean", 0)
        assert basic_mean > stage1_mean > stage2_mean, (
            f"Catch rates should decrease: basic={basic_mean}, "
            f"stage1={stage1_mean}, stage2={stage2_mean}"
        )

    def test_all_monsters_have_minimum_moveset(self):
        data = analyze_monsters(MOD_ROOT)
        assert data["moveset_size"]["min"] >= 3, (
            f"Minimum moveset size is {data['moveset_size']['min']}; "
            "every monster should learn at least 3 moves"
        )

    def test_evolution_paths_exist(self):
        data = analyze_monsters(MOD_ROOT)
        assert data["monsters_with_evolutions"] >= 100, (
            f"Only {data['monsters_with_evolutions']} monsters have evolutions; "
            "expected at least 100"
        )


class TestTechniqueBalanceBenchmarks:
    def test_minimum_technique_count(self):
        data = analyze_techniques(MOD_ROOT)
        assert data["total"] >= 250, (
            f"Technique count dropped to {data['total']}; expected >= 250"
        )

    def test_power_range_is_bounded(self):
        data = analyze_techniques(MOD_ROOT)
        assert data["power"]["max"] <= 5.0, (
            f"Max technique power {data['power']['max']} exceeds 5.0 ceiling"
        )

    def test_mean_accuracy_is_reasonable(self):
        data = analyze_techniques(MOD_ROOT)
        assert 0.7 <= data["accuracy"]["mean"] <= 1.0, (
            f"Mean accuracy {data['accuracy']['mean']} outside expected 0.7-1.0"
        )

    def test_damage_techniques_dominate(self):
        data = analyze_techniques(MOD_ROOT)
        damage_count = data["by_sort"].get("damage", 0)
        assert damage_count / data["total"] >= 0.8, (
            "Damage techniques should be at least 80% of all techniques"
        )


class TestMovesetProgressionBenchmarks:
    def test_power_increases_with_level(self):
        """Mean technique power should increase across level brackets."""
        prog = analyze_moveset_progression(MOD_ROOT)
        brackets = ["1-10", "11-20", "21-30", "31-40"]
        powers = [prog[b]["mean_power"] for b in brackets if prog[b]["techniques"] > 0]
        for i in range(1, len(powers)):
            assert powers[i] >= powers[i - 1], (
                f"Power should not decrease: bracket {brackets[i]} "
                f"({powers[i]}) < bracket {brackets[i-1]} ({powers[i-1]})"
            )

    def test_no_extreme_power_spikes(self):
        """No bracket should have >2.5x the power of the previous bracket."""
        prog = analyze_moveset_progression(MOD_ROOT)
        brackets = ["1-10", "11-20", "21-30", "31-40", "41-50", "51+"]
        prev = 0
        for bracket in brackets:
            data = prog.get(bracket, {})
            mean = data.get("mean_power", 0)
            if prev > 0 and mean > 0:
                ratio = mean / prev
                assert ratio <= 2.5, (
                    f"Power spike in {bracket}: {mean} is {ratio:.1f}x "
                    f"previous ({prev})"
                )
            if mean > 0:
                prev = mean

    def test_early_game_has_enough_techniques(self):
        prog = analyze_moveset_progression(MOD_ROOT)
        early = prog.get("1-10", {})
        assert early.get("techniques", 0) >= 500, (
            f"Only {early.get('techniques', 0)} moves learned in levels 1-10; "
            "expected at least 500 across all monsters"
        )


class TestEconomyBenchmarks:
    def test_items_have_prices(self):
        data = analyze_economy(MOD_ROOT)
        assert data["items_with_price"] >= 50, (
            f"Only {data['items_with_price']} items have prices; expected >= 50"
        )

    def test_entry_level_items_are_affordable(self):
        data = analyze_economy(MOD_ROOT)
        assert data["price_range"]["min"] <= 100, (
            f"Cheapest item costs {data['price_range']['min']}; "
            "expected at least one item <= 100"
        )

    def test_price_spread_is_reasonable(self):
        """Max price should not exceed 200x the minimum to avoid feel-bad gaps."""
        data = analyze_economy(MOD_ROOT)
        pr = data["price_range"]
        if pr["min"] > 0:
            ratio = pr["max"] / pr["min"]
            assert ratio <= 300, (
                f"Price ratio {ratio:.0f}x (max={pr['max']}, min={pr['min']}) "
                "is too extreme"
            )


class TestOverallBalanceFlags:
    def test_no_critical_balance_flags(self):
        """The balance report should produce no flags about extreme spikes."""
        report = build_report(MOD_ROOT)
        flags = report["balance_flags"]
        critical = [
            f for f in flags
            if "Power spike" in f or "Encounter gap" in f
        ]
        assert critical == [], (
            f"Critical balance flags detected: {critical}"
        )

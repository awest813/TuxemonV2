#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Generate a progression balance report for monster/technique/encounter data.

Scans the mod database and produces a summary of stat distributions,
moveset progression curves, encounter level ranges, economy pricing,
and flags potential mid-game balance spikes.

Usage:
    python scripts/balance_report.py
    python scripts/balance_report.py --json
    python scripts/balance_report.py --mod-root mods/tuxemon
"""
from __future__ import annotations

import argparse
import json
import statistics
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

MOD_ROOT = Path("mods/tuxemon")
DB_DIR = "db"


def _load_all(mod_root: Path, table: str) -> list[dict[str, Any]]:
    table_dir = mod_root / DB_DIR / table
    if not table_dir.is_dir():
        return []
    entries: list[dict[str, Any]] = []
    for f in sorted(table_dir.glob("*.json")):
        try:
            entries.append(json.loads(f.read_text(encoding="utf-8")))
        except (json.JSONDecodeError, OSError):
            continue
    try:
        import yaml
        for f in sorted(table_dir.glob("*.yaml")):
            try:
                data = yaml.safe_load(f.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    if "slug" not in data:
                        data["slug"] = f.stem
                    entries.append(data)
            except (OSError, Exception):
                continue
    except ImportError:
        pass
    return entries


# ── Monster analysis ───────────────────────────────────────────────────

def analyze_monsters(mod_root: Path) -> dict[str, Any]:
    monsters = _load_all(mod_root, "monster")
    stage_counts: Counter[str] = Counter()
    catch_rates_by_stage: defaultdict[str, list[float]] = defaultdict(list)
    moveset_sizes: list[int] = []
    max_move_levels: list[int] = []
    evolution_chains: int = 0
    monsters_with_evolutions: int = 0

    for mon in monsters:
        stage = mon.get("stage", "unknown")
        stage_counts[stage] += 1
        cr = mon.get("catch_rate", 0)
        if isinstance(cr, (int, float)):
            catch_rates_by_stage[stage].append(cr)
        moveset = mon.get("moveset", [])
        moveset_sizes.append(len(moveset))
        levels = [
            m.get("level_learned", 0)
            for m in moveset
            if isinstance(m, dict)
        ]
        if levels:
            max_move_levels.append(max(levels))
        evolutions = mon.get("evolutions", [])
        if evolutions:
            monsters_with_evolutions += 1
            evolution_chains += len(evolutions)

    catch_rate_summary = {}
    for stage, rates in sorted(catch_rates_by_stage.items()):
        catch_rate_summary[stage] = {
            "count": len(rates),
            "mean": round(statistics.mean(rates), 1),
            "min": min(rates),
            "max": max(rates),
        }

    return {
        "total": len(monsters),
        "by_stage": dict(stage_counts),
        "catch_rates_by_stage": catch_rate_summary,
        "moveset_size": {
            "mean": round(statistics.mean(moveset_sizes), 1) if moveset_sizes else 0,
            "min": min(moveset_sizes) if moveset_sizes else 0,
            "max": max(moveset_sizes) if moveset_sizes else 0,
        },
        "max_move_level": {
            "mean": round(statistics.mean(max_move_levels), 1) if max_move_levels else 0,
            "max": max(max_move_levels) if max_move_levels else 0,
        },
        "monsters_with_evolutions": monsters_with_evolutions,
        "total_evolution_paths": evolution_chains,
    }


# ── Technique analysis ────────────────────────────────────────────────

def analyze_techniques(mod_root: Path) -> dict[str, Any]:
    techniques = _load_all(mod_root, "technique")
    powers: list[float] = []
    accuracies: list[float] = []
    sort_counts: Counter[str] = Counter()
    recharges: Counter[int] = Counter()

    for tech in techniques:
        power = tech.get("power", 0)
        accuracy = tech.get("accuracy", 0)
        sort_type = tech.get("sort", "unknown")
        recharge = tech.get("recharge", 1)

        if isinstance(power, (int, float)):
            powers.append(float(power))
        if isinstance(accuracy, (int, float)):
            accuracies.append(float(accuracy))
        sort_counts[sort_type] += 1
        if isinstance(recharge, int):
            recharges[recharge] += 1

    damage_powers = [p for p in powers if p > 0]

    return {
        "total": len(techniques),
        "by_sort": dict(sort_counts),
        "power": {
            "mean": round(statistics.mean(damage_powers), 2) if damage_powers else 0,
            "median": round(statistics.median(damage_powers), 2) if damage_powers else 0,
            "min": min(damage_powers) if damage_powers else 0,
            "max": max(damage_powers) if damage_powers else 0,
            "zero_power_count": len(powers) - len(damage_powers),
        },
        "accuracy": {
            "mean": round(statistics.mean(accuracies), 2) if accuracies else 0,
            "min": min(accuracies) if accuracies else 0,
            "max": max(accuracies) if accuracies else 0,
        },
        "recharge_distribution": dict(sorted(recharges.items())),
    }


# ── Economy analysis ──────────────────────────────────────────────────

def analyze_economy(mod_root: Path) -> dict[str, Any]:
    items = _load_all(mod_root, "item")
    prices: list[int] = []
    price_by_category: defaultdict[str, list[int]] = defaultdict(list)

    for item in items:
        price = item.get("cost") or item.get("price")
        if isinstance(price, (int, float)) and price > 0:
            prices.append(int(price))
            category = item.get("category", "unknown")
            price_by_category[category].append(int(price))

    category_summary = {}
    for cat, cat_prices in sorted(price_by_category.items()):
        category_summary[cat] = {
            "count": len(cat_prices),
            "mean": round(statistics.mean(cat_prices)),
            "min": min(cat_prices),
            "max": max(cat_prices),
        }

    return {
        "items_with_price": len(prices),
        "total_items": len(items),
        "price_range": {
            "mean": round(statistics.mean(prices)) if prices else 0,
            "median": round(statistics.median(prices)) if prices else 0,
            "min": min(prices) if prices else 0,
            "max": max(prices) if prices else 0,
        },
        "by_category": category_summary,
    }


# ── Encounter analysis ────────────────────────────────────────────────

def analyze_encounters(mod_root: Path) -> dict[str, Any]:
    encounters = _load_all(mod_root, "encounter")
    level_ranges: list[tuple[int, int]] = []
    rates: list[float] = []

    for enc in encounters:
        monsters = enc.get("monsters", [])
        if isinstance(monsters, list):
            for mon_entry in monsters:
                if not isinstance(mon_entry, dict):
                    continue
                lr = mon_entry.get("level_range", [])
                if isinstance(lr, list) and len(lr) == 2:
                    try:
                        level_ranges.append((int(lr[0]), int(lr[1])))
                    except (ValueError, TypeError):
                        pass
                er = mon_entry.get("encounter_rate")
                if isinstance(er, (int, float)):
                    rates.append(float(er))

    all_min_levels = [lr[0] for lr in level_ranges]
    all_max_levels = [lr[1] for lr in level_ranges]

    level_gaps = _find_level_gaps(level_ranges)

    return {
        "total_encounters": len(encounters),
        "total_spawn_entries": len(level_ranges),
        "level_range": {
            "lowest": min(all_min_levels) if all_min_levels else 0,
            "highest": max(all_max_levels) if all_max_levels else 0,
        },
        "encounter_rate": {
            "mean": round(statistics.mean(rates), 2) if rates else 0,
            "min": min(rates) if rates else 0,
            "max": max(rates) if rates else 0,
        },
        "level_coverage_gaps": level_gaps,
    }


def _find_level_gaps(
    ranges: list[tuple[int, int]], max_level: int = 60
) -> list[dict[str, int]]:
    """Find level ranges with no encounter coverage."""
    covered = set()
    for lo, hi in ranges:
        for level in range(lo, hi + 1):
            covered.add(level)

    gaps: list[dict[str, int]] = []
    gap_start = None
    for level in range(1, max_level + 1):
        if level not in covered:
            if gap_start is None:
                gap_start = level
        else:
            if gap_start is not None:
                gaps.append({"from": gap_start, "to": level - 1})
                gap_start = None
    if gap_start is not None:
        gaps.append({"from": gap_start, "to": max_level})
    return gaps


# ── Moveset progression analysis ─────────────────────────────────────

def analyze_moveset_progression(mod_root: Path) -> dict[str, Any]:
    monsters = _load_all(mod_root, "monster")
    techniques = {
        t["slug"]: t
        for t in _load_all(mod_root, "technique")
        if isinstance(t.get("slug"), str)
    }

    level_brackets = {
        "1-10": [],
        "11-20": [],
        "21-30": [],
        "31-40": [],
        "41-50": [],
        "51+": [],
    }

    for mon in monsters:
        for move in mon.get("moveset", []):
            if not isinstance(move, dict):
                continue
            level = move.get("level_learned", 0)
            tech_slug = move.get("technique", "")
            tech = techniques.get(tech_slug, {})
            power = tech.get("power", 0)
            if not isinstance(power, (int, float)):
                continue

            if level <= 10:
                bracket = "1-10"
            elif level <= 20:
                bracket = "11-20"
            elif level <= 30:
                bracket = "21-30"
            elif level <= 40:
                bracket = "31-40"
            elif level <= 50:
                bracket = "41-50"
            else:
                bracket = "51+"
            level_brackets[bracket].append(float(power))

    result = {}
    for bracket, powers in level_brackets.items():
        if powers:
            result[bracket] = {
                "techniques": len(powers),
                "mean_power": round(statistics.mean(powers), 2),
                "max_power": max(powers),
            }
        else:
            result[bracket] = {"techniques": 0, "mean_power": 0, "max_power": 0}
    return result


# ── Spike detection ──────────────────────────────────────────────────

def detect_balance_flags(report: dict[str, Any]) -> list[str]:
    """Flag potential balance issues from the report data."""
    flags: list[str] = []

    gaps = report.get("encounters", {}).get("level_coverage_gaps", [])
    for gap in gaps:
        span = gap["to"] - gap["from"] + 1
        if span >= 5 and gap["from"] <= 40:
            flags.append(
                f"Encounter gap: levels {gap['from']}-{gap['to']} "
                f"({span} levels with no wild encounters)"
            )

    progression = report.get("moveset_progression", {})
    prev_power = 0
    for bracket in ["1-10", "11-20", "21-30", "31-40", "41-50", "51+"]:
        data = progression.get(bracket, {})
        mean = data.get("mean_power", 0)
        if prev_power > 0 and mean > 0:
            ratio = mean / prev_power
            if ratio > 2.0:
                flags.append(
                    f"Power spike: {bracket} mean power ({mean}) is "
                    f"{ratio:.1f}x the previous bracket ({prev_power})"
                )
        if mean > 0:
            prev_power = mean

    catch_rates = report.get("monsters", {}).get("catch_rates_by_stage", {})
    for stage, data in catch_rates.items():
        if data.get("min", 100) < 10:
            flags.append(
                f"Very low catch rate in stage '{stage}': "
                f"min={data['min']} (may frustrate players)"
            )

    economy = report.get("economy", {})
    price_range = economy.get("price_range", {})
    if price_range.get("max", 0) > 20 * price_range.get("median", 1):
        flags.append(
            f"Economy spread: max price ({price_range['max']}) is "
            f">20x the median ({price_range['median']})"
        )

    return flags


# ── Main ─────────────────────────────────────────────────────────────

def build_report(mod_root: Path) -> dict[str, Any]:
    report: dict[str, Any] = {
        "monsters": analyze_monsters(mod_root),
        "techniques": analyze_techniques(mod_root),
        "economy": analyze_economy(mod_root),
        "encounters": analyze_encounters(mod_root),
        "moveset_progression": analyze_moveset_progression(mod_root),
    }
    report["balance_flags"] = detect_balance_flags(report)
    return report


def print_report(report: dict[str, Any]) -> None:
    mon = report["monsters"]
    print(f"=== Monsters ({mon['total']}) ===")
    print(f"  Stages: {mon['by_stage']}")
    print(f"  Catch rates by stage:")
    for stage, data in mon["catch_rates_by_stage"].items():
        print(f"    {stage}: mean={data['mean']}, range=[{data['min']}, {data['max']}]")
    print(f"  Moveset size: mean={mon['moveset_size']['mean']}, "
          f"range=[{mon['moveset_size']['min']}, {mon['moveset_size']['max']}]")
    print(f"  Evolutions: {mon['monsters_with_evolutions']} monsters, "
          f"{mon['total_evolution_paths']} paths")

    tech = report["techniques"]
    print(f"\n=== Techniques ({tech['total']}) ===")
    print(f"  Sorts: {tech['by_sort']}")
    print(f"  Power (damage): mean={tech['power']['mean']}, "
          f"median={tech['power']['median']}, "
          f"range=[{tech['power']['min']}, {tech['power']['max']}]")
    print(f"  Accuracy: mean={tech['accuracy']['mean']}, "
          f"range=[{tech['accuracy']['min']}, {tech['accuracy']['max']}]")
    print(f"  Recharge: {tech['recharge_distribution']}")

    eco = report["economy"]
    print(f"\n=== Economy ({eco['items_with_price']}/{eco['total_items']} priced) ===")
    pr = eco["price_range"]
    print(f"  Prices: mean={pr['mean']}, median={pr['median']}, "
          f"range=[{pr['min']}, {pr['max']}]")

    enc = report["encounters"]
    print(f"\n=== Encounters ({enc['total_encounters']} zones, "
          f"{enc['total_spawn_entries']} spawn entries) ===")
    lr = enc["level_range"]
    print(f"  Level range: {lr['lowest']}-{lr['highest']}")
    if enc["level_coverage_gaps"]:
        print(f"  Level gaps: {enc['level_coverage_gaps']}")

    prog = report["moveset_progression"]
    print(f"\n=== Moveset Power Progression ===")
    for bracket in ["1-10", "11-20", "21-30", "31-40", "41-50", "51+"]:
        data = prog.get(bracket, {})
        print(f"  Level {bracket}: "
              f"{data.get('techniques', 0)} techniques, "
              f"mean_power={data.get('mean_power', 0)}, "
              f"max_power={data.get('max_power', 0)}")

    flags = report["balance_flags"]
    if flags:
        print(f"\n=== Balance Flags ({len(flags)}) ===")
        for flag in flags:
            print(f"  ⚠ {flag}")
    else:
        print("\n=== No balance flags detected ===")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate progression balance report"
    )
    parser.add_argument(
        "--mod-root", type=Path, default=MOD_ROOT,
        help="Path to mod root directory"
    )
    parser.add_argument(
        "--json", action="store_true",
        help="Output raw JSON instead of formatted text"
    )
    args = parser.parse_args()

    report = build_report(args.mod_root)

    if args.json:
        print(json.dumps(report, indent=2))
    else:
        print_report(report)

    if report["balance_flags"]:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()

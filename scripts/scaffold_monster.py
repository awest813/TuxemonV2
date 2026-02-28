#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Scaffold a new monster definition with all required fields.

Creates the JSON database entry and locale stubs for a new monster.
Run with --dry-run to preview changes without writing files.

Usage:
    python scripts/scaffold_monster.py --slug rockitten --name Rockitten \\
        --species cat --types fire,earth --stage basic \\
        --description "A small kitten made of volcanic rock."

    python scripts/scaffold_monster.py --slug rockitten --name Rockitten \\
        --species cat --types fire --stage basic --dry-run
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

MOD_ROOT = Path("mods/tuxemon")
DB_DIR = MOD_ROOT / "db" / "monster"
LOCALE_DIR = MOD_ROOT / "l18n" / "en_US" / "LC_MESSAGES"
LOCALE_FILE = LOCALE_DIR / "base.po"


def _next_txmn_id() -> int:
    """Scan existing monster files and return the next available txmn_id."""
    max_id = 0
    for json_file in DB_DIR.glob("*.json"):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
            tid = data.get("txmn_id", 0)
            if isinstance(tid, int) and tid > max_id:
                max_id = tid
        except (json.JSONDecodeError, OSError):
            continue
    return max_id + 1


def build_monster_json(
    slug: str,
    species: str,
    types: list[str],
    stage: str,
    txmn_id: int,
    shape: str = "default",
    height: float = 100.0,
    weight: float = 50.0,
    catch_rate: float = 125.0,
) -> dict:
    return {
        "slug": slug,
        "species": species,
        "moveset": [
            {
                "level_learned": 1,
                "technique": "struggle",
                "learning_method": "fallback",
            },
        ],
        "evolutions": [],
        "history": [
            {
                "slug": slug,
                "stage": stage,
                "evolves_from": [],
                "evolves_into": [],
            },
        ],
        "terrains": [],
        "tags": [],
        "shape": shape,
        "stage": stage,
        "types": types,
        "gender_weights": {"male": 0.5, "female": 0.5},
        "txmn_id": txmn_id,
        "height": height,
        "weight": weight,
        "sounds": {
            "combat_call": {"sfx": f"sound_{slug}", "volume": 1.0},
            "faint_call": {"sfx": f"sound_{slug}_faint", "volume": 1.0},
        },
        "catch_rate": catch_rate,
        "lower_catch_resistance": 0.95,
        "upper_catch_resistance": 1.05,
    }


def build_locale_entries(
    slug: str, name: str, species: str, description: str
) -> list[str]:
    lines = []
    lines.append(f'msgid "{slug}"')
    lines.append(f'msgstr "{name}"')
    lines.append("")
    lines.append(f'msgid "{slug}_description"')
    lines.append(f'msgstr "{description}"')
    lines.append("")
    if species:
        lines.append(f'msgid "cat_{species}"')
        lines.append(f'msgstr "{species.title()}"')
        lines.append("")
    return lines


def slug_exists_in_locale(slug: str) -> bool:
    if not LOCALE_FILE.is_file():
        return False
    content = LOCALE_FILE.read_text(encoding="utf-8")
    return f'msgid "{slug}"' in content


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Scaffold a new monster definition"
    )
    parser.add_argument("--slug", required=True, help="Monster slug (lowercase, underscores)")
    parser.add_argument("--name", required=True, help="Display name")
    parser.add_argument("--species", required=True, help="Species category slug")
    parser.add_argument("--types", required=True, help="Comma-separated element types")
    parser.add_argument("--stage", default="basic", choices=["basic", "stage1", "standalone"],
                        help="Evolution stage (default: basic)")
    parser.add_argument("--description", default="A newly discovered monster.",
                        help="Monster description for locale")
    parser.add_argument("--shape", default="default", help="Body shape (default: default)")
    parser.add_argument("--height", type=float, default=100.0, help="Height in cm")
    parser.add_argument("--weight", type=float, default=50.0, help="Weight in kg")
    parser.add_argument("--catch-rate", type=float, default=125.0, help="Catch rate")
    parser.add_argument("--dry-run", action="store_true", help="Preview without writing files")
    parser.add_argument("--json", action="store_true", help="Output as JSON summary")

    args = parser.parse_args()

    slug = args.slug.lower().strip()
    types = [t.strip() for t in args.types.split(",") if t.strip()]

    json_path = DB_DIR / f"{slug}.json"
    if json_path.exists() and not args.dry_run:
        print(f"Error: {json_path} already exists.", file=sys.stderr)
        sys.exit(1)

    txmn_id = _next_txmn_id()
    monster_data = build_monster_json(
        slug=slug,
        species=args.species,
        types=types,
        stage=args.stage,
        txmn_id=txmn_id,
        shape=args.shape,
        height=args.height,
        weight=args.weight,
        catch_rate=args.catch_rate,
    )
    locale_entries = build_locale_entries(
        slug=slug,
        name=args.name,
        species=args.species,
        description=args.description,
    )

    if args.json:
        summary = {
            "json_path": str(json_path),
            "monster_data": monster_data,
            "locale_entries": locale_entries,
            "dry_run": args.dry_run,
        }
        print(json.dumps(summary, indent=2))
        if args.dry_run:
            return
    else:
        print(f"Monster: {args.name} ({slug})")
        print(f"  txmn_id: {txmn_id}")
        print(f"  types: {types}")
        print(f"  stage: {args.stage}")
        print(f"  JSON: {json_path}")
        print(f"  Locale: {LOCALE_FILE}")
        print()

    if args.dry_run:
        print("--- DRY RUN: No files written ---")
        print()
        print(f"Would write {json_path}:")
        print(json.dumps(monster_data, indent=2))
        print()
        print(f"Would append to {LOCALE_FILE}:")
        for line in locale_entries:
            print(f"  {line}")
        return

    json_path.write_text(
        json.dumps(monster_data, indent=2) + "\n", encoding="utf-8"
    )
    print(f"  Wrote {json_path}")

    if not slug_exists_in_locale(slug):
        with LOCALE_FILE.open("a", encoding="utf-8") as f:
            f.write("\n")
            for line in locale_entries:
                f.write(line + "\n")
        print(f"  Appended locale entries to {LOCALE_FILE}")
    else:
        print(f"  Locale entry for '{slug}' already exists, skipped.")

    print()
    print("Next steps:")
    print(f"  1. Add sprite sheets to gfx/sprites/battle/{slug}-sheet.png")
    print(f"  2. Add sound files: sound_{slug}.ogg, sound_{slug}_faint.ogg")
    print(f"  3. Add techniques to the moveset in {json_path}")
    print(f"  4. Run: python -m tuxemon.database.content_validator")


if __name__ == "__main__":
    main()

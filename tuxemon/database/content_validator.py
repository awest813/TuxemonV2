# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Cross-reference content validation for mod data files.

Validates referential integrity between monster definitions,
technique slugs, evolution targets, and localization entries.
Designed to run independently of the game runtime so it can be
invoked from CI without pygame or display dependencies.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

DEFAULT_MOD_ROOT = Path("mods/tuxemon")
DB_DIR = "db"


def _load_slugs_from_table(mod_root: Path, table: str) -> set[str]:
    """Load all slugs from JSON files in a database table directory."""
    table_dir = mod_root / DB_DIR / table
    if not table_dir.is_dir():
        return set()
    slugs: set[str] = set()
    for json_file in sorted(table_dir.glob("*.json")):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Skipping %s: %s", json_file, exc)
            continue
        slug = data.get("slug")
        if isinstance(slug, str):
            slugs.add(slug)
    return slugs


def _load_all_entries(
    mod_root: Path, table: str
) -> list[tuple[str, dict[str, object]]]:
    """Load all entries from a database table, returning (filename, data) pairs."""
    table_dir = mod_root / DB_DIR / table
    if not table_dir.is_dir():
        return []
    entries: list[tuple[str, dict[str, object]]] = []
    for json_file in sorted(table_dir.glob("*.json")):
        try:
            data = json.loads(json_file.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError) as exc:
            logger.warning("Skipping %s: %s", json_file, exc)
            continue
        if isinstance(data, dict):
            entries.append((json_file.name, data))
    return entries


def _load_locale_msgids(mod_root: Path, locale: str = "en_US") -> set[str]:
    """Extract all msgid values from a locale PO file."""
    po_path = mod_root / "l18n" / locale / "LC_MESSAGES" / "base.po"
    if not po_path.is_file():
        return set()
    msgids: set[str] = set()
    for line in po_path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("msgid "):
            key = stripped[6:].strip().strip('"')
            if key:
                msgids.add(key)
    return msgids


def validate_monster_technique_refs(
    mod_root: Path,
) -> list[str]:
    """Check that all technique slugs in monster movesets exist."""
    technique_slugs = _load_slugs_from_table(mod_root, "technique")
    monster_entries = _load_all_entries(mod_root, "monster")
    errors: list[str] = []
    for filename, monster in monster_entries:
        slug = monster.get("slug", filename)
        moveset = monster.get("moveset", [])
        if not isinstance(moveset, list):
            continue
        for move in moveset:
            if not isinstance(move, dict):
                continue
            tech = move.get("technique")
            if isinstance(tech, str) and tech not in technique_slugs:
                errors.append(
                    f"monster/{filename}: technique '{tech}' in "
                    f"moveset of '{slug}' not found in technique table"
                )
    return errors


def validate_monster_evolution_refs(
    mod_root: Path,
) -> list[str]:
    """Check that all evolution target monster slugs exist."""
    monster_slugs = _load_slugs_from_table(mod_root, "monster")
    monster_entries = _load_all_entries(mod_root, "monster")
    errors: list[str] = []
    for filename, monster in monster_entries:
        slug = monster.get("slug", filename)
        evolutions = monster.get("evolutions", [])
        if not isinstance(evolutions, list):
            continue
        for evo in evolutions:
            if not isinstance(evo, dict):
                continue
            target = evo.get("monster_slug")
            if isinstance(target, str) and target not in monster_slugs:
                errors.append(
                    f"monster/{filename}: evolution target '{target}' "
                    f"in '{slug}' not found in monster table"
                )
    return errors


def validate_monster_history_refs(
    mod_root: Path,
) -> list[str]:
    """Check that all history monster slugs exist."""
    monster_slugs = _load_slugs_from_table(mod_root, "monster")
    monster_entries = _load_all_entries(mod_root, "monster")
    errors: list[str] = []
    for filename, monster in monster_entries:
        slug = monster.get("slug", filename)
        history = monster.get("history", [])
        if not isinstance(history, list):
            continue
        for entry in history:
            if not isinstance(entry, dict):
                continue
            mon_slug = entry.get("mon_slug")
            if isinstance(mon_slug, str) and mon_slug not in monster_slugs:
                errors.append(
                    f"monster/{filename}: history ref '{mon_slug}' "
                    f"in '{slug}' not found in monster table"
                )
    return errors


def validate_locale_coverage(
    mod_root: Path,
) -> list[str]:
    """Check that monster, technique, and item slugs have locale entries."""
    msgids = _load_locale_msgids(mod_root)
    errors: list[str] = []
    for table in ("monster", "technique", "item"):
        slugs = _load_slugs_from_table(mod_root, table)
        for slug in sorted(slugs):
            if slug not in msgids:
                errors.append(
                    f"{table}/{slug}: missing locale entry for slug '{slug}'"
                )
            desc_key = f"{slug}_description"
            if table == "monster" and desc_key not in msgids:
                errors.append(
                    f"{table}/{slug}: missing locale entry "
                    f"for description key '{desc_key}'"
                )
    return errors


def validate_npc_monster_refs(
    mod_root: Path,
) -> list[str]:
    """Check that monster slugs referenced in NPC party definitions exist."""
    monster_slugs = _load_slugs_from_table(mod_root, "monster")
    npc_entries = _load_all_entries(mod_root, "npc")
    errors: list[str] = []
    for filename, npc in npc_entries:
        slug = npc.get("slug", filename)
        monsters = npc.get("monsters", [])
        if not isinstance(monsters, list):
            continue
        for mon_entry in monsters:
            if isinstance(mon_entry, dict):
                mon_slug = mon_entry.get("monster_slug")
            elif isinstance(mon_entry, str):
                mon_slug = mon_entry
            else:
                continue
            if isinstance(mon_slug, str) and mon_slug not in monster_slugs:
                errors.append(
                    f"npc/{filename}: monster '{mon_slug}' in "
                    f"party of '{slug}' not found in monster table"
                )
    return errors


def validate_content(
    mod_root: Path | None = None,
    *,
    strict: bool = False,
) -> list[str]:
    """
    Run all content validation checks.

    Returns a list of error strings.  When *strict* is True, locale coverage
    warnings are included; otherwise only cross-reference errors are returned.
    """
    root = mod_root or DEFAULT_MOD_ROOT
    errors: list[str] = []
    errors.extend(validate_monster_technique_refs(root))
    errors.extend(validate_monster_evolution_refs(root))
    errors.extend(validate_monster_history_refs(root))
    errors.extend(validate_npc_monster_refs(root))
    if strict:
        errors.extend(validate_locale_coverage(root))
    return errors


def main() -> None:
    """CLI entry point for content validation."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Validate cross-references in mod content data"
    )
    parser.add_argument(
        "--mod-root",
        type=Path,
        default=DEFAULT_MOD_ROOT,
        help="Path to the mod root directory",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Include locale coverage checks",
    )
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO)
    errors = validate_content(args.mod_root, strict=args.strict)
    if errors:
        print(
            f"Content validation found {len(errors)} issue(s):",
            file=sys.stderr,
        )
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        sys.exit(1)
    else:
        print("Content validation passed.")


if __name__ == "__main__":
    main()

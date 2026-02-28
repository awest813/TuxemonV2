#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Add or check locale entries in the en_US base.po file.

Supports adding single entries, batch entries from a file,
and checking whether entries already exist.

Usage:
    # Add a single entry
    python scripts/scaffold_locale.py add --key "fire_blast" --value "Fire Blast"

    # Check if an entry exists
    python scripts/scaffold_locale.py check --key "fire_blast"

    # Add entries from a TSV file (key<tab>value per line)
    python scripts/scaffold_locale.py batch --file entries.tsv

    # Dry run (preview without writing)
    python scripts/scaffold_locale.py add --key "fire_blast" --value "Fire Blast" --dry-run
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

MOD_ROOT = Path("mods/tuxemon")
LOCALE_FILE = MOD_ROOT / "l18n" / "en_US" / "LC_MESSAGES" / "base.po"


def _load_msgids() -> set[str]:
    if not LOCALE_FILE.is_file():
        return set()
    msgids: set[str] = set()
    for line in LOCALE_FILE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("msgid "):
            key = stripped[6:].strip().strip('"')
            if key:
                msgids.add(key)
    return msgids


def _append_entry(key: str, value: str) -> None:
    with LOCALE_FILE.open("a", encoding="utf-8") as f:
        f.write(f'\nmsgid "{key}"\n')
        f.write(f'msgstr "{value}"\n')


def cmd_add(args: argparse.Namespace) -> None:
    existing = _load_msgids()
    if args.key in existing:
        print(f"Entry '{args.key}' already exists.", file=sys.stderr)
        sys.exit(1)

    if args.dry_run:
        print(f"Would add: msgid \"{args.key}\" -> msgstr \"{args.value}\"")
        return

    _append_entry(args.key, args.value)
    print(f"Added: {args.key} = {args.value}")


def cmd_check(args: argparse.Namespace) -> None:
    existing = _load_msgids()
    keys = [k.strip() for k in args.key.split(",") if k.strip()]
    all_found = True
    for key in keys:
        if key in existing:
            print(f"  FOUND: {key}")
        else:
            print(f"  MISSING: {key}")
            all_found = False
    if not all_found:
        sys.exit(1)


def cmd_batch(args: argparse.Namespace) -> None:
    input_file = Path(args.file)
    if not input_file.is_file():
        print(f"File not found: {input_file}", file=sys.stderr)
        sys.exit(1)

    existing = _load_msgids()
    added = 0
    skipped = 0

    for line_num, line in enumerate(
        input_file.read_text(encoding="utf-8").splitlines(), 1
    ):
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t", 1)
        if len(parts) != 2:
            print(f"  Line {line_num}: skipped (expected key<tab>value)", file=sys.stderr)
            skipped += 1
            continue

        key, value = parts[0].strip(), parts[1].strip()
        if key in existing:
            print(f"  Line {line_num}: '{key}' already exists, skipped.")
            skipped += 1
            continue

        if args.dry_run:
            print(f"  Would add: {key} = {value}")
        else:
            _append_entry(key, value)
            print(f"  Added: {key} = {value}")
        existing.add(key)
        added += 1

    print(f"\nTotal: {added} added, {skipped} skipped.")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Manage locale entries in en_US base.po"
    )
    sub = parser.add_subparsers(dest="command", required=True)

    add_parser = sub.add_parser("add", help="Add a single locale entry")
    add_parser.add_argument("--key", required=True, help="Translation key (msgid)")
    add_parser.add_argument("--value", required=True, help="Translation value (msgstr)")
    add_parser.add_argument("--dry-run", action="store_true")

    check_parser = sub.add_parser("check", help="Check if entries exist")
    check_parser.add_argument("--key", required=True, help="Comma-separated keys to check")

    batch_parser = sub.add_parser("batch", help="Add entries from a TSV file")
    batch_parser.add_argument("--file", required=True, help="TSV file (key<tab>value per line)")
    batch_parser.add_argument("--dry-run", action="store_true")

    args = parser.parse_args()

    if args.command == "add":
        cmd_add(args)
    elif args.command == "check":
        cmd_check(args)
    elif args.command == "batch":
        cmd_batch(args)


if __name__ == "__main__":
    main()

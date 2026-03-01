"""
Validate TMX map files and TSX tileset files for OpenCapsuleMon.

Performs structural checks without requiring pygame or a display so
it can be run in CI or as a pre-commit helper.

EXAMPLES

    Validate all maps in the default mod:
        python scripts/validate_maps.py

    Validate a single map:
        python scripts/validate_maps.py mods/tuxemon/maps/azure_town.tmx

    Validate maps and tilesets together:
        python scripts/validate_maps.py --tilesets

    Emit JSON output (for tooling integration):
        python scripts/validate_maps.py --json

    Treat warnings as errors:
        python scripts/validate_maps.py --strict

EXIT CODES

    0  All files passed validation (no errors; warnings ignored unless
       --strict is set).
    1  One or more files have errors (or warnings when --strict is active).
    2  No map or tileset files were found to validate.
"""

from __future__ import annotations

import json
import logging
import sys
from pathlib import Path

import click

# ---------------------------------------------------------------------------
# Bootstrap import path so the script can be run from the repo root without
# an editable install: ``python scripts/validate_maps.py``.
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tuxemon.map.validator import (  # noqa: E402
    ValidationResult,
    validate_map_directory,
    validate_tmx,
    validate_tsx,
)

DEFAULT_MAPS_DIR = _REPO_ROOT / "mods" / "tuxemon" / "maps"
DEFAULT_TILESETS_DIR = _REPO_ROOT / "mods" / "tuxemon" / "gfx" / "tilesets"

logging.basicConfig(level=logging.WARNING, format="%(levelname)s: %(message)s")


# ---------------------------------------------------------------------------
# Output formatters
# ---------------------------------------------------------------------------


def _print_text(results: list[ValidationResult], strict: bool) -> int:
    """Print human-readable output and return an appropriate exit code."""
    total_errors = 0
    total_warnings = 0
    failed_files = 0

    for r in results:
        file_errors = len(r.errors)
        file_warnings = len(r.warnings)
        total_errors += file_errors
        total_warnings += file_warnings

        issue_count = file_errors + (file_warnings if strict else 0)
        if issue_count == 0:
            continue

        failed_files += 1
        click.echo(f"\n{r.path}")
        for msg in r.errors:
            click.echo(f"  ERROR   {msg}")
        if strict or file_errors:
            for msg in r.warnings:
                level = "WARNING" if not strict else "ERROR  "
                click.echo(f"  {level} {msg}")

    ok_count = len(results) - failed_files
    click.echo(
        f"\n{len(results)} file(s) checked: "
        f"{ok_count} ok, {failed_files} with issues "
        f"({total_errors} error(s), {total_warnings} warning(s))"
    )

    if total_errors > 0:
        return 1
    if strict and total_warnings > 0:
        return 1
    return 0


def _print_json(results: list[ValidationResult], strict: bool) -> int:
    """Emit JSON output and return an appropriate exit code."""
    payload = []
    exit_code = 0

    for r in results:
        entry: dict = {
            "path": str(r.path),
            "ok": r.ok and (not strict or not r.warnings),
            "errors": r.errors,
            "warnings": r.warnings,
        }
        payload.append(entry)
        if r.errors or (strict and r.warnings):
            exit_code = 1

    click.echo(json.dumps(payload, indent=2))
    return exit_code


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("paths", nargs=-1, type=click.Path(exists=True, path_type=Path))
@click.option(
    "--tilesets",
    "include_tilesets",
    is_flag=True,
    default=False,
    help="Also validate .tsx tileset files in the default tilesets directory.",
)
@click.option(
    "--tilesets-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Override the tilesets directory when --tilesets is active.",
)
@click.option(
    "--maps-dir",
    type=click.Path(file_okay=False, path_type=Path),
    default=None,
    help="Override the default maps directory when no PATHS are given.",
)
@click.option(
    "--strict",
    is_flag=True,
    default=False,
    help="Treat warnings as errors (non-zero exit when any warning exists).",
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    default=False,
    help="Emit JSON instead of human-readable text.",
)
def main(
    paths: tuple[Path, ...],
    include_tilesets: bool,
    tilesets_dir: Path | None,
    maps_dir: Path | None,
    strict: bool,
    output_json: bool,
) -> None:
    """Validate OpenCapsuleMon TMX map files and TSX tileset files.

    When no PATHS are given, all .tmx files in the default maps directory
    (mods/tuxemon/maps/) are validated.  Pass one or more file paths to
    restrict validation to specific files.
    """
    results: list[ValidationResult] = []

    if paths:
        # Validate the explicitly supplied files.
        for p in paths:
            p = p.resolve()
            suffix = p.suffix.lower()
            if suffix == ".tmx":
                results.append(validate_tmx(p))
            elif suffix == ".tsx":
                results.append(validate_tsx(p))
            else:
                click.echo(
                    f"Skipping '{p}': not a .tmx or .tsx file.",
                    err=True,
                )
    else:
        # Batch mode: scan the maps (and optionally tilesets) directory.
        resolved_maps_dir = (maps_dir or DEFAULT_MAPS_DIR).resolve()
        resolved_tilesets_dir: Path | None = None

        if include_tilesets:
            resolved_tilesets_dir = (
                tilesets_dir or DEFAULT_TILESETS_DIR
            ).resolve()

        if not resolved_maps_dir.is_dir():
            click.echo(
                f"Maps directory not found: {resolved_maps_dir}", err=True
            )
            sys.exit(2)

        results = validate_map_directory(
            resolved_maps_dir, resolved_tilesets_dir
        )

    if not results:
        click.echo("No files found to validate.", err=True)
        sys.exit(2)

    if output_json:
        exit_code = _print_json(results, strict)
    else:
        exit_code = _print_text(results, strict)

    sys.exit(exit_code)


if __name__ == "__main__":
    main()

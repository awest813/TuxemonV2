# SPDX-License-Identifier: GPL-3.0
"""Helpers for reporting repository progress for this fork."""

from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
import re


@dataclass(frozen=True)
class ProgressCounts:
    monsters: int
    techniques: int
    items: int
    npcs: int
    maps: int
    locales: int


@dataclass(frozen=True)
class RoadmapProgress:
    completed: int
    total: int


def _count_files(directory: Path, pattern: str) -> int:
    if not directory.exists():
        return 0
    return sum(1 for _ in directory.glob(pattern))


def collect_progress_counts(repo_root: Path) -> ProgressCounts:
    mod_root = repo_root / "mods" / "tuxemon"
    db_root = mod_root / "db"

    return ProgressCounts(
        monsters=_count_files(db_root / "monster", "*.json"),
        techniques=_count_files(db_root / "technique", "*.json"),
        items=_count_files(db_root / "item", "*.json"),
        npcs=_count_files(db_root / "npc", "*.json"),
        maps=_count_files(mod_root / "maps", "*.tmx"),
        locales=sum(1 for _ in (mod_root / "l18n").rglob("*.po")),
    )


def collect_roadmap_progress(roadmap_path: Path) -> RoadmapProgress:
    pattern = re.compile(r"^\s*- \[(?P<done>[xX ])\] ")
    total = 0
    completed = 0

    if roadmap_path.exists():
        for line in roadmap_path.read_text(encoding="utf-8").splitlines():
            match = pattern.match(line)
            if not match:
                continue
            total += 1
            if match.group("done").lower() == "x":
                completed += 1

    return RoadmapProgress(completed=completed, total=total)


def _read_git_value(repo_root: Path, args: list[str]) -> str | None:
    command = ["git", *args]
    result = subprocess.run(
        command,
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        return None

    value = result.stdout.strip()
    return value or None


def build_status_report(repo_root: Path) -> str:
    counts = collect_progress_counts(repo_root)
    roadmap = collect_roadmap_progress(repo_root / "ROADMAP.md")
    branch = _read_git_value(repo_root, ["branch", "--show-current"])
    commit = _read_git_value(repo_root, ["rev-parse", "--short", "HEAD"])

    lines = ["Tuxemon fork status"]
    if branch:
        lines.append(f"Branch: {branch}")
    if commit:
        lines.append(f"Commit: {commit}")

    lines.extend(
        [
            "",
            "Content snapshot:",
            f"- Monsters: {counts.monsters}",
            f"- Techniques: {counts.techniques}",
            f"- Items: {counts.items}",
            f"- NPCs: {counts.npcs}",
            f"- Maps: {counts.maps}",
            f"- Localizations (.po files): {counts.locales}",
            "",
            f"Roadmap checklist completion: {roadmap.completed}/{roadmap.total}",
        ]
    )

    return "\n".join(lines)


def print_status(repo_root: Path) -> None:
    """Print status information for local progress tracking."""
    print(build_status_report(repo_root))

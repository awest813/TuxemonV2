# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from pathlib import Path

from tuxemon.world.weekly_event_loader import (
    discover_weekly_event_manifests,
    load_weekly_event_calendar,
)


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def test_discover_weekly_event_manifests(tmp_path: Path):
    mod_a = tmp_path / "mod_a"
    mod_b = tmp_path / "mod_b"

    _write(
        mod_a / "weekly_events.yaml",
        "weekly_events: []\n",
    )
    _write(
        mod_b / "world" / "weekly_events.yaml",
        "weekly_events: []\n",
    )

    manifests = discover_weekly_event_manifests([mod_b, mod_a])
    assert manifests == [
        mod_a / "weekly_events.yaml",
        mod_b / "world" / "weekly_events.yaml",
    ]


def test_load_calendar_merges_and_overrides_by_event_id(tmp_path: Path):
    manifest_a = tmp_path / "a.yaml"
    manifest_b = tmp_path / "b.yaml"

    _write(
        manifest_a,
        """
weekly_events:
  - id: bug_contest
    name_key: event_bug
    days: ["tuesday"]
    time: ["morning"]
    map: "park"
  - id: market
    name_key: event_market
    days: ["sunday"]
    time: ["afternoon"]
""".strip()
        + "\n",
    )
    _write(
        manifest_b,
        """
weekly_events:
  - id: bug_contest
    name_key: event_bug_override
    days: ["thursday"]
    time: ["morning"]
    map: "park"
""".strip()
        + "\n",
    )

    calendar = load_weekly_event_calendar([manifest_a, manifest_b])
    assert len(calendar.weekly_events) == 2

    bug = calendar.get_event("bug_contest")
    assert bug is not None
    assert bug.name_key == "event_bug_override"
    assert bug.days == ["thursday"]


def test_load_calendar_skips_invalid_entries(tmp_path: Path):
    manifest = tmp_path / "bad.yaml"
    _write(
        manifest,
        """
weekly_events:
  - "not-a-mapping"
  - id: ""
    name_key: bad
    days: ["monday"]
    time: ["morning"]
  - id: invalid_day
    name_key: invalid_day
    days: ["funday"]
    time: ["morning"]
  - id: valid
    name_key: valid
    days: ["monday"]
    time: ["morning"]
""".strip()
        + "\n",
    )

    calendar = load_weekly_event_calendar([manifest])
    assert [e.id for e in calendar.weekly_events] == ["valid"]

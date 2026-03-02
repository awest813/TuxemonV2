# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Weekly event calendar discovery and loading helpers.

The game scans active mods for a weekly-event manifest and merges all entries
into a single :class:`WeeklyEventCalendar` used by the world scheduler.
Later mods override duplicate event IDs from earlier mods.
"""

from __future__ import annotations

import logging
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

from tuxemon.constants import paths
from tuxemon.database.yaml_utils import load_yaml
from tuxemon.world.weekly_events import WeeklyEventCalendar, WeeklyEventEntry

logger = logging.getLogger(__name__)

_DEFAULT_MANIFEST_LOCATIONS: tuple[str, ...] = (
    "weekly_events.yaml",
    "data/weekly_events.yaml",
    "world/weekly_events.yaml",
)


def discover_weekly_event_manifests(
    mod_paths: Sequence[Path] | None = None,
) -> list[Path]:
    """
    Return existing weekly-event manifest files for active mods.

    Parameters:
        mod_paths: Optional explicit mod directories. When omitted, active mod
            directories are discovered through :func:`paths.get_active_mod_paths`.
    """
    roots = list(mod_paths or paths.get_active_mod_paths())
    manifests: list[Path] = []
    for mod_root in sorted(roots):
        for rel_path in _DEFAULT_MANIFEST_LOCATIONS:
            candidate = mod_root / rel_path
            if candidate.is_file():
                manifests.append(candidate)
    return manifests


def load_weekly_event_calendar(
    manifest_paths: Sequence[Path] | None = None,
) -> WeeklyEventCalendar:
    """
    Build a :class:`WeeklyEventCalendar` from one or more YAML manifests.

    Duplicate event IDs are overridden by later files in ``manifest_paths``.
    Invalid entries are skipped with warning logs.
    """
    paths_to_load = list(manifest_paths or discover_weekly_event_manifests())
    if not paths_to_load:
        return WeeklyEventCalendar()

    merged_by_id: dict[str, dict[str, Any]] = {}
    order: list[str] = []

    for manifest in paths_to_load:
        try:
            raw = load_yaml(manifest)
        except Exception:
            logger.warning("Skipping unreadable weekly event file: %s", manifest)
            continue

        if not isinstance(raw, Mapping):
            logger.warning("Weekly event file must contain a mapping: %s", manifest)
            continue
        raw_events = raw.get("weekly_events", [])
        if not isinstance(raw_events, list):
            logger.warning(
                "weekly_events must be a list in %s (got %s)",
                manifest,
                type(raw_events).__name__,
            )
            continue

        for entry in raw_events:
            if not isinstance(entry, Mapping):
                logger.warning("Skipping non-mapping weekly event in %s", manifest)
                continue
            event_id = str(entry.get("id", "")).strip()
            if not event_id:
                logger.warning("Skipping weekly event without id in %s", manifest)
                continue
            normalized = dict(entry)
            merged_by_id[event_id] = normalized
            if event_id not in order:
                order.append(event_id)

    weekly_events: list[WeeklyEventEntry] = []
    for event_id in order:
        payload = merged_by_id[event_id]
        try:
            weekly_events.append(WeeklyEventEntry(**payload))
        except Exception:
            logger.warning(
                "Skipping invalid weekly event definition %r from merged manifests",
                event_id,
                exc_info=True,
            )

    return WeeklyEventCalendar(weekly_events=weekly_events)

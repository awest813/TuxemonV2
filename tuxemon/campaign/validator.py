# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Campaign directory validator.

Implements all validation rules from docs/campaign_maker_mvp.md §4.
Validates a campaign directory and returns a ValidationReport containing
blocking errors, warnings, and informational messages.
"""

from __future__ import annotations

import json
import logging
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

import yaml
from pydantic import ValidationError

from tuxemon.campaign.models import (
    CampaignManifest,
)

logger = logging.getLogger(__name__)

ENGINE_VERSION = "0.4.35"

# Known action types recognized by the campaign event graph engine.
KNOWN_ACTION_TYPES: frozenset[str] = frozenset(
    {
        "dialog",
        "set_variable",
        "check_variable",
        "spawn_npc",
        "remove_npc",
        "open_shop",
        "start_battle",
        "end_battle",
        "play_music",
        "stop_music",
        "play_sound",
        "award_item",
        "remove_item",
        "award_monster",
        "teleport",
        "open_menu",
        "close_menu",
        "play_cutscene",
        "wait",
        "call_script",
    }
)

# Known trigger types for the event graph.
KNOWN_TRIGGER_TYPES: frozenset[str] = frozenset(
    {
        "map_zone_enter",
        "map_zone_exit",
        "item_use",
        "dialogue_choice",
        "time_based",
        "battle_outcome",
        "variable_change",
        "game_start",
        "day_change",
        "weekly_event",
    }
)

_SEMVER_RE = re.compile(r"^\d+\.\d+\.\d+$")


# ---------------------------------------------------------------------------
# Severity and issue types
# ---------------------------------------------------------------------------


class Severity(str, Enum):
    BLOCKING = "blocking"
    WARNING = "warning"
    INFO = "info"


@dataclass
class ValidationIssue:
    """A single validation finding."""

    severity: Severity
    check_id: str
    message: str
    path: Optional[str] = None

    def __str__(self) -> str:
        loc = f" [{self.path}]" if self.path else ""
        return f"[{self.severity.value.upper()}] {self.check_id}{loc}: {self.message}"


@dataclass
class ValidationReport:
    """Aggregated result of validating a campaign directory."""

    campaign_dir: Optional[Path] = None
    issues: list[ValidationIssue] = field(default_factory=list)

    # ------------------------------------------------------------------
    # Accessors
    # ------------------------------------------------------------------

    @property
    def blocking(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.BLOCKING]

    @property
    def warnings(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.WARNING]

    @property
    def infos(self) -> list[ValidationIssue]:
        return [i for i in self.issues if i.severity == Severity.INFO]

    @property
    def is_valid(self) -> bool:
        """True if there are no blocking errors."""
        return len(self.blocking) == 0

    # ------------------------------------------------------------------
    # Issue recording helpers
    # ------------------------------------------------------------------

    def add_blocking(
        self, check_id: str, message: str, path: Optional[str] = None
    ) -> None:
        self.issues.append(
            ValidationIssue(Severity.BLOCKING, check_id, message, path)
        )

    def add_warning(
        self, check_id: str, message: str, path: Optional[str] = None
    ) -> None:
        self.issues.append(
            ValidationIssue(Severity.WARNING, check_id, message, path)
        )

    def add_info(
        self, check_id: str, message: str, path: Optional[str] = None
    ) -> None:
        self.issues.append(
            ValidationIssue(Severity.INFO, check_id, message, path)
        )

    # ------------------------------------------------------------------
    # Formatting
    # ------------------------------------------------------------------

    def summary(self) -> str:
        lines = []
        if self.campaign_dir:
            lines.append(f"Campaign: {self.campaign_dir}")
        b, w, i = len(self.blocking), len(self.warnings), len(self.infos)
        lines.append(
            f"Result: {'VALID' if self.is_valid else 'INVALID'} "
            f"({b} blocking, {w} warnings, {i} info)"
        )
        for issue in self.issues:
            lines.append(f"  {issue}")
        return "\n".join(lines)

    def grouped_report(self) -> dict[str, list[str]]:
        """Return issues grouped by severity as string lists."""
        return {
            "blocking": [str(i) for i in self.blocking],
            "warnings": [str(i) for i in self.warnings],
            "info": [str(i) for i in self.infos],
        }


# ---------------------------------------------------------------------------
# Parsed map descriptor (from TMX)
# ---------------------------------------------------------------------------


@dataclass
class MapDescriptor:
    """Lightweight TMX parse result used during validation."""

    path: Path
    map_id: str
    layer_names: list[str]
    object_types: dict[
        str, list[dict]
    ]  # type -> list of object attribute dicts
    spawn_count: int
    encounter_zone_count: int
    transition_targets: list[str]
    npc_script_ids: list[str]
    has_orphan_layers: bool


# ---------------------------------------------------------------------------
# Main validator
# ---------------------------------------------------------------------------


class CampaignValidator:
    """
    Validates a campaign directory against all rules in campaign_maker_mvp.md §4.

    Parameters
    ----------
    known_monster_ids:
        Set of valid monster IDs. When provided, validates all encounter-table
        references against this set. When None, monster ID checks are skipped.
    known_action_types:
        Set of valid event-graph action types. Defaults to KNOWN_ACTION_TYPES.
    engine_version:
        The current engine version string (semver) used for compatibility checks.
    """

    def __init__(
        self,
        known_monster_ids: Optional[frozenset[str]] = None,
        known_action_types: Optional[frozenset[str]] = None,
        engine_version: str = ENGINE_VERSION,
    ) -> None:
        self._known_monster_ids = known_monster_ids
        self._known_action_types = known_action_types or KNOWN_ACTION_TYPES
        self._engine_version = engine_version

    # ------------------------------------------------------------------
    # Public entry point
    # ------------------------------------------------------------------

    def validate(self, campaign_dir: Path) -> ValidationReport:
        """
        Validate the campaign at *campaign_dir* and return a ValidationReport.

        Checks are performed in this order:
        1. Manifest (campaign.yaml) — must be present and schema-valid.
        2. Map files (maps/*.tmx) — per-map structural checks.
        3. Script files (scripts/*.json) — event graph structural checks.
        4. Campaign-level cross-reference checks.
        """
        report = ValidationReport(campaign_dir=campaign_dir)

        if not campaign_dir.exists() or not campaign_dir.is_dir():
            report.add_blocking(
                "campaign_dir_missing",
                f"Campaign directory does not exist: {campaign_dir}",
            )
            return report

        manifest = self._validate_manifest(campaign_dir, report)
        if manifest is None:
            return report

        map_descs, all_map_stems = self._validate_maps(campaign_dir, report)
        script_ids = self._validate_scripts(campaign_dir, report)

        self._check_campaign_level(
            manifest,
            campaign_dir,
            map_descs,
            all_map_stems,
            script_ids,
            report,
        )

        return report

    @staticmethod
    def _with_fix(message: str, fix: str) -> str:
        """Append a concrete fix suggestion to a validation message."""
        return f"{message} Fix: {fix}"

    # ------------------------------------------------------------------
    # Manifest validation (§4.1)
    # ------------------------------------------------------------------

    def _validate_manifest(
        self, campaign_dir: Path, report: ValidationReport
    ) -> Optional[CampaignManifest]:
        manifest_path = campaign_dir / "campaign.yaml"
        if not manifest_path.exists():
            report.add_blocking(
                "manifest_missing",
                "campaign.yaml not found in campaign directory",
                path="campaign.yaml",
            )
            return None

        try:
            raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8"))
        except yaml.YAMLError as exc:
            report.add_blocking(
                "manifest_parse_error",
                f"campaign.yaml could not be parsed: {exc}",
                path="campaign.yaml",
            )
            return None

        if not isinstance(raw, dict):
            report.add_blocking(
                "manifest_not_mapping",
                "campaign.yaml must be a YAML mapping at the top level",
                path="campaign.yaml",
            )
            return None

        try:
            manifest = CampaignManifest(**raw)
        except ValidationError as exc:
            for err in exc.errors():
                field_loc = ".".join(str(x) for x in err["loc"])
                report.add_blocking(
                    "manifest_field_invalid",
                    self._with_fix(
                        f"Field '{field_loc}' is invalid: {err['msg']}.",
                        "Update campaign.yaml so this field matches the manifest schema.",
                    ),
                    path="campaign.yaml",
                )
            return None

        # Engine version compatibility check
        if not self._semver_lte(
            manifest.engine_min_version, self._engine_version
        ):
            report.add_blocking(
                "engine_version_incompatible",
                self._with_fix(
                    (
                        f"campaign.yaml field 'engine_min_version' requires >= {manifest.engine_min_version}, "
                        f"but current engine is {self._engine_version}."
                    ),
                    "Lower engine_min_version or upgrade the engine version.",
                ),
                path="campaign.yaml",
            )

        logger.debug("Manifest valid: id=%s", manifest.id)
        return manifest

    # ------------------------------------------------------------------
    # Map validation (§4.2)
    # ------------------------------------------------------------------

    def _validate_maps(
        self, campaign_dir: Path, report: ValidationReport
    ) -> tuple[list[MapDescriptor], set[str]]:
        maps_dir = campaign_dir / "maps"
        if not maps_dir.exists():
            report.add_warning(
                "maps_dir_missing",
                "No maps/ directory found. Campaign has no maps.",
            )
            return [], set()

        tmx_paths = sorted(maps_dir.rglob("*.tmx"))
        if not tmx_paths:
            report.add_warning(
                "no_maps_found",
                "maps/ directory contains no .tmx files.",
            )
            return [], set()

        map_descs: list[MapDescriptor] = []
        seen_map_ids: dict[str, Path] = {}
        all_map_stems: set[str] = set()

        for tmx_path in tmx_paths:
            rel = tmx_path.relative_to(campaign_dir)
            desc = self._parse_map_file(tmx_path, report)
            if desc is None:
                continue

            all_map_stems.add(str(rel))

            # §4.2 map_id_unique
            if desc.map_id in seen_map_ids:
                report.add_blocking(
                    "map_id_unique",
                    (
                        f"Map ID '{desc.map_id}' is duplicated: "
                        f"{seen_map_ids[desc.map_id]} and {rel}"
                    ),
                    path=str(rel),
                )
            else:
                seen_map_ids[desc.map_id] = rel

            # §4.2 layer_naming_convention
            for layer_name in desc.layer_names:
                if (
                    "day" in layer_name.lower()
                    or "night" in layer_name.lower()
                ):
                    if not (
                        layer_name.startswith("day_")
                        or layer_name.startswith("night_")
                    ):
                        report.add_warning(
                            "layer_naming_convention",
                            (
                                f"Layer '{layer_name}' appears time-aware but "
                                "does not follow day_*/night_* naming convention."
                            ),
                            path=str(rel),
                        )

            # §4.2 orphan_layer
            if desc.has_orphan_layers:
                report.add_info(
                    "orphan_layer",
                    "Map contains layers with no tiles.",
                    path=str(rel),
                )

            # §4.2 encounter_zone_valid — validate encounter zone monster IDs
            for zone in desc.object_types.get("encounter_zone", []):
                monster_ids_raw = zone.get("monster_ids", "")
                monster_ids = [
                    m.strip() for m in monster_ids_raw.split(",") if m.strip()
                ]
                zone_id = zone.get("id", "unknown")
                if not monster_ids:
                    report.add_blocking(
                        "encounter_zone_valid",
                        self._with_fix(
                            f"Encounter zone object id='{zone_id}' field 'monster_ids' is empty.",
                            "Set the encounter_zone property monster_ids to one or more comma-separated monster IDs.",
                        ),
                        path=str(rel),
                    )
                elif self._known_monster_ids is not None:
                    for mid in monster_ids:
                        if mid not in self._known_monster_ids:
                            report.add_blocking(
                                "monster_id_valid",
                                self._with_fix(
                                    f"Encounter zone object id='{zone_id}' references unknown monster id '{mid}' in field 'monster_ids'.",
                                    "Correct the ID spelling or use an existing monster ID from the game database.",
                                ),
                                path=str(rel),
                            )

            # §4.2 npc_script_valid (checked in campaign-level after all scripts known)
            map_descs.append(desc)

        return map_descs, all_map_stems

    def _parse_map_file(
        self, tmx_path: Path, report: ValidationReport
    ) -> Optional[MapDescriptor]:
        tmx_path.name
        try:
            tree = ET.parse(tmx_path)
        except ET.ParseError as exc:
            report.add_blocking(
                "map_parse_error",
                f"TMX file could not be parsed as XML: {exc}",
                path=str(tmx_path),
            )
            return None

        root = tree.getroot()
        props = {
            p.get("name"): p.get("value")
            for p in root.findall("properties/property")
        }
        map_id = props.get("slug") or tmx_path.stem

        layer_names: list[str] = []
        has_orphan_layers = False
        for layer in root.findall("layer"):
            name = layer.get("name", "")
            layer_names.append(name)
            data_el = layer.find("data")
            if data_el is not None:
                text = (data_el.text or "").strip()
                if not text or all(c in ("0", ",", "\n", " ") for c in text):
                    has_orphan_layers = True

        objects_by_type: dict[str, list[dict]] = {}
        spawn_count = 0
        encounter_zone_count = 0
        transition_targets: list[str] = []
        npc_script_ids: list[str] = []

        for og in root.findall("objectgroup"):
            for obj in og.findall("object"):
                obj_type = obj.get("type", "")
                obj_props = {
                    p.get("name"): p.get("value")
                    for p in obj.findall("properties/property")
                }
                obj_data = {"id": obj.get("id", ""), **obj_props}

                objects_by_type.setdefault(obj_type, []).append(obj_data)

                if obj_type == "spawn_point":
                    spawn_count += 1
                elif obj_type == "encounter_zone":
                    encounter_zone_count += 1
                    obj_data["monster_ids"] = obj_props.get("monster_ids", "")
                elif obj_type == "map_transition":
                    target = obj_props.get("target_map", "")
                    if target:
                        transition_targets.append(target)
                elif obj_type == "npc":
                    script_id = obj_props.get("script_id", "")
                    if script_id:
                        npc_script_ids.append(script_id)

        return MapDescriptor(
            path=tmx_path,
            map_id=map_id,
            layer_names=layer_names,
            object_types=objects_by_type,
            spawn_count=spawn_count,
            encounter_zone_count=encounter_zone_count,
            transition_targets=transition_targets,
            npc_script_ids=npc_script_ids,
            has_orphan_layers=has_orphan_layers,
        )

    # ------------------------------------------------------------------
    # Script validation (§4.4)
    # ------------------------------------------------------------------

    def _validate_scripts(
        self, campaign_dir: Path, report: ValidationReport
    ) -> set[str]:
        """Parse all script files and return the set of known script IDs."""
        scripts_dir = campaign_dir / "scripts"
        if not scripts_dir.exists():
            return set()

        script_paths = sorted(scripts_dir.rglob("*.json"))
        if not script_paths:
            return set()

        script_ids: dict[str, Path] = {}
        call_graph: dict[str, list[str]] = {}

        for script_path in script_paths:
            rel = str(script_path.relative_to(campaign_dir))
            try:
                data = json.loads(script_path.read_text(encoding="utf-8"))
            except json.JSONDecodeError as exc:
                report.add_blocking(
                    "script_parse_error",
                    f"Script file could not be parsed as JSON: {exc}",
                    path=rel,
                )
                continue

            if not isinstance(data, dict):
                report.add_blocking(
                    "script_not_object",
                    "Script file must be a JSON object at the top level.",
                    path=rel,
                )
                continue

            sid = data.get("id")
            if not sid:
                report.add_blocking(
                    "script_id_missing",
                    "Script is missing required 'id' field.",
                    path=rel,
                )
                continue

            # §4.4 script_id_unique
            if sid in script_ids:
                report.add_blocking(
                    "script_id_unique",
                    self._with_fix(
                        f"Duplicate script id '{sid}' found in '{rel}' and '{script_ids[sid].relative_to(campaign_dir)}'.",
                        "Give one of these script files a unique id value.",
                    ),
                    path=rel,
                )
            else:
                script_ids[sid] = script_path

            # Validate action nodes
            calls: list[str] = []
            for node_index, node in enumerate(data.get("nodes", []), start=1):
                action_type = node.get("action") or node.get("type")
                node_id = node.get("id", f"index_{node_index}")
                if action_type == "call_script":
                    target = (node.get("args") or {}).get("script_id")
                    if target:
                        calls.append(target)
                elif (
                    action_type and action_type not in self._known_action_types
                ):
                    # §4.4 script_action_valid
                    report.add_blocking(
                        "script_action_valid",
                        self._with_fix(
                            f"Script '{sid}' node '{node_id}' (nodes[{node_index}].action) uses unknown action type '{action_type}'.",
                            "Replace it with a supported action type or remove this node.",
                        ),
                        path=rel,
                    )

                # §4.4 localization_key_defined — warn if dialog text_key used
                args = node.get("args") or {}
                if action_type == "dialog" and "text_key" in args:
                    locale_dir = campaign_dir / "locale"
                    if not locale_dir.exists():
                        report.add_warning(
                            "localization_key_defined",
                            (
                                f"Script '{sid}' references locale key "
                                f"'{args['text_key']}' in node '{node_id}', but no locale/ directory found."
                            ),
                            path=rel,
                        )

            call_graph[sid] = calls

        # §4.4 script_loop_detected — detect cycles using DFS
        self._check_script_cycles(call_graph, report, campaign_dir)

        return set(script_ids.keys())

    def _check_script_cycles(
        self,
        call_graph: dict[str, list[str]],
        report: ValidationReport,
        campaign_dir: Path,
    ) -> None:
        """DFS cycle detection in the script call graph."""
        visited: set[str] = set()
        in_stack: set[str] = set()

        def dfs(node: str) -> bool:
            if node in in_stack:
                return True  # cycle detected
            if node in visited:
                return False
            visited.add(node)
            in_stack.add(node)
            for neighbor in call_graph.get(node, []):
                if dfs(neighbor):
                    return True
            in_stack.discard(node)
            return False

        for sid in call_graph:
            if sid not in visited:
                if dfs(sid):
                    report.add_blocking(
                        "script_loop_detected",
                        self._with_fix(
                            f"Circular script reference detected involving script '{sid}'.",
                            "Remove at least one call_script edge so the call graph becomes acyclic.",
                        ),
                    )

    # ------------------------------------------------------------------
    # Campaign-level checks (§4.5)
    # ------------------------------------------------------------------

    def _check_campaign_level(
        self,
        manifest: CampaignManifest,
        campaign_dir: Path,
        map_descs: list[MapDescriptor],
        all_map_stems: set[str],
        script_ids: set[str],
        report: ValidationReport,
    ) -> None:
        # §4.5 start_map_reachable — the start_map file must exist
        start_map_path = campaign_dir / manifest.start_map
        if not start_map_path.exists():
            report.add_blocking(
                "start_map_reachable",
                self._with_fix(
                    f"campaign.yaml field 'start_map' points to missing file '{manifest.start_map}'.",
                    "Set start_map to an existing .tmx path relative to campaign root (for example: maps/start.tmx).",
                ),
                path=manifest.start_map,
            )
        else:
            # Check start map has a spawn point
            start_map_rel = manifest.start_map
            start_desc = next(
                (
                    d
                    for d in map_descs
                    if str(d.path.relative_to(campaign_dir)) == start_map_rel
                ),
                None,
            )
            if start_desc is not None and start_desc.spawn_count == 0:
                report.add_blocking(
                    "spawn_point_exists",
                    self._with_fix(
                        f"Start map '{manifest.start_map}' has no object of type 'spawn_point'.",
                        "Add a spawn_point object in the map's Events object layer.",
                    ),
                    path=manifest.start_map,
                )

        # §4.5 entry_script — must exist in scripts/
        if script_ids and manifest.entry_script not in script_ids:
            report.add_blocking(
                "entry_script_missing",
                self._with_fix(
                    (
                        f"campaign.yaml field 'entry_script' references '{manifest.entry_script}', "
                        f"but it was not found in scripts/. Known script ids: {sorted(script_ids)}."
                    ),
                    "Create the script file with that id or update entry_script to an existing id.",
                ),
                path="campaign.yaml",
            )

        # §4.2 spawn_point_exists for all maps listed as transition targets
        transition_target_map = {d.path.name: d for d in map_descs}
        for desc in map_descs:
            rel = str(desc.path.relative_to(campaign_dir))
            for target in desc.transition_targets:
                # §4.2 transition_target_valid
                target_name = Path(target).name
                if target not in all_map_stems and target_name not in {
                    d.path.name for d in map_descs
                }:
                    report.add_blocking(
                        "transition_target_valid",
                        self._with_fix(
                            f"Map transition target_map='{target}' in '{rel}' points to a missing map.",
                            "Update target_map to a valid path under maps/.",
                        ),
                        path=rel,
                    )
                else:
                    # Target exists — check it has a spawn point
                    target_desc = transition_target_map.get(target_name)
                    if (
                        target_desc is not None
                        and target_desc.spawn_count == 0
                    ):
                        report.add_blocking(
                            "spawn_point_exists",
                            self._with_fix(
                                f"Transition target '{target}' has no object of type 'spawn_point'.",
                                "Add a spawn_point object to the target map's Events object layer.",
                            ),
                            path=rel,
                        )

            # §4.2 npc_script_valid
            for sid in desc.npc_script_ids:
                if script_ids and sid not in script_ids:
                    report.add_blocking(
                        "npc_script_valid",
                        self._with_fix(
                            f"NPC in '{rel}' references missing script id '{sid}' via field 'script_id'.",
                            "Create a script with this id in scripts/ or update the NPC script_id property.",
                        ),
                        path=rel,
                    )

        # §4.5 no_unreachable_maps — BFS from start map
        if map_descs and manifest.start_map:
            self._check_map_reachability(
                manifest, campaign_dir, map_descs, all_map_stems, report
            )

        # §4.5 ruleset_valid — if campaign has ruleset overrides
        if manifest.ruleset:
            try:
                from tuxemon.rules.models import BattleRules

                BattleRules(
                    team_size=manifest.ruleset.team_size or 6,
                    level_cap=manifest.ruleset.level_cap,
                    active_clauses=manifest.ruleset.active_clauses or [],
                    allow_items_in_battle=(
                        manifest.ruleset.allow_items_in_battle
                        if manifest.ruleset.allow_items_in_battle is not None
                        else True
                    ),
                    allow_held_items=(
                        manifest.ruleset.allow_held_items
                        if manifest.ruleset.allow_held_items is not None
                        else True
                    ),
                )
            except Exception as exc:
                report.add_blocking(
                    "ruleset_valid",
                    f"Campaign ruleset override is invalid: {exc}",
                    path="campaign.yaml",
                )

    def _check_map_reachability(
        self,
        manifest: CampaignManifest,
        campaign_dir: Path,
        map_descs: list[MapDescriptor],
        all_map_stems: set[str],
        report: ValidationReport,
    ) -> None:
        """BFS from start_map; warn about maps not reachable from it."""
        start_name = Path(manifest.start_map).name
        name_to_desc = {d.path.name: d for d in map_descs}
        reachable: set[str] = set()
        queue: list[str] = [start_name]

        while queue:
            current = queue.pop()
            if current in reachable:
                continue
            reachable.add(current)
            desc = name_to_desc.get(current)
            if desc is None:
                continue
            for target in desc.transition_targets:
                target_name = Path(target).name
                if target_name not in reachable:
                    queue.append(target_name)

        for desc in map_descs:
            if desc.path.name not in reachable:
                report.add_warning(
                    "no_unreachable_maps",
                    f"Map '{desc.path.name}' is not reachable from the start map.",
                    path=str(desc.path.relative_to(campaign_dir)),
                )

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    @staticmethod
    def _semver_lte(a: str, b: str) -> bool:
        """Return True if semver string a <= b."""
        try:
            a_parts = tuple(int(x) for x in a.split("."))
            b_parts = tuple(int(x) for x in b.split("."))
            return a_parts <= b_parts
        except ValueError:
            return False

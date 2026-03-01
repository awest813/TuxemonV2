# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
TMX/TSX map and tileset validation for the Tiled editor workflow.

Validates map files for structural correctness and compliance with
OpenCapsuleMon map authoring conventions.  Designed to run without
pygame or display dependencies so it can be used in CI and editor
helper scripts.

Checks performed on TMX files:
  - Required map properties are present (``slug``).
  - The ``edges`` property, when present, has a recognised value.
  - The ``map_type`` property, when present, names a known type.
  - Tileset source references point to existing files.
  - Object names are non-empty.
  - Object types are within the allowed set.
  - ``event`` and ``init`` objects contain at least one action (``act*``).
  - Object coordinates are within the map bounds.

Checks performed on TSX files:
  - The tileset image file exists relative to the TSX file.
  - Per-tile property keys belong to the recognised set.
  - Direction-valued properties contain only valid direction tokens.
"""
from __future__ import annotations

import logging
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

VALID_EDGES: frozenset[str] = frozenset({"clamped", "looped"})

VALID_MAP_TYPES: frozenset[str] = frozenset(
    {"notype", "town", "route", "clinic", "shop", "dungeon"}
)

VALID_OBJECT_TYPES: frozenset[str] = frozenset(
    {"event", "init", "collision", "collision-line", "corner"}
)

# Tile property keys recognised by the engine.
VALID_TILE_PROPERTY_KEYS: frozenset[str] = frozenset(
    {
        "enter_from",
        "exit_from",
        "endure",
        "key",
        "push_direction",
        "push_strength",
        "speed_modifier",
        "surfable",
        "walkable",
        "climbable",
    }
)

VALID_DIRECTIONS: frozenset[str] = frozenset({"up", "down", "left", "right"})

DIRECTION_PROPERTY_KEYS: frozenset[str] = frozenset(
    {"enter_from", "exit_from", "endure", "push_direction"}
)


# ---------------------------------------------------------------------------
# Result dataclass
# ---------------------------------------------------------------------------


@dataclass
class ValidationResult:
    """Aggregated output of a single validation pass."""

    path: Path
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return not self.errors

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _read_xml(path: Path) -> ET.Element | None:
    """Parse an XML file and return the root element, or None on failure."""
    try:
        tree = ET.parse(path)
        return tree.getroot()
    except ET.ParseError as exc:
        logger.error("XML parse error in %s: %s", path, exc)
        return None
    except OSError as exc:
        logger.error("Cannot open %s: %s", path, exc)
        return None


def _get_properties(element: ET.Element) -> dict[str, str]:
    """Return the ``<properties>`` child key/value pairs for *element*."""
    props: dict[str, str] = {}
    for prop in element.findall("./properties/property"):
        name = prop.get("name", "")
        value = prop.get("value", "")
        if name:
            props[name] = value
    return props


def _validate_direction_value(value: str, key: str, label: str) -> list[str]:
    """Return error messages if *value* contains invalid direction tokens."""
    errors: list[str] = []
    if key == "push_direction":
        tokens = [value.strip().lower()] if value.strip() else []
    else:
        tokens = [t.strip().lower() for t in value.split(",") if t.strip()]

    for token in tokens:
        if token not in VALID_DIRECTIONS:
            errors.append(
                f"{label}: tile property '{key}' has invalid direction token "
                f"'{token}' (valid: {', '.join(sorted(VALID_DIRECTIONS))})"
            )
    return errors


# ---------------------------------------------------------------------------
# TSX validation
# ---------------------------------------------------------------------------


def validate_tsx(path: Path) -> ValidationResult:
    """Validate a single ``.tsx`` tileset file.

    Parameters:
        path: Absolute or relative path to the ``.tsx`` file.

    Returns:
        A :class:`ValidationResult` with any discovered errors/warnings.
    """
    result = ValidationResult(path=path)

    root = _read_xml(path)
    if root is None:
        result.add_error("Cannot parse TSX file")
        return result

    # Verify that the image source exists.
    image_el = root.find("image")
    if image_el is not None:
        img_source = image_el.get("source", "")
        if img_source:
            img_path = path.parent / img_source
            if not img_path.exists():
                result.add_error(
                    f"Referenced image not found: {img_source!r} "
                    f"(resolved: {img_path})"
                )
    else:
        result.add_warning("No <image> element found in tileset")

    # Validate per-tile properties.
    for tile_el in root.findall("tile"):
        tile_id = tile_el.get("id", "?")
        label = f"tile id={tile_id}"
        props = _get_properties(tile_el)
        for key, value in props.items():
            key_lower = key.lower()
            if key_lower not in VALID_TILE_PROPERTY_KEYS:
                result.add_warning(
                    f"{label}: unrecognised property key '{key}'"
                )
                continue
            if key_lower in DIRECTION_PROPERTY_KEYS and value:
                errors = _validate_direction_value(value, key_lower, label)
                result.errors.extend(errors)

    return result


# ---------------------------------------------------------------------------
# TMX validation
# ---------------------------------------------------------------------------


def validate_tmx(path: Path) -> ValidationResult:
    """Validate a single ``.tmx`` map file.

    Parameters:
        path: Absolute or relative path to the ``.tmx`` file.

    Returns:
        A :class:`ValidationResult` with any discovered errors/warnings.
    """
    result = ValidationResult(path=path)

    root = _read_xml(path)
    if root is None:
        result.add_error("Cannot parse TMX file")
        return result

    try:
        map_width = int(root.get("width", 0))
        map_height = int(root.get("height", 0))
    except ValueError:
        result.add_error("Map 'width' or 'height' attribute is not an integer")
        map_width = map_height = 0

    map_props = _get_properties(root)

    # Required: slug
    slug = map_props.get("slug", "").strip()
    if not slug:
        result.add_error("Missing required map property 'slug'")

    # Optional: edges
    edges = map_props.get("edges", "").strip()
    if edges and edges not in VALID_EDGES:
        result.add_error(
            f"Map property 'edges' has invalid value '{edges}' "
            f"(valid: {', '.join(sorted(VALID_EDGES))})"
        )

    # Optional: map_type
    map_type = map_props.get("map_type", "").strip()
    if map_type and map_type not in VALID_MAP_TYPES:
        result.add_error(
            f"Map property 'map_type' has invalid value '{map_type}' "
            f"(valid: {', '.join(sorted(VALID_MAP_TYPES))})"
        )

    # Tileset source references.
    for ts_el in root.findall("tileset"):
        source = ts_el.get("source", "").strip()
        if source:
            ts_path = path.parent / source
            if not ts_path.exists():
                result.add_error(
                    f"Tileset source not found: {source!r} "
                    f"(resolved: {ts_path})"
                )

    # Object validation.
    for obj_el in root.findall(".//objectgroup/object"):
        obj_name = (obj_el.get("name") or "").strip()
        obj_type = (obj_el.get("type") or "").strip()

        if not obj_name:
            result.add_warning(
                f"Object at position "
                f"({obj_el.get('x', '?')}, {obj_el.get('y', '?')}) "
                f"has no name"
            )

        if obj_type and obj_type not in VALID_OBJECT_TYPES:
            result.add_warning(
                f"Object '{obj_name}' has unrecognised type '{obj_type}'"
            )

        # Events and inits must have at least one action.
        if obj_type in {"event", "init"}:
            obj_props = _get_properties(obj_el)
            has_action = any(k.startswith("act") for k in obj_props)
            if not has_action:
                result.add_warning(
                    f"Object '{obj_name}' (type='{obj_type}') has no "
                    f"action properties (expected keys starting with 'act')"
                )

        # Coordinate bounds check (pixel coords; object x/y may be floats).
        if map_width > 0 and map_height > 0:
            try:
                tilewidth = int(root.get("tilewidth", 16))
                tileheight = int(root.get("tileheight", 16))
                obj_x = float(obj_el.get("x", 0))
                obj_y = float(obj_el.get("y", 0))
                tile_x = int(obj_x / tilewidth)
                tile_y = int(obj_y / tileheight)
                if tile_x < 0 or tile_x >= map_width:
                    result.add_warning(
                        f"Object '{obj_name}' tile-x {tile_x} is outside "
                        f"map width {map_width}"
                    )
                if tile_y < 0 or tile_y >= map_height:
                    result.add_warning(
                        f"Object '{obj_name}' tile-y {tile_y} is outside "
                        f"map height {map_height}"
                    )
            except (ValueError, ZeroDivisionError):
                pass

    return result


# ---------------------------------------------------------------------------
# Batch helpers
# ---------------------------------------------------------------------------


def validate_map_directory(
    maps_dir: Path,
    tilesets_dir: Path | None = None,
) -> list[ValidationResult]:
    """Validate all ``.tmx`` files in *maps_dir*.

    Parameters:
        maps_dir: Directory containing ``.tmx`` map files.
        tilesets_dir: Optional directory to also validate ``.tsx`` files in.

    Returns:
        One :class:`ValidationResult` per processed file.
    """
    results: list[ValidationResult] = []

    for tmx_path in sorted(maps_dir.glob("*.tmx")):
        results.append(validate_tmx(tmx_path))

    if tilesets_dir is not None:
        for tsx_path in sorted(tilesets_dir.glob("*.tsx")):
            results.append(validate_tsx(tsx_path))

    return results

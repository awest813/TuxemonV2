# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Unit tests for tuxemon.map.validator.

Tests are self-contained: each test writes minimal XML fixtures to a
temporary directory, runs the validator, and inspects the result.
No pygame, display, or full-game initialisation is required.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from tuxemon.map.validator import (
    ValidationResult,
    validate_map_directory,
    validate_tmx,
    validate_tsx,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _write(tmp_path: Path, filename: str, content: str) -> Path:
    p = tmp_path / filename
    p.write_text(content, encoding="utf-8")
    return p


def _minimal_tmx(
    *,
    slug: str = "test_map",
    edges: str = "",
    map_type: str = "",
    extra_props: str = "",
    extra_content: str = "",
    width: int = 10,
    height: int = 10,
) -> str:
    """Return a minimal but valid TMX document string."""
    props = f'<property name="slug" value="{slug}"/>\n'
    if edges:
        props += f'<property name="edges" value="{edges}"/>\n'
    if map_type:
        props += f'<property name="map_type" value="{map_type}"/>\n'
    props += extra_props

    return f"""<?xml version="1.0" encoding="UTF-8"?>
<map version="1.10" width="{width}" height="{height}"
     tilewidth="16" tileheight="16">
  <properties>
    {props}
  </properties>
  {extra_content}
</map>"""


def _minimal_tsx(
    *,
    image_source: str = "sheet.png",
    extra_tiles: str = "",
) -> str:
    """Return a minimal TSX document string."""
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<tileset version="1.10" name="test" tilewidth="16" tileheight="16"
         tilecount="1" columns="1">
  <image source="{image_source}" width="16" height="16"/>
  {extra_tiles}
</tileset>"""


# ---------------------------------------------------------------------------
# TMX validation – required properties
# ---------------------------------------------------------------------------


class TestTmxRequiredProperties:
    def test_valid_map_passes(self, tmp_path):
        p = _write(tmp_path, "map.tmx", _minimal_tmx())
        r = validate_tmx(p)
        assert r.ok, r.errors

    def test_missing_slug_is_error(self, tmp_path):
        tmx = """<?xml version="1.0" encoding="UTF-8"?>
<map version="1.10" width="10" height="10" tilewidth="16" tileheight="16">
  <properties/>
</map>"""
        p = _write(tmp_path, "map.tmx", tmx)
        r = validate_tmx(p)
        assert not r.ok
        assert any("slug" in e for e in r.errors)

    def test_empty_slug_is_error(self, tmp_path):
        extra = '<property name="slug" value=""/>'
        tmx = f"""<?xml version="1.0" encoding="UTF-8"?>
<map version="1.10" width="10" height="10" tilewidth="16" tileheight="16">
  <properties>{extra}</properties>
</map>"""
        p = _write(tmp_path, "map.tmx", tmx)
        r = validate_tmx(p)
        assert not r.ok
        assert any("slug" in e for e in r.errors)


# ---------------------------------------------------------------------------
# TMX validation – edges property
# ---------------------------------------------------------------------------


class TestTmxEdges:
    def test_valid_edges_clamped(self, tmp_path):
        p = _write(tmp_path, "map.tmx", _minimal_tmx(edges="clamped"))
        r = validate_tmx(p)
        assert r.ok, r.errors

    def test_valid_edges_looped(self, tmp_path):
        p = _write(tmp_path, "map.tmx", _minimal_tmx(edges="looped"))
        r = validate_tmx(p)
        assert r.ok, r.errors

    def test_invalid_edges_is_error(self, tmp_path):
        p = _write(tmp_path, "map.tmx", _minimal_tmx(edges="infinite"))
        r = validate_tmx(p)
        assert not r.ok
        assert any("edges" in e for e in r.errors)

    def test_absent_edges_ok(self, tmp_path):
        p = _write(tmp_path, "map.tmx", _minimal_tmx(edges=""))
        r = validate_tmx(p)
        assert r.ok, r.errors


# ---------------------------------------------------------------------------
# TMX validation – map_type property
# ---------------------------------------------------------------------------


class TestTmxMapType:
    @pytest.mark.parametrize(
        "mt", ["notype", "town", "route", "clinic", "shop", "dungeon"]
    )
    def test_valid_map_types(self, tmp_path, mt):
        p = _write(tmp_path, "map.tmx", _minimal_tmx(map_type=mt))
        r = validate_tmx(p)
        assert r.ok, r.errors

    def test_invalid_map_type_is_error(self, tmp_path):
        p = _write(tmp_path, "map.tmx", _minimal_tmx(map_type="forest"))
        r = validate_tmx(p)
        assert not r.ok
        assert any("map_type" in e for e in r.errors)

    def test_absent_map_type_ok(self, tmp_path):
        p = _write(tmp_path, "map.tmx", _minimal_tmx(map_type=""))
        r = validate_tmx(p)
        assert r.ok, r.errors


# ---------------------------------------------------------------------------
# TMX validation – tileset references
# ---------------------------------------------------------------------------


class TestTmxTilesetRefs:
    def test_existing_tsx_passes(self, tmp_path):
        (tmp_path / "sheet.tsx").write_text(
            _minimal_tsx(), encoding="utf-8"
        )
        (tmp_path / "sheet.png").write_bytes(b"")
        extra = '<tileset firstgid="1" source="sheet.tsx"/>'
        p = _write(tmp_path, "map.tmx", _minimal_tmx(extra_content=extra))
        r = validate_tmx(p)
        assert r.ok, r.errors

    def test_missing_tsx_is_error(self, tmp_path):
        extra = '<tileset firstgid="1" source="missing.tsx"/>'
        p = _write(tmp_path, "map.tmx", _minimal_tmx(extra_content=extra))
        r = validate_tmx(p)
        assert not r.ok
        assert any("missing.tsx" in e for e in r.errors)


# ---------------------------------------------------------------------------
# TMX validation – objects
# ---------------------------------------------------------------------------


class TestTmxObjects:
    def _tmx_with_objects(self, *objects: str) -> str:
        obj_xml = "\n".join(objects)
        extra = f"""<objectgroup name="events">
          {obj_xml}
        </objectgroup>"""
        return _minimal_tmx(extra_content=extra)

    def test_event_with_action_passes(self, tmp_path):
        obj = """<object name="sign" type="event" x="16" y="16"
                         width="16" height="16">
          <properties>
            <property name="act10" value="open_dialog Hello"/>
          </properties>
        </object>"""
        p = _write(tmp_path, "map.tmx", self._tmx_with_objects(obj))
        r = validate_tmx(p)
        assert r.ok, r.errors

    def test_event_without_action_is_warning(self, tmp_path):
        obj = """<object name="sign" type="event" x="16" y="16"
                         width="16" height="16">
          <properties>
            <property name="cond10" value="player_at 1,1"/>
          </properties>
        </object>"""
        p = _write(tmp_path, "map.tmx", self._tmx_with_objects(obj))
        r = validate_tmx(p)
        assert r.ok  # no hard error
        assert any("no action" in w for w in r.warnings)

    def test_object_without_name_is_warning(self, tmp_path):
        obj = """<object type="collision" x="0" y="0"
                         width="16" height="16"/>"""
        p = _write(tmp_path, "map.tmx", self._tmx_with_objects(obj))
        r = validate_tmx(p)
        assert any("no name" in w for w in r.warnings)

    def test_unknown_object_type_is_warning(self, tmp_path):
        obj = """<object name="mystery" type="unknown_type"
                         x="16" y="16" width="16" height="16"/>"""
        p = _write(tmp_path, "map.tmx", self._tmx_with_objects(obj))
        r = validate_tmx(p)
        assert any("unrecognised type" in w for w in r.warnings)

    def test_object_out_of_bounds_is_warning(self, tmp_path):
        # Map is 10x10 tiles; object placed at tile (15,15) is out of bounds.
        obj = """<object name="oor" type="event" x="240" y="240"
                         width="16" height="16">
          <properties>
            <property name="act10" value="open_dialog OOR"/>
          </properties>
        </object>"""
        p = _write(tmp_path, "map.tmx", self._tmx_with_objects(obj))
        r = validate_tmx(p)
        assert any("outside" in w for w in r.warnings)

    def test_collision_object_passes(self, tmp_path):
        obj = """<object name="wall" type="collision" x="16" y="16"
                         width="16" height="16"/>"""
        p = _write(tmp_path, "map.tmx", self._tmx_with_objects(obj))
        r = validate_tmx(p)
        assert r.ok, r.errors


# ---------------------------------------------------------------------------
# TSX validation
# ---------------------------------------------------------------------------


class TestTsxValidation:
    def test_valid_tileset_passes(self, tmp_path):
        (tmp_path / "sheet.png").write_bytes(b"")
        p = _write(tmp_path, "sheet.tsx", _minimal_tsx())
        r = validate_tsx(p)
        assert r.ok, r.errors

    def test_missing_image_is_error(self, tmp_path):
        # Do NOT create sheet.png
        p = _write(tmp_path, "sheet.tsx", _minimal_tsx())
        r = validate_tsx(p)
        assert not r.ok
        assert any("image not found" in e.lower() for e in r.errors)

    def test_valid_tile_directions(self, tmp_path):
        (tmp_path / "sheet.png").write_bytes(b"")
        tiles = """<tile id="0">
          <properties>
            <property name="enter_from" value="up,down"/>
            <property name="exit_from" value="left,right"/>
          </properties>
        </tile>"""
        p = _write(tmp_path, "sheet.tsx", _minimal_tsx(extra_tiles=tiles))
        r = validate_tsx(p)
        assert r.ok, r.errors

    def test_invalid_direction_is_error(self, tmp_path):
        (tmp_path / "sheet.png").write_bytes(b"")
        tiles = """<tile id="0">
          <properties>
            <property name="enter_from" value="north,south"/>
          </properties>
        </tile>"""
        p = _write(tmp_path, "sheet.tsx", _minimal_tsx(extra_tiles=tiles))
        r = validate_tsx(p)
        assert not r.ok
        assert any("north" in e or "south" in e for e in r.errors)

    def test_unrecognised_tile_property_is_warning(self, tmp_path):
        (tmp_path / "sheet.png").write_bytes(b"")
        tiles = """<tile id="0">
          <properties>
            <property name="custom_flag" value="true"/>
          </properties>
        </tile>"""
        p = _write(tmp_path, "sheet.tsx", _minimal_tsx(extra_tiles=tiles))
        r = validate_tsx(p)
        assert r.ok  # warning, not error
        assert any("custom_flag" in w for w in r.warnings)


# ---------------------------------------------------------------------------
# Batch validation
# ---------------------------------------------------------------------------


class TestValidateMapDirectory:
    def test_scans_tmx_files(self, tmp_path):
        maps = tmp_path / "maps"
        maps.mkdir()
        for name in ("alpha.tmx", "beta.tmx"):
            (maps / name).write_text(_minimal_tmx(), encoding="utf-8")
        results = validate_map_directory(maps)
        assert len(results) == 2

    def test_includes_tsx_when_tilesets_dir_given(self, tmp_path):
        maps = tmp_path / "maps"
        maps.mkdir()
        tilesets = tmp_path / "tilesets"
        tilesets.mkdir()
        (maps / "map.tmx").write_text(_minimal_tmx(), encoding="utf-8")
        (tilesets / "sheet.png").write_bytes(b"")
        (tilesets / "sheet.tsx").write_text(_minimal_tsx(), encoding="utf-8")
        results = validate_map_directory(maps, tilesets)
        assert len(results) == 2  # 1 TMX + 1 TSX

    def test_empty_directory_returns_empty_list(self, tmp_path):
        maps = tmp_path / "maps"
        maps.mkdir()
        results = validate_map_directory(maps)
        assert results == []

    def test_non_tmx_files_ignored(self, tmp_path):
        maps = tmp_path / "maps"
        maps.mkdir()
        (maps / "readme.txt").write_text("ignore me", encoding="utf-8")
        (maps / "map.yaml").write_text("events: {}", encoding="utf-8")
        results = validate_map_directory(maps)
        assert results == []


# ---------------------------------------------------------------------------
# ValidationResult helper methods
# ---------------------------------------------------------------------------


class TestValidationResult:
    def test_ok_when_no_errors(self):
        r = ValidationResult(path=Path("dummy.tmx"))
        assert r.ok

    def test_not_ok_when_has_errors(self):
        r = ValidationResult(path=Path("dummy.tmx"))
        r.add_error("something broke")
        assert not r.ok

    def test_warnings_do_not_affect_ok(self):
        r = ValidationResult(path=Path("dummy.tmx"))
        r.add_warning("potential issue")
        assert r.ok

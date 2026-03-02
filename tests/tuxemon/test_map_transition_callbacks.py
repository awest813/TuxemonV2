# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for MapTransition post-change listener callbacks (Hook 4.3 support).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from tuxemon.map.transition import MapTransition


def _make_transition() -> MapTransition:
    """Return a MapTransition with all dependencies mocked."""
    mt = MapTransition.__new__(MapTransition)
    mt.map_loader = MagicMock()
    mt.map_manager = MagicMock()
    mt.npc_manager = MagicMock()
    mt.boundary = MagicMock()
    mt.event_engine = MagicMock()
    mt._post_change_listeners = []
    return mt


def test_register_post_change_listener():
    mt = _make_transition()
    cb = MagicMock()
    mt.register_post_change_listener(cb)
    assert cb in mt._post_change_listeners


def test_listener_called_after_change_map():
    mt = _make_transition()
    received: list[str] = []
    mt.register_post_change_listener(received.append)

    fake_map = MagicMock()
    fake_map.filename = "test_map"
    mt.map_manager.current_map = fake_map
    mt.map_loader.load_map_data.return_value = fake_map

    mt.change_map("test_map")

    assert received == ["test_map"]


def test_multiple_listeners_all_called():
    mt = _make_transition()
    calls_a: list[str] = []
    calls_b: list[str] = []
    mt.register_post_change_listener(calls_a.append)
    mt.register_post_change_listener(calls_b.append)

    fake_map = MagicMock()
    fake_map.filename = "zone_a"
    mt.map_manager.current_map = None
    mt.map_loader.load_map_data.return_value = fake_map

    mt.change_map("zone_a")

    assert calls_a == ["zone_a"]
    assert calls_b == ["zone_a"]


def test_listener_receives_empty_string_for_yaml_map():
    mt = _make_transition()
    received: list[str] = []
    mt.register_post_change_listener(received.append)

    null_map = MagicMock()
    mt.map_loader.load_null_map.return_value = null_map
    mt.map_manager.current_map = None

    mt.change_map(yaml_path="some/path.yaml")

    assert received == [""]


def test_listener_exception_does_not_propagate():
    mt = _make_transition()

    def bad_listener(slug: str) -> None:
        raise RuntimeError("listener error")

    mt.register_post_change_listener(bad_listener)

    fake_map = MagicMock()
    mt.map_manager.current_map = None
    mt.map_loader.load_map_data.return_value = fake_map

    mt.change_map("test_map")


def test_no_listeners_change_map_still_works():
    mt = _make_transition()
    fake_map = MagicMock()
    mt.map_manager.current_map = None
    mt.map_loader.load_map_data.return_value = fake_map
    mt.change_map("test_map")

# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Tests for tuxemon.campaign.event_graph — EventGraph, EventNode, EventTrigger,
and EventGraphBuilder.
"""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from tuxemon.campaign.event_graph import (
    ActionType,
    EventGraph,
    EventGraphBuilder,
    EventNode,
    EventTrigger,
    TriggerType,
)


class TestEventTrigger:
    def test_valid_trigger(self):
        t = EventTrigger(type=TriggerType.GAME_START)
        assert t.type == TriggerType.GAME_START

    def test_trigger_with_args(self):
        t = EventTrigger(
            type=TriggerType.MAP_ZONE_ENTER, args={"zone": "village_zone"}
        )
        assert t.args["zone"] == "village_zone"

    def test_invalid_trigger_type(self):
        with pytest.raises(ValidationError):
            EventTrigger(type="fly_to_moon")


class TestEventNode:
    def test_valid_node(self):
        node = EventNode(
            id="node_a", action=ActionType.DIALOG, args={"text_key": "k"}
        )
        assert node.id == "node_a"

    def test_invalid_node_id_uppercase(self):
        with pytest.raises(ValidationError):
            EventNode(id="NodeA", action=ActionType.DIALOG)

    def test_invalid_action_type(self):
        with pytest.raises(ValidationError):
            EventNode(id="node_a", action="do_magic_trick")

    def test_node_with_next(self):
        node = EventNode(id="node_a", action=ActionType.DIALOG, next="node_b")
        assert node.next == "node_b"

    def test_node_with_branches(self):
        node = EventNode(
            id="node_a",
            action=ActionType.CHECK_VARIABLE,
            branches={"true": "node_b", "false": "node_c"},
        )
        assert "true" in node.branches


class TestEventGraph:
    def _valid_graph(self, **overrides) -> dict:
        base = {
            "id": "test_script",
            "triggers": [{"type": "game_start", "args": {}}],
            "nodes": [
                {
                    "id": "node_start",
                    "action": "dialog",
                    "args": {"text_key": "intro.text"},
                    "next": None,
                    "branches": {},
                }
            ],
            "entry_node": "node_start",
        }
        base.update(overrides)
        return base

    def test_valid_graph(self):
        g = EventGraph(**self._valid_graph())
        assert g.id == "test_script"

    def test_invalid_next_reference(self):
        with pytest.raises(ValidationError):
            EventGraph(
                **self._valid_graph(
                    nodes=[
                        {
                            "id": "node_start",
                            "action": "dialog",
                            "args": {},
                            "next": "nonexistent_node",
                            "branches": {},
                        }
                    ]
                )
            )

    def test_invalid_entry_node(self):
        with pytest.raises(ValidationError):
            EventGraph(**self._valid_graph(entry_node="phantom_node"))

    def test_internal_cycle_raises(self):
        with pytest.raises(ValidationError):
            EventGraph(
                id="cycling",
                triggers=[{"type": "game_start", "args": {}}],
                nodes=[
                    {
                        "id": "node_a",
                        "action": "dialog",
                        "args": {},
                        "next": "node_b",
                        "branches": {},
                    },
                    {
                        "id": "node_b",
                        "action": "dialog",
                        "args": {},
                        "next": "node_a",
                        "branches": {},
                    },
                ],
            )

    def test_no_nodes_is_valid(self):
        g = EventGraph(id="empty_script", triggers=[])
        assert g.nodes == []

    def test_to_json_round_trip(self):
        g = EventGraph(**self._valid_graph())
        json_str = g.to_json()
        g2 = EventGraph.from_json(json_str)
        assert g2.id == g.id
        assert len(g2.nodes) == len(g.nodes)

    def test_save_and_load_from_file(self, tmp_path):
        g = EventGraph(**self._valid_graph())
        saved_path = g.save(tmp_path)
        assert saved_path.exists()
        g2 = EventGraph.from_file(saved_path)
        assert g2.id == g.id

    def test_from_json_string(self):
        data = {
            "id": "from_json",
            "triggers": [],
            "nodes": [],
        }
        g = EventGraph.from_json(json.dumps(data))
        assert g.id == "from_json"

    def test_call_script_to_other_script_allowed(self):
        """call_script targeting another script ID should NOT be treated as a cycle."""
        g = EventGraph(
            id="script_a",
            triggers=[{"type": "game_start", "args": {}}],
            nodes=[
                {
                    "id": "node_call",
                    "action": "call_script",
                    "args": {"script_id": "script_b"},
                    "next": None,
                    "branches": {},
                }
            ],
        )
        assert g.id == "script_a"


class TestEventGraphBuilder:
    def test_build_simple_dialog_graph(self):
        g = (
            EventGraphBuilder("shop_open")
            .description("Opens the shop.")
            .on_trigger(TriggerType.MAP_ZONE_ENTER, zone="shop_zone")
            .add_dialog("greet", text_key="shop.greeting")
            .build()
        )
        assert g.id == "shop_open"
        assert len(g.triggers) == 1
        assert len(g.nodes) == 1
        assert g.nodes[0].action == ActionType.DIALOG

    def test_build_chained_nodes(self):
        g = (
            EventGraphBuilder("intro")
            .on_trigger(TriggerType.GAME_START)
            .add_dialog("greet", text_key="intro.text", next_node="set_var")
            .add_set_variable("set_var", key="started", value="true")
            .build()
        )
        assert g.nodes[0].next == "set_var"
        assert g.nodes[1].action == ActionType.SET_VARIABLE

    def test_build_with_entry_node(self):
        g = (
            EventGraphBuilder("story")
            .on_trigger(TriggerType.GAME_START)
            .add_dialog("start_node", text_key="key")
            .entry("start_node")
            .build()
        )
        assert g.entry_node == "start_node"

    def test_build_produces_event_graph_instance(self):
        g = EventGraphBuilder("test").build()
        assert isinstance(g, EventGraph)

    def test_invalid_next_in_built_graph_raises(self):
        """Builder produces correct data; validator should catch bad references."""
        with pytest.raises(Exception):
            (
                EventGraphBuilder("broken")
                .on_trigger(TriggerType.GAME_START)
                .add_action(
                    "node_a",
                    ActionType.DIALOG,
                    args={"text_key": "k"},
                    next_node="missing_node",
                )
                .build()
            )

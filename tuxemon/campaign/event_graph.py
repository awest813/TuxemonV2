# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Event graph data model for campaign event authoring.

Implements the event trigger and action graph described in
docs/campaign_maker_mvp.md §3 Workflow C.

The event graph is the data-layer representation of the visual event graph
editor. Creators connect trigger conditions to action chains; this module
provides the schema, validation, and JSON serialization for those graphs.

Script files are stored as JSON in the campaign's scripts/ directory.
Each file represents one event graph (script). The CampaignValidator
(validator.py) reads these files during the campaign validation pass.
"""

from __future__ import annotations

import re
from enum import Enum
from pathlib import Path
from typing import Any, Optional

from pydantic import BaseModel, Field, field_validator, model_validator

from tuxemon.campaign.validator import KNOWN_ACTION_TYPES, KNOWN_TRIGGER_TYPES

# ---------------------------------------------------------------------------
# Trigger types
# ---------------------------------------------------------------------------


class TriggerType(str, Enum):
    MAP_ZONE_ENTER = "map_zone_enter"
    MAP_ZONE_EXIT = "map_zone_exit"
    ITEM_USE = "item_use"
    DIALOGUE_CHOICE = "dialogue_choice"
    TIME_BASED = "time_based"
    BATTLE_OUTCOME = "battle_outcome"
    VARIABLE_CHANGE = "variable_change"
    GAME_START = "game_start"
    DAY_CHANGE = "day_change"
    WEEKLY_EVENT = "weekly_event"


class EventTrigger(BaseModel):
    """
    A condition that activates the event graph.

    At least one trigger must be defined per script.
    """

    type: TriggerType
    args: dict[str, Any] = Field(default_factory=dict)

    @field_validator("type", mode="before")
    @classmethod
    def _validate_trigger_type(cls, v: str) -> str:
        if v not in KNOWN_TRIGGER_TYPES:
            raise ValueError(
                f"Unknown trigger type '{v}'. "
                f"Must be one of: {sorted(KNOWN_TRIGGER_TYPES)}"
            )
        return v


# ---------------------------------------------------------------------------
# Action node types
# ---------------------------------------------------------------------------


class ActionType(str, Enum):
    DIALOG = "dialog"
    SET_VARIABLE = "set_variable"
    CHECK_VARIABLE = "check_variable"
    SPAWN_NPC = "spawn_npc"
    REMOVE_NPC = "remove_npc"
    OPEN_SHOP = "open_shop"
    START_BATTLE = "start_battle"
    END_BATTLE = "end_battle"
    PLAY_MUSIC = "play_music"
    STOP_MUSIC = "stop_music"
    PLAY_SOUND = "play_sound"
    AWARD_ITEM = "award_item"
    REMOVE_ITEM = "remove_item"
    AWARD_MONSTER = "award_monster"
    TELEPORT = "teleport"
    OPEN_MENU = "open_menu"
    CLOSE_MENU = "close_menu"
    PLAY_CUTSCENE = "play_cutscene"
    WAIT = "wait"
    CALL_SCRIPT = "call_script"


_NODE_ID_RE = re.compile(r"^[a-z][a-z0-9_]{0,63}$")


class EventNode(BaseModel):
    """
    A single node in the event graph action chain.

    Nodes are connected via the ``next`` field, forming a directed graph.
    The graph must be acyclic within a single script (cycles are only
    permitted via ``call_script`` between separate scripts).
    """

    id: str = Field(..., min_length=1, max_length=64)
    action: ActionType
    args: dict[str, Any] = Field(default_factory=dict)
    next: Optional[str] = None
    branches: dict[str, str] = Field(default_factory=dict)

    @field_validator("id")
    @classmethod
    def _validate_node_id(cls, v: str) -> str:
        if not _NODE_ID_RE.match(v):
            raise ValueError(
                f"Node ID '{v}' is invalid. "
                "Must start with a lowercase letter and contain only "
                "lowercase letters, digits, and underscores."
            )
        return v

    @field_validator("action", mode="before")
    @classmethod
    def _validate_action_type(cls, v: str) -> str:
        if v not in KNOWN_ACTION_TYPES:
            raise ValueError(
                f"Unknown action type '{v}'. "
                f"Must be one of: {sorted(KNOWN_ACTION_TYPES)}"
            )
        return v


# ---------------------------------------------------------------------------
# Event graph (script)
# ---------------------------------------------------------------------------


class EventGraph(BaseModel):
    """
    A complete event graph (script) consisting of triggers and action nodes.

    This is the top-level data model for a campaign script file.
    Campaign scripts are stored as JSON files in the scripts/ directory.

    Example::

        graph = EventGraph(
            id="main_intro",
            triggers=[EventTrigger(type=TriggerType.GAME_START)],
            nodes=[
                EventNode(
                    id="node_greet",
                    action=ActionType.DIALOG,
                    args={"text_key": "intro.greeting"},
                    next="node_set_started",
                ),
                EventNode(
                    id="node_set_started",
                    action=ActionType.SET_VARIABLE,
                    args={"key": "intro_done", "value": "true"},
                ),
            ],
        )
    """

    id: str = Field(..., min_length=1, max_length=64)
    description: str = ""
    triggers: list[EventTrigger] = Field(default_factory=list)
    nodes: list[EventNode] = Field(default_factory=list)
    entry_node: Optional[str] = None

    @model_validator(mode="after")
    def _validate_graph_integrity(self) -> "EventGraph":
        if not self.nodes:
            return self
        node_ids = {n.id for n in self.nodes}

        # Validate next references
        for node in self.nodes:
            if node.next and node.next not in node_ids:
                raise ValueError(
                    f"Node '{node.id}' has next='{node.next}' "
                    f"which is not a known node ID in this script."
                )
            for branch_target in node.branches.values():
                if branch_target not in node_ids:
                    raise ValueError(
                        f"Node '{node.id}' branch target '{branch_target}' "
                        "is not a known node ID in this script."
                    )

        # Validate entry_node if specified
        if self.entry_node and self.entry_node not in node_ids:
            raise ValueError(
                f"entry_node '{self.entry_node}' is not a known node ID."
            )

        # Detect internal cycles (call_script to other scripts is allowed)
        self._detect_cycles(node_ids)

        return self

    def _detect_cycles(self, node_ids: set[str]) -> None:
        """DFS cycle detection within this graph's internal edges."""
        adjacency: dict[str, list[str]] = {}
        for node in self.nodes:
            neighbors: list[str] = []
            if node.next and node.next in node_ids:
                neighbors.append(node.next)
            for t in node.branches.values():
                if t in node_ids:
                    neighbors.append(t)
            adjacency[node.id] = neighbors

        visited: set[str] = set()
        in_stack: set[str] = set()

        def dfs(nid: str) -> bool:
            if nid in in_stack:
                return True
            if nid in visited:
                return False
            visited.add(nid)
            in_stack.add(nid)
            for neighbor in adjacency.get(nid, []):
                if dfs(neighbor):
                    return True
            in_stack.discard(nid)
            return False

        for nid in adjacency:
            if nid not in visited and dfs(nid):
                raise ValueError(
                    f"Circular node reference detected in script '{self.id}'."
                )

    # ------------------------------------------------------------------
    # Serialization
    # ------------------------------------------------------------------

    def to_json(self, *, indent: int = 2) -> str:
        """Serialize to JSON string for writing to a script file."""
        return self.model_dump_json(indent=indent)

    @classmethod
    def from_json(cls, text: str) -> "EventGraph":
        """Deserialize from a JSON string."""
        return cls.model_validate_json(text)

    @classmethod
    def from_file(cls, path: Path) -> "EventGraph":
        """Load an EventGraph from a .json script file."""
        return cls.from_json(path.read_text(encoding="utf-8"))

    def save(self, scripts_dir: Path) -> Path:
        """
        Write this graph to ``<scripts_dir>/<id>.json``.

        Returns the path of the written file.
        """
        scripts_dir.mkdir(parents=True, exist_ok=True)
        out = scripts_dir / f"{self.id}.json"
        out.write_text(self.to_json(), encoding="utf-8")
        return out


# ---------------------------------------------------------------------------
# Event graph builder (fluent API)
# ---------------------------------------------------------------------------


class EventGraphBuilder:
    """
    Fluent builder for constructing EventGraph objects.

    Usage::

        graph = (
            EventGraphBuilder("shop_opened")
            .description("Opens the Taba shop when player enters the zone.")
            .on_trigger(TriggerType.MAP_ZONE_ENTER, zone="shop_zone")
            .add_dialog("greet", text_key="shop.greeting", next_node="open_shop")
            .add_action("open_shop", ActionType.OPEN_SHOP, args={"shop_id": "taba_shop"})
            .build()
        )
    """

    def __init__(self, script_id: str) -> None:
        self._id = script_id
        self._description = ""
        self._triggers: list[dict] = []
        self._nodes: list[dict] = []
        self._entry_node: Optional[str] = None

    def description(self, text: str) -> "EventGraphBuilder":
        self._description = text
        return self

    def on_trigger(
        self, trigger_type: TriggerType, **args: Any
    ) -> "EventGraphBuilder":
        self._triggers.append({"type": trigger_type.value, "args": args})
        return self

    def add_action(
        self,
        node_id: str,
        action: ActionType,
        *,
        args: Optional[dict[str, Any]] = None,
        next_node: Optional[str] = None,
        branches: Optional[dict[str, str]] = None,
    ) -> "EventGraphBuilder":
        self._nodes.append(
            {
                "id": node_id,
                "action": action.value,
                "args": args or {},
                "next": next_node,
                "branches": branches or {},
            }
        )
        return self

    def add_dialog(
        self,
        node_id: str,
        *,
        text_key: str,
        next_node: Optional[str] = None,
    ) -> "EventGraphBuilder":
        return self.add_action(
            node_id,
            ActionType.DIALOG,
            args={"text_key": text_key},
            next_node=next_node,
        )

    def add_set_variable(
        self,
        node_id: str,
        *,
        key: str,
        value: str,
        next_node: Optional[str] = None,
    ) -> "EventGraphBuilder":
        return self.add_action(
            node_id,
            ActionType.SET_VARIABLE,
            args={"key": key, "value": value},
            next_node=next_node,
        )

    def entry(self, node_id: str) -> "EventGraphBuilder":
        self._entry_node = node_id
        return self

    def build(self) -> EventGraph:
        return EventGraph(
            id=self._id,
            description=self._description,
            triggers=[EventTrigger(**t) for t in self._triggers],
            nodes=[EventNode(**n) for n in self._nodes],
            entry_node=self._entry_node,
        )

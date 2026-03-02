# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any, Optional

from pydantic import BaseModel, Field

TIME_FORMAT = "%Y-%m-%d %H:%M"


class TrainerState(BaseModel):
    """
    Persistent state for a single trainer NPC, supporting the rematch loop
    described in docs/gold_silver_blueprint.md §3.
    """

    trainer_id: str = Field(
        ...,
        description="Stable identifier matching the NPC definition.",
    )
    defeated: bool = Field(
        default=False,
        description="True after the player wins the first encounter.",
    )
    last_rematch_at: Optional[str] = Field(
        default=None,
        description=(
            f"ISO-formatted timestamp ('{TIME_FORMAT}') of the most recent "
            "rematch, or None if no rematch has occurred."
        ),
    )
    rematch_count: int = Field(
        default=0,
        ge=0,
        description="Number of rematches completed against this trainer.",
    )
    rematch_eligible: bool = Field(
        default=False,
        description=(
            "True when the trainer's rematch policy is active and the player "
            "meets the configured badge/milestone threshold."
        ),
    )


class WorldSave(BaseModel):
    factions_manager: dict[str, Any] = Field(default_factory=dict)
    menu_flags: dict[str, bool] = Field(default_factory=dict)


class SessionSave(BaseModel):
    uuid: str | None = Field(default=None)
    start_time: str | None = Field(default=None)
    duration: float | None = Field(default=None)
    total_playtime: float | None = Field(default=None)


class NPCState(BaseModel):
    instance_id: str | None = None
    is_player: bool = False
    position: list[float] | None = Field(
        default=None,
        description=(
            "Continuous world-space coordinates [x, y] in floating-point. "
            "This is the authoritative position used by physics and movement."
        ),
    )
    tile_pos: tuple[int, int] | None = Field(
        default=None,
        description=(
            "Discrete tile-space coordinates (x, y) in integers. "
            "Derived from world_position and used for grid-based logic. "
            "Kept for compatibility and debugging."
        ),
    )
    current_map: str | None = None
    facing: str | None = None
    gender: str | None = None
    birthdate: tuple[int, int] | None = None
    game_variables: dict[str, Any] = Field(default_factory=dict)
    battles: Sequence[Mapping[str, Any]] = Field(default_factory=list)
    tuxepedia: Mapping[str, Any] = Field(default_factory=dict)
    relationships: Mapping[str, Any] = Field(default_factory=dict)
    money: Mapping[str, Any] = Field(default_factory=dict)
    appearance: dict[str, Any] = Field(default_factory=dict)
    missions: Sequence[Mapping[str, Any]] = Field(default_factory=list)
    items: Sequence[Mapping[str, Any]] = Field(default_factory=list)
    monsters: Sequence[Mapping[str, Any]] = Field(default_factory=list)
    player_name: str | None = None
    player_slug: str | None = None
    player_steps: float | None = None
    monster_boxes: Mapping[str, list[Mapping[str, Any]]] = Field(
        default_factory=dict
    )
    item_boxes: Mapping[str, list[Mapping[str, Any]]] = Field(
        default_factory=dict
    )
    monster_box_metadata: Mapping[str, Any] = Field(default_factory=dict)
    item_box_metadata: Mapping[str, Any] = Field(default_factory=dict)
    teleport_faint: Mapping[str, Any] = Field(default_factory=dict)
    tracker: Mapping[str, Any] = Field(default_factory=dict)
    step_tracker: Mapping[str, Any] = Field(default_factory=dict)
    unlocked_letters: Mapping[str, Any] = Field(default_factory=dict)
    evolution_registry: Mapping[str, Any] = Field(default_factory=dict)
    routing_policy: str | None = None
    trainer_states: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Mapping of trainer_id → serialized TrainerState. "
            "Tracks defeat, rematch eligibility, and cooldown for every "
            "trainer the player has encountered."
        ),
    )
    coin_wallet: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Serialised CoinWallet state (balance, daily_earned, daily_earn_cap). "
            "In-game currency only — no real-money pathway exists."
        ),
    )
    milestone_state: dict[str, Any] = Field(
        default_factory=dict,
        description=(
            "Serialised PostgameMilestoneTracker state. "
            "Tracks which post-game milestone tiers (0-5) the player has achieved "
            "and cumulative rematch-win count."
        ),
    )


class SaveData(BaseModel):
    screenshot: str | None = Field(default=None)
    screenshot_width: int | None = Field(default=None)
    screenshot_height: int | None = Field(default=None)
    time: str | None = Field(default=None)
    version: int | None = Field(default=None)
    npc_state: NPCState | None = Field(default=None)
    world_state: WorldSave | None = Field(default=None)
    session_state: SessionSave | None = Field(default=None)
    shop_stock: dict[str, dict[str, Any]] = Field(default_factory=dict)
    multiplayer_battles: dict[str, Any] = Field(default_factory=dict)
    tournament_data: dict[str, Any] = Field(default_factory=dict)
    persistent_state: list[NPCState] = Field(default_factory=list)

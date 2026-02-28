# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
import time
from collections.abc import Mapping
from enum import Enum, auto
from itertools import count
from typing import TYPE_CHECKING, Any, TypedDict
from uuid import UUID

import pygame as pg

from tuxemon.entity.npc import NPC
from tuxemon.multiplayer_battle_manager import (
    BattleChallenge,
    BattleChallengeResult,
)
from tuxemon.network.event_dispatcher import EventDispatcher
from tuxemon.network.networking import EventData, update_client
from tuxemon.network.websocket_client import (
    ConnectionState,
    WebsocketClientWrapper,
)
from tuxemon.session import local_session
from tuxemon.states import world_state as world

if TYPE_CHECKING:
    from tuxemon.base_client import BaseClient

logger = logging.getLogger(__name__)


def _normalize_duel_response(raw_response: Any) -> str | None:
    """Normalize duel response tokens for challenge lifecycle updates."""
    if raw_response is None:
        return None
    if not isinstance(raw_response, str):
        return None

    token = raw_response.strip().lower()
    if not token:
        return None
    if token in {"accept", "accepted"}:
        return "accept"
    if token in {"decline", "declined", "reject", "rejected"}:
        return "reject"
    return token


class GameEntry(TypedDict):
    ip: str
    port: int
    name: str


class ConnState(Enum):
    DISCONNECTED = auto()
    REGISTERING = auto()
    READY = auto()


class TuxemonClient:
    """Manages multiplayer networking and synchronization for a local game client."""

    def __init__(
        self,
        game: BaseClient,
        server_port: int = 40081,
    ) -> None:
        """
        Initializes the client with networking, event handling, and multiplayer
        support.
        """
        self.game = game
        self.server_port = server_port

        self.dispatcher = EventDispatcher(self)
        self.input_translator = InputEventTranslator(self)
        self.sync_manager = PlayerSyncManager(self)
        self.discovery = MultiplayerDiscovery(self)
        self.interaction_manager = InteractionManager(self)
        self.connection_manager = ConnectionManager(self)

        self.available_games: list[tuple[str, int]] = []
        self.server_list: list[str] = []
        self.selected_game: tuple[str, int] | None = None
        self.pending_feedback: list[
            list[tuple[str, dict[str, str]]]
        ] = []

        self.populated: bool = False
        self.listening: bool = False
        self.event_counter = count(start=1)

        # Networking wrapper: handles loop, JSON, ping.
        self.client = WebsocketClientWrapper(
            port=self.server_port,
            ping_interval=2.0,
        )

    @property
    def registry(self) -> dict[str, Any]:
        return self.client.registry

    def send_event(self, event_data: dict[str, Any]) -> None:
        """Helper to send a high-level event dict over the network."""
        self.client.send_event(event_data)

    def queue_feedback(self, *message_keys: str) -> None:
        """Queue translated message keys for player-facing network feedback."""
        entries = [(key, {}) for key in message_keys if key]
        if entries:
            self.pending_feedback.append(entries)

    def queue_feedback_formatted(
        self, key: str, params: dict[str, str] | None = None
    ) -> None:
        """Queue a single feedback line with optional format parameters."""
        if key:
            self.pending_feedback.append([(key, params or {})])

    def consume_feedback(
        self,
    ) -> list[list[tuple[str, dict[str, str]]]]:
        """Return and clear pending network feedback messages."""
        feedback = self.pending_feedback
        self.pending_feedback = []
        return feedback

    def connect_to_host(self, ip_address: str, port: int) -> None:
        """
        Sets up the client to attempt connection to a specified host/port
        and kicks off connection immediately.
        """
        self.selected_game = (ip_address, port)
        self.listening = True
        self.connection_manager.connect_to_host(ip_address, port)

    def disconnect(self) -> None:
        """Closes the client connection and resets its state."""
        if not self.listening:
            return

        self.client.disconnect()
        self.connection_manager.disconnect()
        self.listening = False
        self.selected_game = None
        self.client.registry = {}
        self.server_list = []
        self.populated = False

    def update(self) -> None:
        """Synchronizes game state and handles connection updates per frame."""
        self.connection_manager.update()
        self.check_notify()

    def check_notify(self) -> None:
        """Dispatches incoming server events to appropriate handlers."""
        for event_dict in self.client.get_incoming_events():
            self.dispatcher.dispatch(event_dict)

    def update_multiplayer_list(self) -> None:
        """Refreshes the list of available multiplayer servers."""
        self.discovery.update_multiplayer_list()

    def populate_player(self, event_type: str = "PUSH_SELF") -> None:
        """Sends the local player's character data to the server."""
        self.sync_manager.populate_player(event_type)

    def update_player(
        self,
        direction: str,
        event_type: str = "CLIENT_MAP_UPDATE",
    ) -> None:
        """Updates the server with the player's current map and position."""
        self.sync_manager.update_player(direction, event_type)

    def set_key_condition(self, event: Any) -> None:
        """Translates input events into network events."""
        payload = self.input_translator.translate(event)
        if payload is not None:
            self.send_event(payload)

    def update_client_map(self, cuuid: str, event_data: EventData) -> None:
        """Updates a remote client's map and character state from server data."""
        entry = self.client.registry.get(cuuid)
        if not entry:
            logger.warning(f"Unknown client {cuuid} in CLIENT_MAP_UPDATE")
            return
        sprite = entry["sprite"]
        self.client.registry[cuuid]["map_name"] = event_data.map_name
        update_client(sprite, event_data.char_dict, self.game)

    def player_interact(
        self,
        sprite: NPC,
        interaction: str,
        event_type: str = "CLIENT_INTERACTION",
        response: Any = None,
    ) -> None:
        """
        Sends an interaction event between the player and another character.
        """
        self.interaction_manager.player_interact(
            sprite, interaction, event_type, response
        )

    def route_combat(self, event: Any) -> None:
        """Handles routing of combat-related events."""
        self.interaction_manager.route_combat(event)


class InputEventTranslator:
    """
    Pure translator: converts pygame events into high-level network event dicts.
    It does NOT perform any sending; that is the caller's responsibility.
    """

    def __init__(self, client: TuxemonClient):
        self.client = client

    def translate(self, event: Any) -> dict[str, Any] | None:
        """
        Returns a dict ready to be sent over the network via
        TuxemonClient.send_event, or None if no event should be sent.
        """
        if (
            self.client.game.current_state
            != self.client.game.get_state_by_name(world.WorldState)
        ):
            logger.debug("Input ignored: not in WorldState.")
            return None

        event_type: str | None = None
        kb_key: str | None = None

        if event.type == pg.KEYDOWN:
            event_type = "CLIENT_KEYDOWN"
            kb_key = self._map_key(event.key)
        elif event.type == pg.KEYUP:
            event_type = "CLIENT_KEYUP"
            kb_key = self._map_key(event.key)

        if event.type == pg.KEYDOWN and kb_key in {
            "up",
            "down",
            "left",
            "right",
        }:
            event_type = "CLIENT_FACING"

        logger.debug(f"Translated input: type={event_type}, key={kb_key}")

        if not event_type or not kb_key:
            return None

        event_data_dict: dict[str, Any] = {
            "type": event_type,
            "event_number": next(self.client.event_counter),
        }

        if event_type == "CLIENT_FACING":
            if self.client.game.network_manager.is_connected():
                event_data_dict["char_dict"] = {"facing": kb_key}
            else:
                return None
        else:
            event_data_dict["kb_key"] = kb_key

        return EventData.from_dict(event_data_dict).to_dict()

    def _map_key(self, key: int) -> str | None:
        key_map = {
            pg.K_LSHIFT: "SHIFT",
            pg.K_RSHIFT: "SHIFT",
            pg.K_LCTRL: "CTRL",
            pg.K_RCTRL: "CTRL",
            pg.K_LALT: "ALT",
            pg.K_RALT: "ALT",
            pg.K_UP: "up",
            pg.K_DOWN: "down",
            pg.K_LEFT: "left",
            pg.K_RIGHT: "right",
        }
        return key_map.get(key)


class PlayerSyncManager:
    """
    Handles synchronization of the local player's state with the server.
    """

    def __init__(self, client: TuxemonClient):
        self.client = client
        self.game = client.game

    def _snapshot_local_player(self) -> dict[str, Any]:
        """Build a minimal, serialization-safe player snapshot."""
        try:
            player = local_session.player
        except Exception:
            return {
                "tile_pos": (0, 0),
                "name": "Unnamed Player",
                "facing": "down",
                "running": False,
            }

        raw_tile_pos = getattr(player, "tile_pos", (0, 0))
        tile_pos = (0, 0)
        if isinstance(raw_tile_pos, (list, tuple)) and len(raw_tile_pos) >= 2:
            try:
                tile_pos = (int(raw_tile_pos[0]), int(raw_tile_pos[1]))
            except (TypeError, ValueError):
                tile_pos = (0, 0)

        return {
            "tile_pos": tile_pos,
            "name": str(getattr(player, "name", "Unnamed Player")),
            "facing": getattr(player, "facing", "down"),
            "running": bool(getattr(player, "running", False)),
        }

    def _send_event(self, event_type: str, **fields: Any) -> None:
        """
        Helper for building and sending typed events with an incrementing
        event_number. Centralizes the boilerplate.
        """
        payload: dict[str, Any] = {
            "type": event_type,
            "event_number": next(self.client.event_counter),
        }
        payload.update(fields)
        event_data_obj = EventData.from_dict(payload)
        self.client.send_event(event_data_obj.to_dict())

    def populate_player(self, event_type: str = "PUSH_SELF") -> None:
        """Sends client character to the server."""
        player_data = self._snapshot_local_player()
        map_name = self.game.get_map_name()

        self._send_event(
            event_type,
            map_name=map_name,
            char_dict=player_data,
        )
        self.client.populated = True

    def update_player(
        self, direction: str, event_type: str = "CLIENT_MAP_UPDATE"
    ) -> None:
        """Sends client's current map and location to the server."""
        player_data = self._snapshot_local_player()
        map_name = self.game.get_map_name()

        self._send_event(
            event_type,
            map_name=map_name,
            direction=direction,
            char_dict={
                "tile_pos": player_data["tile_pos"],
                "facing": player_data["facing"],
                "running": player_data["running"],
            },
        )


class MultiplayerDiscovery:
    """
    Handles discovery and listing of available multiplayer game servers.
    """

    def __init__(self, client: TuxemonClient):
        self.client = client

    def update_multiplayer_list(self) -> None:
        """
        Populates the list of available games with hardcoded entries.
        Replace with real API call when matchmaking backend is ready.
        """
        try:
            games: list[GameEntry] = [
                {
                    "ip": "127.0.0.1",
                    "port": 40081,
                    "name": "Local Test Server",
                },
                {
                    "ip": "192.168.1.50",
                    "port": 40081,
                    "name": "LAN Party Server",
                },
            ]
            self.client.available_games = [
                (str(entry["ip"]), int(entry["port"])) for entry in games
            ]
            self.client.server_list = [str(entry["name"]) for entry in games]
        except Exception as e:
            logger.warning(f"Failed to populate server list: {e}")
            self.client.available_games = []
            self.client.server_list = []


class InteractionManager:
    """
    Handles player-to-player interactions and combat routing.
    """

    def __init__(self, client: TuxemonClient):
        self.client = client
        self.game = client.game

    def player_interact(
        self,
        sprite: NPC,
        interaction: str,
        event_type: str = "CLIENT_INTERACTION",
        response: Any = None,
    ) -> None:
        """
        Sends client-to-client interaction request to the server.
        """
        cuuid: str | None = None
        for client_id, data in self.client.registry.items():
            if data.get("sprite") == sprite:
                cuuid = client_id
                break

        local_snapshot = self.client.sync_manager._snapshot_local_player()

        payload = {
            "type": event_type,
            "event_number": next(self.client.event_counter),
            "interaction": interaction,
            "target": cuuid,
            "response": response,
            "char_dict": local_snapshot,
        }

        event_data = EventData.from_dict(payload)
        self.client.send_event(event_data.to_dict())

        # Keep local challenge state synchronized with outbound DUEL actions.
        if interaction.upper() == "DUEL":
            self.route_combat(event_data)

    def _resolve_remote_player_id(self, cuuid: str | None) -> UUID | None:
        if not cuuid:
            return None
        entry = self.client.registry.get(cuuid)
        if not isinstance(entry, dict):
            return None
        sprite = entry.get("sprite")
        player_id = getattr(sprite, "instance_id", None)
        if isinstance(player_id, UUID):
            return player_id
        return None

    def _resolve_duel_participants(
        self, event: EventData
    ) -> tuple[UUID, UUID] | None:
        """Resolve duel participants as (challenger, challenged)."""
        try:
            local_player_id = getattr(local_session.player, "instance_id", None)
        except Exception:
            local_player_id = None
        if not isinstance(local_player_id, UUID):
            logger.warning("Cannot route duel: local player id missing.")
            return None

        response = _normalize_duel_response(event.response)
        incoming = event.cuuid is not None
        remote_cuuid = event.cuuid if incoming else event.target
        remote_player_id = self._resolve_remote_player_id(remote_cuuid)
        if remote_player_id is None:
            logger.warning("Cannot route duel: remote player id missing.")
            return None

        if response is None:
            if incoming:
                return (remote_player_id, local_player_id)
            return (local_player_id, remote_player_id)

        if incoming:
            return (local_player_id, remote_player_id)
        return (remote_player_id, local_player_id)

    def _find_pending_duel_challenge(
        self,
        challenger_player_id: UUID,
        challenged_player_id: UUID,
    ) -> BattleChallenge | None:
        manager = self.game.multiplayer_battle_manager
        participants = {challenger_player_id, challenged_player_id}
        exact_match = next(
            (
                challenge
                for challenge in manager.pending_challenges
                if challenge.challenger_player_id == challenger_player_id
                and challenge.challenged_player_id == challenged_player_id
            ),
            None,
        )
        if exact_match is not None:
            return exact_match
        return next(
            (
                challenge
                for challenge in manager.pending_challenges
                if {
                    challenge.challenger_player_id,
                    challenge.challenged_player_id,
                }
                == participants
            ),
            None,
        )

    def route_combat(self, event: Any) -> None:
        """Route multiplayer combat/challenge updates into battle manager state."""
        manager = self.game.multiplayer_battle_manager

        if isinstance(event, Mapping):
            action = str(event.get("action", "")).lower()
            if action == "submit_turn":
                session_id = event.get("session_id")
                player_id = event.get("player_id")
                if not isinstance(session_id, str) or not isinstance(
                    player_id, str
                ):
                    logger.warning(
                        "Invalid submit_turn payload missing ids: %r", event
                    )
                    return
                try:
                    result = manager.submit_turn_action(
                        UUID(session_id),
                        UUID(player_id),
                        turn=int(event.get("turn", 0)),
                        action=dict(event.get("turn_action", {})),
                    )
                except (TypeError, ValueError):
                    logger.warning("Invalid submit_turn payload: %r", event)
                    return
                feedback = manager.get_turn_submission_feedback(result)
                manager.event_bus.publish(
                    "multiplayer_combat_feedback", feedback
                )
                self.client.queue_feedback_formatted(
                    feedback.message, feedback.format_params
                )
                return

        if not isinstance(event, EventData):
            logger.debug("Ignoring unsupported combat event payload: %r", event)
            return
        if (event.interaction or "").upper() != "DUEL":
            return

        participants = self._resolve_duel_participants(event)
        if participants is None:
            return
        challenger_player_id, challenged_player_id = participants
        response = _normalize_duel_response(event.response)

        if response is None:
            result = manager.propose_challenge(
                challenger_player_id, challenged_player_id
            )
            feedback = manager.get_challenge_action_feedback(
                result, action="propose"
            )
        else:
            challenge = self._find_pending_duel_challenge(
                challenger_player_id, challenged_player_id
            )
            if challenge is None:
                result = BattleChallengeResult.NOT_FOUND
            elif response == "accept":
                result = manager.accept_challenge(
                    challenge.challenge_id,
                    accepting_player_id=challenge.challenged_player_id,
                )
            elif response == "reject":
                result = manager.reject_challenge(
                    challenge.challenge_id,
                    rejecting_player_id=challenge.challenged_player_id,
                )
            else:
                logger.warning("Unknown duel response token: %r", event.response)
                return

            action = "accept" if response == "accept" else "reject"
            feedback = manager.get_challenge_action_feedback(result, action=action)

        manager.event_bus.publish("multiplayer_combat_feedback", feedback)
        self.client.queue_feedback_formatted(
            feedback.message, feedback.format_params
        )


class ConnectionManager:
    """
    Minimal connection manager: delegates lifecycle to WebsocketClientWrapper,
    and only coordinates registration and "ready" state for gameplay.
    """

    def __init__(self, client: TuxemonClient):
        self.client = client
        self.state = ConnState.DISCONNECTED
        self._registration_deadline: float | None = None
        self._register_timeout_seconds = 5.0

    def update(self) -> None:
        """
        Checks registration state and transitions into READY when the
        underlying WebsocketClientWrapper reports registration.
        """
        if self.state is ConnState.DISCONNECTED:
            return

        if self.state is ConnState.REGISTERING:
            if self.client.client.registered:
                if not self.client.populated:
                    self.client.sync_manager.populate_player()
                self.state = ConnState.READY
                self._registration_deadline = None
                return
            if self._registration_timed_out():
                logger.info(
                    "Connection attempt failed before player registration."
                )
                self._handle_connection_loss("multiplayer_connect_failed")
            return

        if (
            self.state is ConnState.READY
            and self.client.client.state is ConnectionState.DISCONNECTED
        ):
            logger.info("Connection dropped after registration.")
            self._handle_connection_loss("multiplayer_connection_lost")

    def _registration_timed_out(self) -> bool:
        if self._registration_deadline is None:
            return False
        if self.client.client.state is not ConnectionState.DISCONNECTED:
            return False
        if self.client.client.registered:
            return False
        return time.monotonic() >= self._registration_deadline

    def _handle_connection_loss(self, message_key: str) -> None:
        self.client.client.disconnect()
        self.client.client.registry = {}
        self.client.populated = False
        self.client.listening = False
        self.client.queue_feedback(message_key, "multiplayer_retry_hint")
        self.disconnect()

    def connect_to_host(self, ip: str, port: int) -> None:
        """
        Attempts to connect to the selected multiplayer server immediately.
        """
        if self.client.game.network_manager.is_host():
            logger.info("Skipping client connection: running as host.")
            return

        logger.info(f"Connecting to WS server: {ip}:{port}")
        self._registration_deadline = (
            time.monotonic() + self._register_timeout_seconds
        )
        self.client.client.start_connection(ip, port)
        self.state = ConnState.REGISTERING

    def disconnect(self) -> None:
        self.state = ConnState.DISCONNECTED
        self._registration_deadline = None

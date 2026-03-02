# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from collections.abc import Callable
from typing import TYPE_CHECKING

from tuxemon.map.tuxemon import AbstractMap

if TYPE_CHECKING:
    from tuxemon.boundary import BoundaryChecker
    from tuxemon.event.eventengine import EventEngine
    from tuxemon.map.loader import MapLoader
    from tuxemon.map.manager import MapManager
    from tuxemon.map.tuxemon import AbstractMap
    from tuxemon.npc_manager import NPCManager

logger = logging.getLogger(__name__)

#: Type alias for post-change listener callbacks.
#: Receives the new map slug (empty string for NullMap / yaml-loaded maps).
MapChangeListener = Callable[[str], None]


class MapTransition:
    """Handles transitioning between maps, updating game state accordingly."""

    def __init__(
        self,
        map_loader: MapLoader,
        npc_manager: NPCManager,
        map_manager: MapManager,
        boundary: BoundaryChecker,
        event_engine: EventEngine,
    ) -> None:
        self.map_loader = map_loader
        self.map_manager = map_manager
        self.npc_manager = npc_manager
        self.boundary = boundary
        self.event_engine = event_engine
        self._post_change_listeners: list[MapChangeListener] = []

    def register_post_change_listener(self, listener: MapChangeListener) -> None:
        """
        Register a callback that fires after every successful map change.

        The callback receives the new map slug (the ``map_name`` argument
        that was passed to ``change_map``).  Subscribers use this to fire
        Hook 4.3 (``on_map_zone_enter``) or update any other per-zone state.

        Parameters:
            listener: Callable accepting a single ``str`` (map slug).
        """
        self._post_change_listeners.append(listener)

    def change_map(
        self, map_name: str | None = None, yaml_path: str | None = None
    ) -> None:
        """Loads the new map or a NullMap and updates relevant game components."""
        current = self.map_manager.current_map
        self._clear_npcs()

        if map_name:
            if current is None or map_name != current.filename:
                map_data = self.map_loader.load_map_data(map_name)
            else:
                map_data = current
        else:
            map_data = self.map_loader.load_null_map(yaml_path)

        self._reset_events(map_data)
        self._update_map_state(map_data)
        self._update_boundaries()

        zone_slug = map_name or ""
        for listener in self._post_change_listeners:
            try:
                listener(zone_slug)
            except Exception:
                logger.exception(
                    "post-change listener %s raised an exception", listener
                )

    def validate_coordinates(self, x: int, y: int) -> None:
        if not self.boundary.is_within_boundaries((x, y)):
            raise ValueError(
                f"Coordinates ({x}, {y}) are out of map boundaries."
            )

    def _reset_events(self, map_data: AbstractMap) -> None:
        """Resets and updates event engine for the new map."""
        self.event_engine.reset()
        self.event_engine.set_current_map(map_data)

    def _update_map_state(self, map_data: AbstractMap) -> None:
        """Updates the map manager with new map data."""
        self.map_manager.load_map(map_data)

    def _clear_npcs(self) -> None:
        """Clears NPCs to ensure a clean transition."""
        self.npc_manager.clear_npcs()

    def _update_boundaries(self) -> None:
        """Updates the game boundaries to fit the new map."""
        map_size = self.map_manager.map_size
        self.boundary.set_rectangular_boundary(
            "map", 0, map_size[0], 0, map_size[1]
        )

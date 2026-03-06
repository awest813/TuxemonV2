# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
import time
from collections.abc import Callable
from typing import TYPE_CHECKING

import pygame

from tuxemon.base_client import BaseClient, ClientState
from tuxemon.config import TuxemonConfig
from tuxemon.map.tuxemon import NullMap
from tuxemon.map.view import DebugRenderer, MapRenderer, NullRenderer
from tuxemon.performance_profiler import RuntimeProfiler
from tuxemon.state.draw import EventDebugDrawer, Renderer, StateDrawer

if TYPE_CHECKING:
    from tuxemon.prepare import DisplayContext

logger = logging.getLogger(__name__)


class LocalPygameClient(BaseClient):
    """
    Client class for the entire project.

    Contains the game loop and the event_loop, which passes events to
    States as needed.

    Parameters:
        config: The configuration for the game.
        screen: The surface where the game is rendered.
    """

    @classmethod
    def create(
        cls, config: TuxemonConfig, context: DisplayContext
    ) -> LocalPygameClient:
        """
        Initialize the LocalPygameClient with the given configuration and screen.
        """
        try:
            client = LocalPygameClient(config, context)
            logger.info("Client initialized successfully.")
        except (TypeError, ValueError) as e:
            logger.error(f"Failed to initialize client: {e}")
            raise
        except Exception as e:
            logger.critical(
                f"Unexpected error during client initialization: {e}"
            )
            raise
        return client

    def __init__(self, config: TuxemonConfig, context: DisplayContext):
        super().__init__(config, context)

        # movie creation
        self.frame_number = 0
        self.save_to_disk = False

        # Initialize drawers
        self.state_drawer = StateDrawer(
            self.screen, self.state_manager, config
        )
        self.event_debug_drawer = EventDebugDrawer(self.context)
        self.renderer = Renderer(
            self.screen,
            self.state_drawer,
            self.config,
            self.event_debug_drawer,
        )
        self.debug_renderer = DebugRenderer(
            self.map_manager, self.npc_manager, self.context
        )
        self.profiler = RuntimeProfiler()
        self._f3_pressed = False

        map_renderer = MapRenderer(
            self.camera_manager,
            self.npc_manager,
            self.debug_renderer,
            self.context,
        )
        self.set_renderer(map_renderer)

    def reset_renderer(self) -> None:
        current_map = self.map_manager.current_map
        self._f3_pressed = False
        if isinstance(current_map, NullMap):
            self.set_renderer(NullRenderer())
            logger.debug("Renderer reset to NullRenderer.")
        else:
            self.debug_renderer = DebugRenderer(
                self.map_manager, self.npc_manager, self.context
            )
            map_renderer = MapRenderer(
                self.camera_manager,
                self.npc_manager,
                self.debug_renderer,
                self.context,
            )
            self.set_renderer(map_renderer)
            logger.debug("Renderer reset to MapRenderer.")

    def main(self) -> None:
        """
        Initiates the main game loop.

        Since we are using Asteria networking to handle network events,
        we pass this session.Client instance to networking which in turn
        executes the "main_loop" method every frame.
        This leaves the networking component responsible for the main loop.
        """
        update = self.update
        draw = self.draw
        screen = self.screen
        flip = pygame.display.update
        clock = time.time
        frame_length = 1.0 / self.config.fps
        time_since_draw = 0.0
        last_update = clock()

        while self.state != ClientState.DONE:
            if self.state == ClientState.RUNNING:
                self.profiler.start_frame()
                clock_tick = clock() - last_update
                last_update = clock()
                time_since_draw += clock_tick

                with self.profiler.section("update"):
                    update(clock_tick)

                f3_down = pygame.key.get_pressed()[pygame.K_F3]
                if f3_down and not self._f3_pressed:
                    self.profiler.toggle_overlay()
                self._f3_pressed = f3_down

                if self.map_loader.last_load_time:
                    self.profiler.record("asset_load", self.map_loader.last_load_time)
                    self.map_loader.last_load_time = 0.0

                if time_since_draw >= frame_length:
                    time_since_draw -= frame_length
                    with self.profiler.section("render"):
                        draw()
                    with self.profiler.section("ui_render"):
                        self.input_manager.draw_inputs(screen)
                    self.profiler.draw_overlay(screen)
                    flip()

                if self.config.show_fps:
                    self.renderer.update(clock_tick)

                self.profiler.end_frame()
                time.sleep(0.01)
            elif self.state == ClientState.EXITING:
                self.perform_cleanup()
                self.state = ClientState.DONE

    def update(self, time_delta: float) -> None:
        """
        Main loop for entire game.

        Parameters:
            time_delta: Elapsed time since last frame.
        """
        with self.profiler.section("ui_update"):
            self.update_states(time_delta)

        current_state = self.state_manager.current_state
        if current_state:
            self.profiler.set_active_ui_state(current_state.name)

    def queue_command(self, command: Callable[[], None]) -> None:
        self.command_queue.put(command)
        logger.debug("Queued command for execution in main thread.")

    def draw(self) -> None:
        """Centralized draw logic."""
        draw_calls = self.renderer.draw()
        self.profiler.set_draw_calls(draw_calls)

        if self.config.collision_map:
            self.renderer.draw_debug(self.event_engine.partial_events)

        if self.save_to_disk:
            self.renderer.save_frame(self.frame_number)

        self.frame_number += 1

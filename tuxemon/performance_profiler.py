# SPDX-License-Identifier: GPL-3.0
from __future__ import annotations

import statistics
import time
import tracemalloc
from collections import deque
from contextlib import contextmanager
from dataclasses import dataclass, field
from typing import Iterator

import pygame
from pygame.font import Font, get_default_font
from pygame.surface import Surface


@dataclass
class RollingMetric:
    values: deque[float] = field(default_factory=lambda: deque(maxlen=300))

    def add(self, value: float) -> None:
        self.values.append(value)

    def average_ms(self) -> float:
        if not self.values:
            return 0.0
        return sum(self.values) / len(self.values) * 1000.0

    def p95_ms(self) -> float:
        if not self.values:
            return 0.0
        if len(self.values) == 1:
            return self.values[0] * 1000.0
        return statistics.quantiles(self.values, n=100)[94] * 1000.0


class RuntimeProfiler:
    """Collects low-overhead frame timing data and draws an optional overlay."""

    def __init__(self) -> None:
        self.overlay_enabled = False
        self.metrics: dict[str, RollingMetric] = {
            "frame": RollingMetric(),
            "update": RollingMetric(),
            "render": RollingMetric(),
            "ui_update": RollingMetric(),
            "ui_render": RollingMetric(),
            "input_latency": RollingMetric(),
            "asset_load": RollingMetric(),
        }
        self.draw_calls = 0
        self.active_ui_state = "unknown"
        self._frame_start = time.perf_counter()
        if not tracemalloc.is_tracing():
            tracemalloc.start()

    @contextmanager
    def section(self, name: str) -> Iterator[None]:
        start = time.perf_counter()
        try:
            yield
        finally:
            self.metrics[name].add(time.perf_counter() - start)

    def start_frame(self) -> None:
        self._frame_start = time.perf_counter()

    def end_frame(self) -> None:
        self.metrics["frame"].add(time.perf_counter() - self._frame_start)

    def record(self, name: str, seconds: float) -> None:
        if name in self.metrics:
            self.metrics[name].add(seconds)

    def set_draw_calls(self, draw_calls: int) -> None:
        self.draw_calls = draw_calls

    def set_active_ui_state(self, state_name: str) -> None:
        self.active_ui_state = state_name

    def toggle_overlay(self) -> None:
        self.overlay_enabled = not self.overlay_enabled

    def draw_overlay(self, surface: Surface) -> None:
        if not self.overlay_enabled:
            return

        current_mem, _peak_mem = tracemalloc.get_traced_memory()
        fps = 1000.0 / max(self.metrics["frame"].average_ms(), 0.0001)
        lines = [
            f"FPS: {fps:.1f}",
            f"Frame: {self.metrics['frame'].average_ms():.2f} ms (p95 {self.metrics['frame'].p95_ms():.2f})",
            f"Update: {self.metrics['update'].average_ms():.2f} ms",
            f"Render: {self.metrics['render'].average_ms():.2f} ms",
            f"UI Update: {self.metrics['ui_update'].average_ms():.2f} ms",
            f"UI Render: {self.metrics['ui_render'].average_ms():.2f} ms",
            f"Input latency: {self.metrics['input_latency'].average_ms():.2f} ms",
            f"Asset load: {self.metrics['asset_load'].average_ms():.2f} ms",
            f"Draw calls (proxy): {self.draw_calls}",
            f"Memory: {current_mem / (1024 * 1024):.1f} MB",
            f"Active UI state: {self.active_ui_state}",
        ]

        width = 520
        height = 18 * len(lines) + 10
        panel = pygame.Surface((width, height), pygame.SRCALPHA)
        panel.fill((0, 0, 0, 180))
        surface.blit(panel, (10, 10))

        font = Font(get_default_font(), 14)
        for idx, line in enumerate(lines):
            text = font.render(line, True, (255, 255, 255))
            surface.blit(text, (18, 16 + idx * 18))

# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Combat HUD overlay components: turn counter and weather/terrain indicator.

These lightweight classes carry pure-state logic; the actual pygame rendering
is delegated to the combat state's draw layer so they remain unit-testable
without a display context.
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


class TurnCounter:
    """
    Tracks the current turn number and total turns elapsed in a battle.

    Usage::

        counter = TurnCounter()
        counter.next_turn()        # advance to turn 2
        print(counter.current)     # 2
        print(counter.total)       # 1  (only one full turn has elapsed)

    A "turn" begins when a new decision round starts and ends when all
    actions in that round have been resolved.  :meth:`next_turn` should
    be called at the start of each new decision round.
    """

    def __init__(self) -> None:
        self._current: int = 1
        self._total: int = 0

    @property
    def current(self) -> int:
        """The 1-based index of the ongoing turn."""
        return self._current

    @property
    def total(self) -> int:
        """Number of fully completed turns since battle start."""
        return self._total

    def next_turn(self) -> None:
        """Advance to the next turn and increment the completed-turn count."""
        self._total = self._current
        self._current += 1
        logger.debug("TurnCounter: turn %d began", self._current)

    def reset(self) -> None:
        """Reset the counter to its initial state (turn 1, 0 completed)."""
        self._current = 1
        self._total = 0
        logger.debug("TurnCounter: reset")

    def __repr__(self) -> str:
        return f"TurnCounter(current={self._current}, total={self._total})"


@dataclass
class WeatherTerrainState:
    """
    Snapshot of the active weather and terrain for a battle.

    Both fields are token strings (e.g. ``"rain"``, ``"electric_terrain"``)
    or ``None`` when no effect is active.  These tokens are resolved to
    display names and icons via the localisation system in the UI layer.

    Attributes:
        weather:  Active weather token, or ``None``.
        terrain:  Active terrain token, or ``None``.
        turns_remaining: Turns left for the weather/terrain effect,
            or ``None`` when the effect is permanent / not tracked.
    """

    weather: str | None = None
    terrain: str | None = None
    turns_remaining: int | None = None

    @property
    def has_effect(self) -> bool:
        """``True`` if any weather or terrain effect is currently active."""
        return self.weather is not None or self.terrain is not None

    @property
    def display_token(self) -> str | None:
        """
        Primary display token: weather takes priority over terrain.
        Returns ``None`` when no effect is active.
        """
        return self.weather or self.terrain


class WeatherTerrainIndicator:
    """
    Tracks and surfaces weather / terrain state for the combat HUD overlay.

    The indicator stores the *current* :class:`WeatherTerrainState` and
    provides change detection so the HUD only re-renders when something
    actually changes.

    Usage::

        indicator = WeatherTerrainIndicator()
        indicator.set_weather("rain", turns_remaining=5)
        indicator.set_terrain("misty_terrain")

        state = indicator.current
        print(state.weather)           # "rain"
        print(state.terrain)           # "misty_terrain"
        print(state.turns_remaining)   # 5

        indicator.clear_weather()
        print(indicator.changed)       # True (state changed since last ack)
        indicator.acknowledge()        # clear changed flag

    """

    def __init__(self) -> None:
        self._state: WeatherTerrainState = WeatherTerrainState()
        self._changed: bool = False

    @property
    def current(self) -> WeatherTerrainState:
        """The current weather/terrain snapshot (read-only view)."""
        return WeatherTerrainState(
            weather=self._state.weather,
            terrain=self._state.terrain,
            turns_remaining=self._state.turns_remaining,
        )

    @property
    def changed(self) -> bool:
        """
        ``True`` if the state has changed since the last :meth:`acknowledge`.
        The HUD can poll this to decide whether to redraw the indicator.
        """
        return self._changed

    def set_weather(
        self,
        weather: str | None,
        turns_remaining: int | None = None,
    ) -> None:
        """
        Update the active weather effect.

        Parameters:
            weather: Weather token string, or ``None`` to clear.
            turns_remaining: Optional remaining-turns count for this effect.
        """
        if self._state.weather != weather or self._state.turns_remaining != turns_remaining:
            self._state.weather = weather
            self._state.turns_remaining = turns_remaining
            self._changed = True
            logger.debug(
                "WeatherTerrainIndicator: weather=%r turns_remaining=%r",
                weather,
                turns_remaining,
            )

    def set_terrain(self, terrain: str | None) -> None:
        """
        Update the active terrain effect.

        Parameters:
            terrain: Terrain token string, or ``None`` to clear.
        """
        if self._state.terrain != terrain:
            self._state.terrain = terrain
            self._changed = True
            logger.debug("WeatherTerrainIndicator: terrain=%r", terrain)

    def clear_weather(self) -> None:
        """Remove the current weather effect."""
        self.set_weather(None, None)

    def clear_terrain(self) -> None:
        """Remove the current terrain effect."""
        self.set_terrain(None)

    def clear_all(self) -> None:
        """Remove all weather and terrain effects."""
        self.clear_weather()
        self.clear_terrain()

    def tick_turn(self) -> None:
        """
        Decrement turns_remaining by 1.  If it reaches 0, the weather is cleared.
        No-op when turns_remaining is ``None`` (permanent effect).
        """
        if self._state.turns_remaining is None:
            return
        self._state.turns_remaining -= 1
        self._changed = True
        if self._state.turns_remaining <= 0:
            logger.debug(
                "WeatherTerrainIndicator: weather %r expired", self._state.weather
            )
            self._state.weather = None
            self._state.turns_remaining = None

    def acknowledge(self) -> None:
        """Clear the changed flag after the HUD has processed the update."""
        self._changed = False

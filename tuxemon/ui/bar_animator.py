# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
"""
Frame-rate-independent bar animators for combat HP and EXP bars — P0.

This module provides two animators:

* :class:`HpBarAnimator` — smoothly drains the HP bar and shows a
  *ghost bar* (a fading residual from the pre-damage HP level) while the
  bar catches up.  The ghost colour provides instant damage feedback even
  before the drain animation reaches the new value.

* :class:`ExpBarAnimator` — fills the EXP bar toward the target progress
  and, on level-up, automatically fills to full then resets to zero before
  filling to the new in-level progress.

Both classes are pure Python and update via ``update(dt: float)``.
They do **not** depend on the pygame animation scheduler, making them
straightforwardly unit-testable.

Integration with :class:`~tuxemon.ui.combat_bars.CombatBars`
-------------------------------------------------------------
``CombatBars`` holds one animator per monster.  Each call to
``draw_bars`` should call ``animator.update(dt)`` first (the combat
state must pass ``dt`` through), then use ``animator.display_value``
and ``animator.ghost_value`` to draw the bar layers.

The actual pygame drawing remains in :class:`~tuxemon.menu.interface.Bar`
(foreground fill, background, border, gloss).  The animators are pure
state machines that produce normalised ``[0, 1]`` values for the draw
layer to consume.
"""
from __future__ import annotations

import math

# ---------------------------------------------------------------------------
# Speed / timing constants  (all in normalised-value / second units)
# ---------------------------------------------------------------------------

# HP bar drains at this many HP-ratio units per second (0.3 = 30 % per sec).
_HP_DRAIN_SPEED: float = 0.40
# Ghost bar decays toward the animated HP at this many units per second.
_GHOST_DECAY_SPEED: float = 0.15
# EXP bar fills at this many progress units per second.
_EXP_FILL_SPEED: float = 0.50
# Delay (seconds) before the EXP bar begins filling after a request.
_EXP_FILL_DELAY: float = 0.20


def _lerp(a: float, b: float, t: float) -> float:
    """Linear interpolation between *a* and *b* by factor *t* ∈ [0, 1]."""
    return a + (b - a) * t


def _clamp(value: float, lo: float = 0.0, hi: float = 1.0) -> float:
    return max(lo, min(hi, value))


class HpBarAnimator:
    """
    Smooth HP-bar drain with a ghost-bar overlay.

    The *ghost bar* renders the "old" HP level in a distinct colour (e.g.
    yellow) while the active (green/amber/red) bar gradually drains toward
    the new target.  Once the active bar catches up, the ghost fades out.

    This gives the player instant visual feedback — the ghost appears
    *immediately* on damage — while the drain provides a satisfying sense
    of "weight" to the damage number.

    Attributes:
        display_value: Normalised HP currently rendered by the active bar
            (``0.0`` = empty, ``1.0`` = full).
        ghost_value:   Normalised HP rendered by the ghost overlay.  Equals
            ``display_value`` when no animation is active.

    Parameters:
        initial_value: Starting HP ratio (defaults to 1.0 for a fresh bar).
        drain_speed:   HP-ratio units per second for the active bar drain.
        ghost_speed:   HP-ratio units per second for the ghost decay.
    """

    def __init__(
        self,
        initial_value: float = 1.0,
        drain_speed: float = _HP_DRAIN_SPEED,
        ghost_speed: float = _GHOST_DECAY_SPEED,
    ) -> None:
        value = _clamp(initial_value)
        self._display: float = value
        self._ghost: float = value
        self._target: float = value
        self._drain_speed = drain_speed
        self._ghost_speed = ghost_speed

    # ------------------------------------------------------------------
    # Properties (read-only for consumers)
    # ------------------------------------------------------------------

    @property
    def display_value(self) -> float:
        """Active bar fill level in [0, 1]."""
        return self._display

    @property
    def ghost_value(self) -> float:
        """Ghost bar fill level in [0, 1].  Equals ``display_value`` when idle."""
        return self._ghost

    @property
    def target_value(self) -> float:
        """The HP ratio the bar is animating toward."""
        return self._target

    @property
    def is_animating(self) -> bool:
        """``True`` while either the active bar or ghost is still moving."""
        tol = 1e-4
        return (
            abs(self._display - self._target) > tol
            or abs(self._ghost - self._display) > tol
        )

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def set_target(self, new_hp_ratio: float) -> None:
        """
        Request the bar to animate toward *new_hp_ratio*.

        Call this whenever the monster's HP changes.  The ghost is snapped
        to the *current* display value immediately (giving instant feedback),
        while the active bar and ghost decay over subsequent frames.

        Parameters:
            new_hp_ratio: Desired HP ratio in [0, 1].
        """
        new_value = _clamp(new_hp_ratio)
        if new_value == self._target:
            return

        # Snap the ghost to where the bar currently is so the "old HP"
        # overlay appears immediately.
        self._ghost = max(self._ghost, self._display)
        self._target = new_value

    def snap(self, value: float) -> None:
        """
        Instantly set all bar layers to *value* (no animation).

        Use this when initialising or after a monster switch.
        """
        v = _clamp(value)
        self._display = v
        self._ghost = v
        self._target = v

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        """
        Advance the animation by *dt* seconds.

        Parameters:
            dt: Elapsed time since the last update in seconds.
        """
        if dt <= 0:
            return

        # Drain the active bar toward the target.
        if self._display != self._target:
            step = self._drain_speed * dt
            if self._display > self._target:
                self._display = max(self._target, self._display - step)
            else:
                # HP restored — fill immediately (no ghost for healing).
                self._display = min(self._target, self._display + step * 2)

        # Decay the ghost toward the current display value.
        if self._ghost > self._display:
            ghost_step = self._ghost_speed * dt
            self._ghost = max(self._display, self._ghost - ghost_step)

        # Clamp for floating-point drift.
        self._display = _clamp(self._display)
        self._ghost = _clamp(self._ghost)


class ExpBarAnimator:
    """
    Smooth EXP-bar fill with automatic level-up wrap-around.

    On a normal XP gain, the bar fills toward the target progress at
    ``fill_speed`` units per second.

    On a **level-up**, the animation proceeds in two phases:
    1. Fill to 1.0 (full bar).
    2. Reset to 0.0, then fill to the new in-level progress.

    A short ``delay`` (default 0.2 s) is inserted before the bar begins
    moving, giving the combat text time to settle.

    Attributes:
        display_value: Normalised EXP progress currently rendered (0–1).

    Parameters:
        initial_value: Starting progress ratio (defaults to 0.0).
        fill_speed:    EXP progress units per second.
        delay:         Seconds to wait before beginning the fill.
    """

    def __init__(
        self,
        initial_value: float = 0.0,
        fill_speed: float = _EXP_FILL_SPEED,
        delay: float = _EXP_FILL_DELAY,
    ) -> None:
        value = _clamp(initial_value)
        self._display: float = value
        self._target: float = value
        self._fill_speed = fill_speed
        self._default_delay = delay

        self._filling_to_max: bool = False
        self._pending_target: float | None = None
        self._delay_remaining: float = 0.0

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def display_value(self) -> float:
        """EXP fill level in [0, 1]."""
        return self._display

    @property
    def target_value(self) -> float:
        """Final target EXP progress after any level-up wrap."""
        if self._pending_target is not None:
            return self._pending_target
        return self._target

    @property
    def is_animating(self) -> bool:
        """``True`` while any animation is still in progress."""
        tol = 1e-4
        if self._delay_remaining > tol:
            return True
        if self._filling_to_max:
            return True
        if self._pending_target is not None:
            return True
        return abs(self._display - self._target) > tol

    # ------------------------------------------------------------------
    # Mutators
    # ------------------------------------------------------------------

    def set_target(self, new_progress: float, level_up: bool = False) -> None:
        """
        Request the bar to animate toward *new_progress*.

        Parameters:
            new_progress: Target EXP progress in [0, 1] within the new level.
            level_up:     If ``True``, fill to 1.0 first then reset to 0 and
                          fill to *new_progress*.
        """
        new_value = _clamp(new_progress)
        self._delay_remaining = self._default_delay

        if level_up:
            # Phase 1: fill to max.  Phase 2: reset and fill to new_progress.
            self._target = 1.0
            self._filling_to_max = True
            self._pending_target = new_value
        else:
            self._target = new_value
            self._filling_to_max = False
            self._pending_target = None

    def snap(self, value: float) -> None:
        """Instantly set the bar to *value* with no animation."""
        v = _clamp(value)
        self._display = v
        self._target = v
        self._filling_to_max = False
        self._pending_target = None
        self._delay_remaining = 0.0

    # ------------------------------------------------------------------
    # Update
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        """
        Advance the animation by *dt* seconds.

        Parameters:
            dt: Elapsed time since the last update in seconds.
        """
        if dt <= 0:
            return

        # Honour initial delay.
        if self._delay_remaining > 0:
            self._delay_remaining -= dt
            if self._delay_remaining > 0:
                return
            dt = -self._delay_remaining  # carry over excess time
            self._delay_remaining = 0.0

        step = self._fill_speed * dt

        # Phase 1 of level-up: fill to 1.0.
        if self._filling_to_max:
            self._display = min(1.0, self._display + step)
            if math.isclose(self._display, 1.0, abs_tol=1e-4):
                self._display = 1.0
                self._filling_to_max = False
                # Transition to phase 2: reset and begin filling.
                self._display = 0.0
                self._target = self._pending_target or 0.0
                self._pending_target = None
            return

        # Normal fill (including phase-2 of level-up after reset).
        if self._display < self._target:
            self._display = min(self._target, self._display + step)
        elif self._display > self._target:
            # Shouldn't normally happen but handle EXP loss gracefully.
            self._display = max(self._target, self._display - step)

        self._display = _clamp(self._display)

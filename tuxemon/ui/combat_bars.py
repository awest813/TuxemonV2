# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import logging
from collections.abc import MutableMapping
from typing import TYPE_CHECKING

from pygame import SRCALPHA
from pygame import draw as pg_draw
from pygame.rect import Rect
from pygame.surface import Surface

from tuxemon.menu.interface import ExpBar, HpBar
from tuxemon.sprite import Sprite
from tuxemon.ui.bar_animator import ExpBarAnimator, HpBarAnimator

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from tuxemon.db import BattleGraphicsModel
    from tuxemon.monster.monster import Monster
    from tuxemon.prepare import DisplayContext

# Ghost bar is rendered with this RGBA colour (semi-transparent amber).
_GHOST_COLOR: tuple[int, int, int, int] = (240, 200, 60, 180)


class CombatBars:
    """
    Draws combat HP and EXP bars with frame-rate-independent drain animations.

    Each monster tracked by this manager has:

    * An :class:`~tuxemon.menu.interface.HpBar` for visual rendering.
    * An :class:`~tuxemon.ui.bar_animator.HpBarAnimator` that drives the
      smooth drain and ghost-bar overlay.
    * An :class:`~tuxemon.menu.interface.ExpBar` for EXP rendering.
    * An :class:`~tuxemon.ui.bar_animator.ExpBarAnimator` that drives the
      fill animation including level-up wrap-around.

    Call :meth:`update` every frame with the elapsed ``dt`` to advance all
    animators, then call :meth:`draw_bars` to render the current frame.
    """

    def __init__(self, context: "DisplayContext") -> None:
        self.context = context
        self._hp_bars: MutableMapping[Monster, HpBar] = {}
        self._exp_bars: MutableMapping[Monster, ExpBar] = {}
        self._hp_animators: MutableMapping[Monster, HpBarAnimator] = {}
        self._exp_animators: MutableMapping[Monster, ExpBarAnimator] = {}

    # ------------------------------------------------------------------
    # Per-frame update
    # ------------------------------------------------------------------

    def update(self, dt: float) -> None:
        """
        Advance all active bar animations.

        Parameters:
            dt: Elapsed time since last frame in seconds.

        This must be called once per frame (typically from the combat state's
        ``update()`` method) before :meth:`draw_bars` is called.
        """
        for animator in self._hp_animators.values():
            animator.update(dt)
        for animator in self._exp_animators.values():
            animator.update(dt)

    def any_animating(self) -> bool:
        """
        Return ``True`` if any bar is still mid-animation.

        The combat state can poll this to know when to refresh the HUD
        after the last frame of an animation sequence.
        """
        return any(a.is_animating for a in self._hp_animators.values()) or any(
            a.is_animating for a in self._exp_animators.values()
        )

    # ------------------------------------------------------------------
    # Target updates (called when game state changes)
    # ------------------------------------------------------------------

    def set_hp_target(self, monster: "Monster") -> None:
        """
        Notify the HP animator that the monster's HP has changed.

        Call this whenever ``monster.current_hp`` is updated (e.g. after a
        move lands).  The bar will smoothly drain to the new ratio and the
        ghost overlay will appear immediately.

        Parameters:
            monster: The monster whose HP changed.
        """
        animator = self.get_hp_animator(monster)
        animator.set_target(monster.hp_ratio)

    def set_exp_target(
        self, monster: "Monster", level_up: bool = False
    ) -> None:
        """
        Notify the EXP animator that the monster's experience changed.

        Parameters:
            monster:  The monster that gained EXP.
            level_up: Pass ``True`` when a level-up occurred so the bar
                      fills to 1.0 before resetting to the new in-level
                      progress.
        """
        animator = self.get_exp_animator(monster)
        animator.set_target(monster.experience_progress_percent, level_up=level_up)

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def draw_bars(
        self,
        hud: MutableMapping["Monster", Sprite],
        graphics: "BattleGraphicsModel",
    ) -> None:
        """
        Draw all bars onto their respective HUD sprites.

        HP bars render in two layers:
        1. Ghost bar (amber, at the old HP level) drawn first.
        2. Active bar (colour-coded by health) drawn on top.

        EXP bars render a single fill layer driven by the EXP animator.

        Parameters:
            hud:      Mapping of monster → HUD sprite to draw onto.
            graphics: Battle graphics model supplying layout constants.
        """
        gh = graphics.hud

        for monster, _sprite in hud.items():
            if gh.hp_bar_player or gh.hp_bar_opponent:
                top_offset = (
                    gh.hp_player_top if _sprite.player else gh.hp_opponent_top
                )
                rect = self.create_rect_for_bar(
                    _sprite,
                    gh.hp_bar_width,
                    gh.hp_bar_height,
                    top_offset,
                    gh.bar_right_padding,
                )
                hp_bar = self.get_hp_bar(monster)
                hp_animator = self.get_hp_animator(monster)

                # Draw ghost layer before the active bar so it appears behind.
                self._draw_ghost_layer(
                    _sprite.image, hp_bar, rect, hp_animator
                )

                # Sync the bar's render value from the animator.
                hp_bar.value = hp_animator.display_value
                hp_bar.draw(_sprite.image, rect)

            if _sprite.player and gh.exp_bar_player:
                rect = self.create_rect_for_bar(
                    _sprite,
                    gh.hp_bar_width,
                    gh.exp_bar_height,
                    gh.exp_bar_top,
                    gh.bar_right_padding,
                )
                exp_bar = self.get_exp_bar(monster)
                exp_bar.value = self.get_exp_animator(monster).display_value
                exp_bar.draw(_sprite.image, rect)

    def _draw_ghost_layer(
        self,
        surface: Surface,
        hp_bar: HpBar,
        rect: Rect,
        animator: HpBarAnimator,
    ) -> None:
        """Render the ghost (old HP) overlay for an HP bar."""
        ghost = animator.ghost_value
        if ghost <= animator.display_value + 1e-4:
            return  # No visible ghost; skip drawing.

        inner = hp_bar.calc_inner_rect(rect)
        ghost_width = int(inner.width * ghost)
        if ghost_width <= 0:
            return

        ghost_surf = Surface(inner.size, SRCALPHA)
        ghost_rect = Rect(0, 0, ghost_width, inner.height)
        pg_draw.rect(ghost_surf, _GHOST_COLOR, ghost_rect, border_radius=2)
        surface.blit(ghost_surf, inner.topleft)

    # ------------------------------------------------------------------
    # Factory helpers
    # ------------------------------------------------------------------

    def create_rect_for_bar(
        self,
        hud: Sprite,
        width: int,
        height: int,
        top: int,
        right_padding: int,
    ) -> Rect:
        s = self.context.scaling.scale_int

        width = s(width)
        height = s(height)
        top = s(top)
        right_padding = s(right_padding)

        rect = Rect(0, 0, width, height)
        rect.top = top
        rect.right = hud.image.get_width() - right_padding
        return rect

    def get_hp_bar(self, monster: "Monster") -> HpBar:
        return self._hp_bars.setdefault(
            monster, HpBar(self.context, monster.hp_ratio)
        )

    def get_exp_bar(self, monster: "Monster") -> ExpBar:
        return self._exp_bars.setdefault(
            monster, ExpBar(self.context, monster.experience_progress_percent)
        )

    def get_hp_animator(self, monster: "Monster") -> HpBarAnimator:
        if monster not in self._hp_animators:
            self._hp_animators[monster] = HpBarAnimator(
                initial_value=monster.hp_ratio
            )
        return self._hp_animators[monster]

    def get_exp_animator(self, monster: "Monster") -> ExpBarAnimator:
        if monster not in self._exp_animators:
            self._exp_animators[monster] = ExpBarAnimator(
                initial_value=monster.experience_progress_percent
            )
        return self._exp_animators[monster]

    # ------------------------------------------------------------------
    # Cleanup
    # ------------------------------------------------------------------

    def remove_monster(self, monster: "Monster") -> None:
        if monster in self._hp_bars:
            logger.debug("Removing HP bar for %s", monster.name)
            self._hp_bars.pop(monster, None)
        if monster in self._hp_animators:
            self._hp_animators.pop(monster, None)
        if monster in self._exp_bars:
            logger.debug("Removing EXP bar for %s", monster.name)
            self._exp_bars.pop(monster, None)
        if monster in self._exp_animators:
            self._exp_animators.pop(monster, None)

    def clear_all(self) -> None:
        logger.debug("Clearing all combat bars.")
        self._hp_bars.clear()
        self._exp_bars.clear()
        self._hp_animators.clear()
        self._exp_animators.clear()

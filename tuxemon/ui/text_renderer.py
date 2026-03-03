# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>
from __future__ import annotations

import math
from typing import TYPE_CHECKING

from pygame import SRCALPHA
from pygame.font import Font
from pygame.surface import Surface

from tuxemon.graphics import ColorLike
from tuxemon.platform.const.graphics import FONT_SHADOW_COLOR, FONT_SIZE

if TYPE_CHECKING:
    from tuxemon.scaling import ScalingStrategy


class TextRenderer:
    def __init__(
        self,
        scaling: ScalingStrategy,
        font_color: ColorLike,
        font_shadow_color: ColorLike | None = None,
        font_filename: str | None = None,
        font: Font | None = None,
    ) -> None:
        self.scaling = scaling
        self.font_color = font_color
        if font_shadow_color is None:
            font_shadow_color = FONT_SHADOW_COLOR
        self.font_shadow_color = font_shadow_color
        self.font = font or Font(
            font_filename, self.scaling.scale_int(FONT_SIZE)
        )

    def shadow_text(
        self,
        text: str,
        bg: ColorLike | None = None,
        fg: ColorLike | None = None,
        offset: tuple[float, float] = (0.5, 0.5),
    ) -> Surface:
        """
        Render shadowed text using the current font and shadow color settings.

        Parameters:
            text: The text string to render.
            bg: Shadow color. If None, uses the default font shadow color.
            fg: Foreground font color. If None, uses the default font color.
            offset: Tuple representing the x and y shadow offset in pixels.

        Returns:
            A Surface containing the rendered text with its shadow applied.
        """
        if fg is None:
            fg = self.font_color
        if bg is None:
            bg = self.font_shadow_color
        font_color = self.font.render(text, True, fg)
        shadow_color = self.font.render(text, True, bg)
        _offset = self.scaling.scale_sequence(offset)
        size = [
            int(math.ceil(a + b))
            for a, b in zip(_offset, font_color.get_size())
        ]
        image = Surface(size, SRCALPHA)
        image.blit(shadow_color, tuple(_offset))
        image.blit(font_color, (0, 0))
        return image

    def outline_text(
        self,
        text: str,
        fg: ColorLike | None = None,
        outline_color: ColorLike | None = None,
        outline_width: int = 1,
    ) -> Surface:
        """
        Render text with a solid outline (stroke) instead of a drop shadow.

        The outline is produced by rendering the text in the outline color at
        each of the 8 surrounding pixel positions and then compositing the
        foreground color on top.

        Parameters:
            text: The text string to render.
            fg: Foreground font color. If None, uses the default font color.
            outline_color: Color of the outline stroke. If None, uses the
                default font shadow color.
            outline_width: Thickness of the outline in (unscaled) pixels.
                Defaults to 1.

        Returns:
            A Surface containing the rendered text with outline applied.
        """
        if fg is None:
            fg = self.font_color
        if outline_color is None:
            outline_color = self.font_shadow_color

        scaled_width = max(1, self.scaling.scale_int(outline_width))

        base_surface = self.font.render(text, True, fg)
        w, h = base_surface.get_size()
        pad = scaled_width
        total_w = w + pad * 2
        total_h = h + pad * 2

        image = Surface((total_w, total_h), SRCALPHA)

        offsets = [
            (-pad, -pad), (0, -pad), (pad, -pad),
            (-pad,   0),             (pad,   0),
            (-pad,  pad), (0,  pad), (pad,  pad),
        ]
        outline_surface = self.font.render(text, True, outline_color)
        for ox, oy in offsets:
            image.blit(outline_surface, (pad + ox, pad + oy))

        image.blit(base_surface, (pad, pad))
        return image

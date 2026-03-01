# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>

from __future__ import annotations

import logging
from collections.abc import Iterable, Mapping
from enum import Enum
from typing import TYPE_CHECKING, Any, NoReturn, TypeVar
from uuid import UUID

from tuxemon.constants.asset_loader import fetch_asset
from tuxemon.scaling import ScalingStrategy

if TYPE_CHECKING:
    from pygame.rect import Rect

    from tuxemon.game_variables import ScopeVariablesManager
    from tuxemon.sprite import Sprite

logger = logging.getLogger(__name__)

# Used to indicate that a function should never be called
# https://typing.readthedocs.io/en/latest/source/unreachable.html
Never = NoReturn

TVar = TypeVar("TVar")
TEnum = TypeVar("TEnum", bound=Enum)


def transform_resource_filename(*filename: str) -> str:
    """
    Appends the resource folder name to a filename.

    Parameters:
        filename: Relative path of a resource.

    Returns:
        The absolute path of the resource.
    """
    return fetch_asset(*filename)


def get_screen_rect(sprite: Sprite, internal_rect: Rect) -> Rect:
    """
    Converts a rectangle from HUD local coordinates to screen coordinates.

    Parameters:
        sprite: The HUD sprite whose position on screen defines the base.
        internal_rect: The Rect relative to sprite.image.

    Returns:
        A Rect object in screen coordinates.
    """
    return internal_rect.move(sprite.rect.topleft)


def scale(number: int, scaling: ScalingStrategy | None = None) -> int:
    """Scale a number by the configured scale factor."""
    if scaling is None:
        from tuxemon.prepare import DISPLAY_CONTEXT

        scaling = DISPLAY_CONTEXT.scaling

    return scaling.scale_int(number)


def safe_enum_value(
    enum_class: type[TEnum],
    value: str | None,
    default: TEnum,
    raise_on_error: bool = False,
) -> TEnum:
    """
    Attempts to convert a string to an enum member.
    Raises or falls back to default on failure.
    """
    try:
        return enum_class(value)
    except (ValueError, TypeError) as e:
        if raise_on_error:
            raise ValueError(
                f"Invalid value for {enum_class.__name__}: {value!r}"
            ) from e
        logger.warning(
            f"Invalid value for {enum_class.__name__}: {value!r}, using default: {default}"
        )
        return default


def get_valid_uuid(
    game_variables: ScopeVariablesManager, variable_name: str
) -> UUID | None:
    """Safely retrieves a valid UUID from game variables."""
    raw_value: str | None = game_variables.get(variable_name)

    if raw_value in ("no_choice", "no_options", None):
        logger.info(
            f"Monster selection result for '{variable_name}': {raw_value}"
        )
        return None

    try:
        return UUID(str(raw_value))
    except (ValueError, TypeError) as e:
        logger.warning(
            f"Invalid UUID format for '{variable_name}': {raw_value} ({e})"
        )
        return None


def copy_dict_with_keys(
    source: Mapping[str, TVar],
    keys: Iterable[str],
) -> Mapping[str, TVar]:
    """
    Return new dict using only the keys/value from ``keys``.

    If key from keys is not present no error is raised.

    Parameters:
        source: Original mapping.
        keys: Allowed keys in the output mapping.

    Returns:
        New mapping with the keys restricted to those in ``keys``.
    """
    return {k: source[k] for k in keys if k in source}


def assert_never(value: Never) -> NoReturn:
    """
    Assertion for exhaustive checking of a variable.

    Parameters:
        value: The value that will be checked for exhaustiveness.
    """
    assert False, f"Unhandled value: {value} ({type(value).__name__})"


def format_playtime(seconds: float) -> str:
    """Convert seconds into a human-readable hours and minutes format."""
    minutes, sec = divmod(int(seconds), 60)
    hours, min = divmod(minutes, 60)
    return f"{hours}h {min}m"

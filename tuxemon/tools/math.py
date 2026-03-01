# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>

from __future__ import annotations

from collections.abc import Callable, Mapping
from operator import add, eq, ge, gt, le, lt, mul, ne, sub
from typing import Any

from tuxemon.compat.rect import ReadOnlyRect
from tuxemon.db import Comparison
from tuxemon.math import Vector2


def safe_floordiv(a: float, b: float) -> int:
    if b == 0:
        return int(a)  # no-op fallback
    return int(a // b)


ops_dict: Mapping[str, Callable[[float, float], int]] = {
    "+": add,
    "-": sub,
    "*": mul,
    "/": safe_floordiv,
}


def get_cell_coordinates(
    rect: ReadOnlyRect,
    point: tuple[int, int],
    size: tuple[int, int],
) -> tuple[int, int]:
    """Find the cell of size, within rect, that point occupies."""
    point = (point[0] - rect.x, point[1] - rect.y)
    cell_x = (point[0] // size[0]) * size[0]
    cell_y = (point[1] // size[1]) * size[1]
    return (cell_x, cell_y)


def vector2_to_tile_pos(vector: Vector2) -> tuple[int, int]:
    return (int(vector[0]), int(vector[1]))


def number_or_variable(variables: dict[str, Any], value: str) -> float:
    """
    Converts a string to a numeric value or retrieves a numeric variable by
    name.

    This function attempts to convert the input string `value` into a float.
    If that fails, it then tries to retrieve a variable by its name from the
    `variables` dictionary and convert its value to a float.

    Parameters:
        variables: A dictionary containing variable names and their
            corresponding values.
        value: Either a string containing a numeric value or the name of a
            variable.

    Returns:
        The numeric value obtained by converting the string or retrieving
        the variable.

    Raises:
        ValueError: If `value` is neither a valid numeric string nor a valid
        variable name, or the retrieved variable value cannot be converted to
        a float.
    """
    try:
        return float(value)
    except ValueError:
        try:
            return float(variables[value])
        except (KeyError, ValueError, TypeError):
            raise ValueError(
                f"Unable to retrieve numeric variable or convert value '{value}'."
            )


def round_to_divisible(x: float, base: int = 16) -> int:
    """
    Rounds a number to a divisible base.

    This is used to round collision areas that aren't defined well. This
    function assists in making sure collisions work if the map creator didn't
    set the collision areas to round numbers.

    Parameters:
        x: The number we want to round.
        base: The base that we want our number to be divisible by. By default
            this is 16.

    Returns:
        Rounded number that is divisible by ``base``.
    """
    return int(base * round(float(x) / base))


def compare(key: str, value1: int | float, value2: int | float) -> bool:
    """
    It compares and it returns a boleean whether is greater_than or not.

    It supports: less_than, less_or_equal, greater_than, greater_or_equal
        equals and not_equals.

    It supports: >, <, >=, <=, == and !=

    It raises a ValueError if the key isn't among the operators.

    Parameters:
        key: Key to check.
        value1: First value to compare.
        value2: Second value to compare.

    Returns:
        boolean: true / false
    """
    if key == Comparison.LESS_THAN or key == "<":
        return bool(lt(value1, value2))
    elif key == Comparison.LESS_OR_EQUAL or key == "<=":
        return bool(le(value1, value2))
    elif key == Comparison.GREATER_THAN or key == ">":
        return bool(gt(value1, value2))
    elif key == Comparison.GREATER_OR_EQUAL or key == ">=":
        return bool(ge(value1, value2))
    elif key == Comparison.EQUALS or key == "==":
        return bool(eq(value1, value2))
    elif key == Comparison.NOT_EQUALS or key == "!=":
        return bool(ne(value1, value2))
    else:
        raise ValueError(f"{key} isn't among {list(Comparison)}")


def compare_tuple(
    key: str,
    value1: tuple[int | float, int | float],
    value2: tuple[int | float, int | float],
) -> bool:
    """
    Tuple-based comparison using the same Comparison enum
    and symbolic operators supported by compare().
    """

    if key == Comparison.LESS_THAN or key == "<":
        return value1 < value2
    elif key == Comparison.LESS_OR_EQUAL or key == "<=":
        return value1 <= value2
    elif key == Comparison.GREATER_THAN or key == ">":
        return value1 > value2
    elif key == Comparison.GREATER_OR_EQUAL or key == ">=":
        return value1 >= value2
    elif key == Comparison.EQUALS or key == "==":
        return value1 == value2
    elif key == Comparison.NOT_EQUALS or key == "!=":
        return value1 != value2
    else:
        raise ValueError(f"{key} isn't among {list(Comparison)}")


def fix_measure(measure: int, percentage: float) -> int:
    """it returns the correct measure based on percentage"""
    return round(measure * percentage)

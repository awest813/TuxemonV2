# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import fields
from datetime import date, datetime, time, timedelta
from decimal import Decimal
from enum import Enum
from fractions import Fraction
from functools import lru_cache
from types import UnionType
from typing import (
    Any,
    Literal,
    Sequence,
    TypeVar,
    get_args,
    get_origin,
    get_type_hints,
)

ValidParameterSingleType = type[Any] | None
ValidParameterTypes = (
    ValidParameterSingleType | Sequence[ValidParameterSingleType]
)

TEnum = TypeVar("TEnum", bound=Enum)


def cast_value(
    i: tuple[tuple[ValidParameterTypes, str], Any],
) -> Any:
    """
    Attempt to cast a raw value into one of the expected types.

    Parameters:
        i: A tuple containing ((constructors, param_name), value).
           - constructors: sequence of type constructors or typing hints
           - param_name: name of the parameter (for error messages)
           - value: the raw value to cast

    Returns:
        The value cast to one of the expected types.

    Raises:
        ValueError: if the value cannot be cast to any of the expected types.
    """
    (type_constructors, param_name), value = i

    # Normalize constructors into a list
    if not isinstance(type_constructors, Sequence) or isinstance(
        type_constructors, type
    ):
        type_constructors = [type_constructors]

    # Expand Union/Optional types
    expanded: list[Any] = []
    for c in type_constructors:
        if c is None:
            expanded.append(type(None))
        elif get_origin(c) == UnionType:
            expanded.extend(get_args(c))
        else:
            expanded.append(c)

    constructors_to_try: list[Any] = [c for c in expanded if c is not None]
    is_optional = type(None) in expanded

    # Handle None
    if value is None:
        if is_optional:
            return None
        raise ValueError(f"Parameter '{param_name}' cannot be None.")

    # Handle empty string
    if isinstance(value, str) and not value.strip():
        if is_optional:
            return None
        if str in constructors_to_try:
            return ""
        raise ValueError(f"Parameter '{param_name}' cannot be empty string.")

    # First pass: direct isinstance
    for constructor in constructors_to_try:
        if get_origin(constructor) is Literal:
            continue
        origin = get_origin(constructor) or constructor
        try:
            if isinstance(value, origin):
                return value
        except TypeError:
            continue

    # Special handling for numerics
    if any(c in constructors_to_try for c in (int, float, Decimal, Fraction)):
        try:
            if (
                int in constructors_to_try
                and isinstance(value, str)
                and value.isdigit()
            ):
                return int(value)
            if int in constructors_to_try:
                try:
                    return int(value)
                except ValueError:
                    # allow "3.0" → 3
                    if isinstance(value, str) and "." in value:
                        return int(float(value))
            if float in constructors_to_try:
                return float(value)
            if Decimal in constructors_to_try:
                return Decimal(value)
            if Fraction in constructors_to_try:
                return Fraction(value)
        except Exception:
            pass

    # Special handling for booleans
    if bool in constructors_to_try:
        if isinstance(value, str):
            val = value.strip().lower()
            if val in ("true", "1", "yes", "on"):
                return True
            if val in ("false", "0", "no", "off"):
                return False
            raise ValueError(
                f"Parameter '{param_name}' cannot be cast to bool from string '{value}'."
            )
        return bool(value)

    # Special handling for datetime/date/time/timedelta
    if datetime in constructors_to_try:
        try:
            return datetime.fromisoformat(value)
        except Exception:
            pass
    if date in constructors_to_try:
        try:
            return date.fromisoformat(value)
        except Exception:
            pass
    if time in constructors_to_try:
        try:
            return time.fromisoformat(value)
        except Exception:
            pass
    if timedelta in constructors_to_try:
        try:
            return timedelta(seconds=float(value))
        except Exception:
            pass

    # Special handling for enums
    for constructor in constructors_to_try:
        if isinstance(constructor, type) and issubclass(constructor, Enum):
            if isinstance(value, constructor):
                return value
            try:
                return constructor(value)
            except Exception:
                pass

    # Handle Literal
    for constructor in constructors_to_try:
        if get_origin(constructor) is Literal:
            allowed_values = get_args(constructor)
            if value in allowed_values:
                return value
            raise ValueError(
                f"Parameter '{param_name}' must be one of {allowed_values}, got {value!r}"
            )

    # Handle collections (basic coercion)
    for constructor in constructors_to_try:
        origin = get_origin(constructor) or constructor
        if origin in (list, set, tuple):
            try:
                if isinstance(value, str):
                    parts = value.split(",")
                    if is_optional:
                        items = [
                            p.strip() if p.strip() else None for p in parts
                        ]
                    else:
                        items = [p.strip() for p in parts]
                    return origin(items)
                return origin(value)
            except Exception:
                pass
        elif origin is dict:
            try:
                if isinstance(value, str):
                    import json

                    return json.loads(value)
                return dict(value)
            except Exception:
                pass

    # Generic casting fallback
    for constructor in constructors_to_try:
        try:
            return constructor(value)
        except Exception:
            continue

    # Attempt to format expected types for cleaner error message
    expected_types = []
    for c in constructors_to_try:
        if isinstance(c, type):
            expected_types.append(c.__name__)
        elif get_origin(c) is Literal:
            expected_types.append(f"Literal{get_args(c)}")
        else:
            expected_types.append(str(c))

    expected_types_str = " | ".join(expected_types)

    # If all attempts fail
    raise ValueError(
        f"Error parsing parameter '{param_name}': Cannot cast value {value!r} "
        f"(type {type(value).__name__}) to expected type(s): {expected_types_str}"
    )


def get_types_tuple(
    param_type: ValidParameterSingleType,
) -> Sequence[ValidParameterSingleType]:
    """
    Expand a typing annotation into its component types.
    """
    origin = get_origin(param_type)

    if origin is UnionType:
        return get_args(param_type)

    if param_type is type(None):
        return (param_type,)

    return (param_type,)


@lru_cache(maxsize=None)
def get_cached_type_info(cls: type) -> dict[str, tuple[type, ...]]:
    """
    Retrieve and cache type information for dataclass fields.
    """
    type_hints = get_type_hints(cls)

    info = {}
    for field in fields(cls):
        if not field.init:
            continue

        component_types: list[Any] = []
        for t in get_types_tuple(type_hints[field.name]):
            if isinstance(t, type):
                component_types.append(t)
            elif get_origin(t) is Literal:
                component_types.append(t)
            elif t is type(None):
                component_types.append(type(None))

        info[field.name] = tuple(component_types)

    return info


def cast_dataclass_parameters(obj: Any) -> None:
    """
    Cast all dataclass fields to their annotated types.

    Args:
        obj: The dataclass instance to mutate.

    Side effects:
        Mutates the dataclass instance in place.

    Raises:
        ValueError: if any field cannot be cast to its annotated type.
    """
    field_info = get_cached_type_info(obj.__class__)
    for field_name, constructors in field_info.items():
        old_value = getattr(obj, field_name)
        try:
            new_value = cast_value(((constructors, field_name), old_value))
        except ValueError as e:
            raise ValueError(
                f"Failed to cast field '{field_name}' with value {old_value!r}: {e}"
            ) from e
        setattr(obj, field_name, new_value)

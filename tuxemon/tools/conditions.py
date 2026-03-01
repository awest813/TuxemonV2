# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>

import logging

logger = logging.getLogger(__name__)


def parse_flag(value: str | None) -> bool:
    """
    Convert a string flag to a boolean.

    Accepted truthy values: "true", "1", "yes" (case-insensitive).
    All other values (including None) return False.
    """
    return str(value or "").strip().lower() in {"true", "1", "yes"}


def check_condition(value: str, dataset: set[str]) -> bool:
    """
    Check if a condition is satisfied against a set of values.

    - If the input starts with '!', it asserts that the value is NOT in the dataset.
    - Otherwise, it asserts that the value IS in the dataset.
    """
    value = value.strip().lower()
    if not value:
        logger.debug("Empty condition skipped.")
        return False

    if value.startswith("!"):
        result = value[1:] not in dataset
        logger.debug(f"Checking NOT '{value[1:]}' in {dataset}: {result}")
        return result

    result = value in dataset
    logger.debug(f"Checking '{value}' in {dataset}: {result}")
    return result

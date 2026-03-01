# SPDX-License-Identifier: GPL-3.0
# Copyright (c) 2014-2026 William Edwards <shadowapex@gmail.com>, Benjamin Bean <superman2k5@gmail.com>

"""
Backward compatibility shim for tuxemon.tools.
All functionality has been moved to the submodules in tuxemon.tools package.
Importing from tuxemon.tools directly is deprecated and will emit a warning.
"""

import importlib
import warnings
from typing import Any

_deprecated_exports = {
    # TODO(TOOLS-201): Remove `Never` shim once all imports target `tuxemon.tools.misc` directly.
    "Never": "tuxemon.tools.misc",
    # TODO(TOOLS-202): Remove casting compatibility imports after sunset window (see docs/tools_phase1_issue_map.md).
    "ValidParameterSingleType": "tuxemon.tools.casting",
    "ValidParameterTypes": "tuxemon.tools.casting",
    "cast_dataclass_parameters": "tuxemon.tools.casting",
    "cast_value": "tuxemon.tools.casting",
    "get_cached_type_info": "tuxemon.tools.casting",
    "get_types_tuple": "tuxemon.tools.casting",
    # TODO(TOOLS-203): Remove condition helper compatibility imports after call sites migrate.
    "check_condition": "tuxemon.tools.conditions",
    "parse_flag": "tuxemon.tools.conditions",
    # TODO(TOOLS-204): Remove dialog helper compatibility imports after event module migration.
    "open_choice_dialog": "tuxemon.tools.dialog",
    "open_dialog": "tuxemon.tools.dialog",
    "show_result_as_dialog": "tuxemon.tools.dialog",
    # TODO(TOOLS-205): Remove math helper compatibility imports after direct module imports are complete.
    "compare": "tuxemon.tools.math",
    "compare_tuple": "tuxemon.tools.math",
    "fix_measure": "tuxemon.tools.math",
    "get_cell_coordinates": "tuxemon.tools.math",
    "number_or_variable": "tuxemon.tools.math",
    "ops_dict": "tuxemon.tools.math",
    "round_to_divisible": "tuxemon.tools.math",
    "safe_floordiv": "tuxemon.tools.math",
    "vector2_to_tile_pos": "tuxemon.tools.math",
    # TODO(TOOLS-206): Remove misc helper compatibility imports after module-level migration is complete.
    "assert_never": "tuxemon.tools.misc",
    "copy_dict_with_keys": "tuxemon.tools.misc",
    "format_playtime": "tuxemon.tools.misc",
    "get_screen_rect": "tuxemon.tools.misc",
    "get_valid_uuid": "tuxemon.tools.misc",
    "safe_enum_value": "tuxemon.tools.misc",
    "scale": "tuxemon.tools.misc",
    "transform_resource_filename": "tuxemon.tools.misc",
}


def __getattr__(name: str) -> Any:
    if name in _deprecated_exports:
        warnings.warn(
            f"Importing {name} from tuxemon.tools is deprecated. "
            f"Please import from the specific module in tuxemon.tools package.",
            DeprecationWarning,
            stacklevel=2,
        )
        module_name = _deprecated_exports[name]
        module = importlib.import_module(module_name)
        return getattr(module, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = list(_deprecated_exports.keys())

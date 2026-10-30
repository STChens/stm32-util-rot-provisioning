#
# ****************************************************************************
# @attention
#
# Copyright (c) 2026 STMicroelectronics.
# All rights reserved.
#
# This software is licensed under terms that can be found in the LICENSE file
# in the root directory of this software component.
# If no LICENSE file comes with this software, it is provided AS-IS.
#
# ****************************************************************************

from helper.config.example import ExampleConfig
from helper.tools.cube_programmer import CubeProgrammer, CubeProgrammerMode


def _compute_option_bytes_da(option_byte_step_name: str,
                             example_config: ExampleConfig) -> list[dict]:
    """Compute static option-byte groups for a standalone DA phase."""
    all_ob_dict = example_config.get_option_bytes()
    step_ob_dict = all_ob_dict[option_byte_step_name]

    final_ob = []
    for option_byte_group in step_ob_dict:
        ob_dict = dict(option_byte_group.get("static_values", {}))
        mode = CubeProgrammerMode(option_byte_group.get("mode", "hotplug"))
        reset = option_byte_group.get("reset", False)
        final_ob.append({"reset": reset, "mode": mode, "ob": ob_dict})
    return final_ob


def ob_da_apply(option_byte_step_name: str,
                example_config: ExampleConfig,
                cube_programmer: CubeProgrammer) -> None:
    """Apply static option-byte groups configured for a standalone DA phase."""
    ob_to_apply = _compute_option_bytes_da(option_byte_step_name, example_config)

    for ob in ob_to_apply:
        cube_programmer.set_option_bytes(ob["ob"], reset=ob["reset"], mode=ob["mode"])

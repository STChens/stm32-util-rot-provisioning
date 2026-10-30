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

import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))
from helper.config.option_bytes_base import compute_wrp, compute_hdp
from helper.config.example import ExampleConfig
from helper.config.oemirot.flash_layout import OEMiRoTFlashLayout
from helper.tools.cube_programmer import CubeProgrammer, CubeProgrammerMode
from helper.exception.rot_exception import RoTUnexpectedError


def _compute_option_bytes_oemirot(
    option_byte_step_name: str,
    example_config: ExampleConfig,
    flash_layout: OEMiRoTFlashLayout
) -> list[dict]:
    """
    Computes the option bytes configuration for a given step name.
    Calculates WRP and HDP option byte values based on the configuration and flash layout.

    Args:
        option_byte_step_name (str): Step name for option bytes.
        example_config (Example_Config): Configuration object.
        flash_layout (OEMiRoTFlashLayout): Flash layout object.
    Raises:
        RoTUnexpectedError: If an unsupported option byte type is encountered.
    Returns:
        list[dict]: List of dictionaries mapping option byte names to computed values.
    """
    all_ob_dict = example_config.get_option_bytes()
    memory_dict = example_config.get_memory()
    step_ob_dict = all_ob_dict[option_byte_step_name]

    bank_size = int(memory_dict["bank_size"], 16)
    block_size = int(memory_dict["block_size"], 16)
    hdp_block_size = int(memory_dict["hdp_block_size"], 16)

    final_ob = []

    for d in step_ob_dict:
        ob_dict = dict(d.get("static_values", {}))
        for ob in d.get("dynamic_values", []):
            ob_type = ob.get("type")
            if ob_type == "WRP":
                start_address = flash_layout.get_flash_layout("FLASH_ROT_WRP_START_OFFSET")
                end_address = flash_layout.get_flash_layout("FLASH_ROT_WRP_END_OFFSET")
                wrpgrp_size = memory_dict["wrpgrp_size"]
                wrpgrp_ob_length = memory_dict["wrpgrp_ob_length"]
                wrp_dict = compute_wrp(
                    start_address, end_address, wrpgrp_size, wrpgrp_ob_length,
                    bank_size, block_size, ob["ob_name_per_bank"]
                )
                ob_dict.update(wrp_dict)
            elif ob_type == "HDP":
                hdp_end_offset = flash_layout.get_flash_layout("FLASH_ROT_HDP_END_OFFSET")
                hdp_dict = compute_hdp(
                    hdp_end_offset, bank_size, hdp_block_size, ob["ob_name_per_bank"]
                )
                ob_dict.update(hdp_dict)
            else:
                raise RoTUnexpectedError(f"Unsupported option byte to compute: {ob}")

        # Getting mode, default to hotplug
        json_mode = d.get("mode", "hotplug")
        mode_enum = CubeProgrammerMode(json_mode)
        # Getting if reset necessary, default to False
        reset = d.get("reset", False)

        final_ob.append({"reset": reset, "mode": mode_enum, "ob": ob_dict})

    return final_ob


def ob_oemirot_apply(ob_step_option_byte_step_name: str,
                     example_config: ExampleConfig,
                     flash_layout: OEMiRoTFlashLayout,
                     cube_programmer: CubeProgrammer) -> None:
    """
    Applies all option bytes from a step, dynamic & static one, grouped as described in the OB json.

    Args:
        ob_step_option_byte_step_name (str): The name of the option byte step to apply.
        example_config (Example_Config): The configuration object containing example settings.
        flash_layout (OEMiRoTFlashLayout): The flash layout object for OEMiRoT.
        cube_programmer (CubeProgrammer): CubeProgrammer instance to set option bytes.

    Returns:
        None
    """
    ob_to_apply = _compute_option_bytes_oemirot(
        ob_step_option_byte_step_name, example_config, flash_layout)
    for ob in ob_to_apply:
        cube_programmer.set_option_bytes(ob["ob"], reset=ob["reset"], mode=ob["mode"])

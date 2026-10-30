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
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))
from helper.config.example import ExampleConfig
from helper.tools.cube_programmer import CubeProgrammer, CubeProgrammerMode
from helper.common.hxml import extract_xml_value_by_name
from helper.exception.rot_exception import RoTUnexpectedError


def _compute_ecc(field_name: str, ob_name: str, config_xml_path: str, invert_value: bool = False) -> dict:
    """
    Computes the ECC option-byte value from the STiRoT configuration XML.

    The XML entry is read and the raw XML value is normalized to the value
    expected by CubeProgrammer: any nonzero value maps to 1 and 0 maps to 0.

    Args:
        field_name (str): The name of the field in the XML to read.
        ob_name (str): The name of the option byte.
        config_xml_path (str): Path to the STiRoT configuration XML file.
        invert_value (bool): Whether to invert the computed ECC value.

    Returns:
        dict: A one-entry mapping of option-byte name to the computed ECC value.

    Raises:
        RoTUnexpectedError: If ``config_xml_path`` is not provided.
    """
    if config_xml_path is None:
        raise RoTUnexpectedError("A config XML path is required for XML dynamic option bytes.")

    ecc_dict = {}
    raw_value = extract_xml_value_by_name(
        config_xml_path,
        "Bool",
        field_name,
        "Value"
    )

    ecc_value = 1 if int(raw_value, 0) != 0 else 0
    if invert_value:
        ecc_value = 0 if ecc_value == 1 else 1
    ecc_dict[ob_name] = ecc_value
    return ecc_dict


def _compute_option_bytes_stirot(
    option_byte_step_name: str,
    example_config: ExampleConfig,
    config_xml_path: str = None,
) -> list[dict]:
    """
    Computes the option bytes configuration for STiRoT, using static and dynamic values from the JSON.

    Args:
        option_byte_step_name (str): Step name for option bytes.
        example_config (ExampleConfig): Configuration object.
        config_xml_path (str, optional): Path to the STiRoT configuration XML file. Required
            when the selected step contains XML-driven dynamic values such as ``ECC``.

    Returns:
        list[dict]: List of dictionaries mapping option byte names to computed values.

    Raises:
        RoTUnexpectedError: If a dynamic option-byte type is not supported.
    """
    all_ob_dict = example_config.get_option_bytes()
    step_ob_dict = all_ob_dict[option_byte_step_name]

    final_ob = []
    for d in step_ob_dict:
        ob_dict = dict(d.get("static_values", {}))
        for ob in d.get("dynamic_values", []):
            ob_type = ob.get("type")
            if ob_type == "ECC":
                ecc_dict = _compute_ecc(ob["field_name"], ob["ob_name"], config_xml_path, ob["invert_value"])
                ob_dict.update(ecc_dict)
            else:
                raise RoTUnexpectedError(f"Unsupported option byte to compute: {ob}")
        # Getting mode, default to hotplug
        json_mode = d.get("mode", "hotplug")
        mode_enum = CubeProgrammerMode(json_mode)
        # Getting if reset necessary, default to False
        reset = d.get("reset", False)
        final_ob.append({"reset": reset, "mode": mode_enum, "ob": ob_dict})
    return final_ob


def ob_stirot_apply(ob_step_option_byte_step_name: str,
                    example_config: ExampleConfig,
                    cube_programmer: CubeProgrammer,
                    config_xml_path: str = None) -> None:
    """
    Applies all option bytes from a step, dynamic & static one, grouped as described in the OB json.

    Args:
        ob_step_option_byte_step_name (str): The name of the option byte step to apply.
        example_config (ExampleConfig): The configuration object containing example settings.
        cube_programmer (CubeProgrammer): CubeProgrammer instance to set option bytes.
        config_xml_path (str, optional): Path to the STiRoT configuration XML file used for
            XML-driven dynamic values.

    Returns:
        None
    """
    ob_to_apply = _compute_option_bytes_stirot(
        ob_step_option_byte_step_name, example_config, config_xml_path)
    for ob in ob_to_apply:
        cube_programmer.set_option_bytes(ob["ob"], reset=ob["reset"], mode=ob["mode"])

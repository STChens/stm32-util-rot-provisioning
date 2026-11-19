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

import logging

from helper.workflow.step import Step
from helper.workflow.common.installation_step import (
    installation_substeps as _common_installation_substeps,
    installation_step_product,
    ProgramFinalProductStateStep,
    program_da_obk,
)
from helper.tools.cube_programmer import CubeProgrammer, CubeProgrammerMode
from helper.tools.cube_programmer_rdp import CubeProgrammerRDP
from helper.tools.cube_programmer_da import CubeProgrammerDA
from helper.config.example import ExampleConfig, LifecycleType
from helper.config.variant import OEMIROT_VARIANT
from helper.config.oemirot.flash_layout import OEMiRoTFlashLayout
from helper.config.oemirot.option_bytes import ob_oemirot_apply
from helper.tools.tools_config import Tools_Config
from helper.config.oemirot.appli_project import AppliProjectConfig
from helper.config.oemirot.provisioning import OEMiRoTProvisioningConfig
from helper.config.rdp_lifecycle import RDPLevel
from helper.config.oemirot.project import OEMiRoTProjectConfig
from helper.exception.rot_exception import RoTUnexpectedError, RoTValueError
from helper.common.hxml import extract_output_file_path

logger = logging.getLogger()

# Metadata for the overall installation step (RDP-specific; product state variant imported from common)
installation_step_rdp = {
    "id": "installation",
    "name": "Installation",
    "texts": [{"message": "The {board_name} must be in level 0 of Read Out Protection (RDP)"}],
    "wait_for_input": True,
    "success": "Successful installation"
}

# Substeps of the installation process (extends the common base with OEMiRoT-specific entries)
installation_substeps = {
    **_common_installation_substeps,
    "program_rdp_key":
    {
        "name": "RDP keys programming",
        "wait_for_input": False,
        "process": "RDP keys programming starts ...",
        "success": "Successful RDP keys programming"
    },
    "program_final_rdp_level":
    {
        "name": "Final RDP Level programming",
        "texts": [{"message": "Programming RDP, regression is impossible without the key !", "type": "warning"}],
        "wait_for_input": True,
        "process": "Final RDP Level programming starts ...",
        "success": "Successful Final RDP Level programming"
    },
}


def _validate_obk_skip(lifecycle_config, product_state, no_obk_provisioning: bool) -> None:
    if no_obk_provisioning and not lifecycle_config.is_open_product_state(product_state):
        raise RoTValueError("OBK provisioning cannot be skipped if the final product state is not OPEN.")


def _get_obk_programming_mode(config: OEMiRoTProvisioningConfig,
                              example_config: ExampleConfig) -> CubeProgrammerMode:
    final_product_state = config.lifecycle_config.get_product_state("final")
    if config.lifecycle_config.is_open_product_state(final_product_state):
        return CubeProgrammerMode(example_config.get_obk_mode())
    return CubeProgrammerMode.HOT_PLUG


class InstallationStep(Step):
    """
    Represents the main installation step in the workflow.

    Args:
        board_name (str): The name of the board being provisioned.
    """

    def __init__(self, board_name: str, lifecycle_type: str):
        if lifecycle_type == LifecycleType.RDP:
            super().__init__(installation_step_rdp)
        else:
            super().__init__(installation_step_product)
        self.log_param = {"board_name": board_name}


class RemoveOBStep(Step):
    """
    Represents the substep for removing option bytes.

    Args:
        example_config (Example_Config): example.json object for retrieving the default option bytes values.
        cube_programmer (CubeProgrammer): The CubeProgrammer instance for programming the option bytes.

    """

    def __init__(self, example_config: ExampleConfig, cube_programmer: CubeProgrammer, flash_layout: OEMiRoTFlashLayout):
        super().__init__(installation_substeps["remove_ob"])
        self.example_config = example_config
        self.cube_programmer = cube_programmer
        self.flash_layout = flash_layout

    def process_step(self):
        ob_oemirot_apply("default", self.example_config, self.flash_layout, self.cube_programmer)
        self.cube_programmer.erase_all_flash_sectors()


class InstallationSubstep(Step):
    """
    Represents the substep for flashing binaries during the installation process.

    Args:
        config (OEMiRoTProvisioningConfig): The provisioning object to retrieve binary path.
        cube_programmer (CubeProgrammer): The CubeProgrammer instance for flashing the binaries.
    """

    def __init__(self, config: OEMiRoTProvisioningConfig, cube_programmer: CubeProgrammer):
        super().__init__(installation_substeps["install"])
        self.provisioning_config = config
        self.appli_config = AppliProjectConfig(self.provisioning_config.get_appli_ini_path())
        self.oemirot_config = OEMiRoTProjectConfig(self.provisioning_config.get_oemirot_ini_path())
        self.example_config = ExampleConfig(self.provisioning_config.get_example_json_path())
        self.memory_config = OEMIROT_VARIANT.memory_config_cls(
            self.provisioning_config.get_memory_config_ini_path(), self.example_config)
        self.flash_layout = OEMiRoTFlashLayout(self.example_config,
                                               self.memory_config,
                                               config.get_oemirot_installation_mode())
        self.cube_programmer = cube_programmer
        self.base = int(self.example_config.get_memory()["base"], 16)

    def process_step(self):
        if self.example_config.get_option_bytes().get("preflash"):
            # Applying preflash OB
            ob_oemirot_apply("preflash", self.example_config, self.flash_layout, self.cube_programmer)

        if self.example_config.get_board().get("obk") == False:
            key_path_bin = extract_output_file_path(self.provisioning_config.get_config_keys_xml_path())
            config_data_offset = hex(self.base + self.flash_layout.get_flash_layout("FLASH_NVCNT_OFFSET"))
            key_offset = hex(self.base + self.flash_layout.get_flash_layout("FLASH_KEYS_OFFSET"))
            # Flash all the binaries
            self.cube_programmer.flash_binary(self.provisioning_config.get_config_data_path(), config_data_offset)
            self.cube_programmer.flash_binary(key_path_bin, key_offset)

        if self.flash_layout.get_flash_layout("DATA_IMAGE_NUMBER") == 1:
            appli_data_path_bin = extract_output_file_path(
                self.provisioning_config.get_appli_data_xml_path("provisioning"))
            self.cube_programmer.flash_binary(appli_data_path_bin)

        self.cube_programmer.flash_binary(self.appli_config.get_image_binary_path("provisioning"))
        oemirot_binary_path = self.oemirot_config.get_build_binary_path()
        oemirot_flash_addresses = self.provisioning_config.get_oemirot_binary_flash_addresses()
        if oemirot_flash_addresses:
            for address in oemirot_flash_addresses:
                self.cube_programmer.flash_binary(oemirot_binary_path, start_address=address)
        else:
            self.cube_programmer.flash_binary(oemirot_binary_path)


class OBKProgrammingSubstep(Step):
    """
    Represents the substep for flashing OBK binary during the installation process.

    Args:
        config (OEMiRoTProvisioningConfig): The provisioning object to retrieve binary path.
        cube_programmer (CubeProgrammer): The CubeProgrammer instance for flashing the binaries.
    """

    def __init__(self, config: OEMiRoTProvisioningConfig, cube_programmer: CubeProgrammer, no_obk_provisioning: bool):
        super().__init__(installation_substeps["program_obk"])
        self.provisioning_config = config
        self.cube_programmer = cube_programmer
        self.no_obk_provisioning = no_obk_provisioning
        self.example_config = ExampleConfig(self.provisioning_config.get_example_json_path())

    def check_skip(self) -> bool:
        final_product_state = self.provisioning_config.lifecycle_config.get_product_state("final")
        _validate_obk_skip(self.provisioning_config.lifecycle_config, final_product_state, self.no_obk_provisioning)
        return self.no_obk_provisioning

    def process_step(self):
        obk_mode = _get_obk_programming_mode(self.provisioning_config, self.example_config)
        program_da_obk(self.provisioning_config, self.cube_programmer)
        key_path_obk = extract_output_file_path(self.provisioning_config.get_config_keys_xml_path())
        self.cube_programmer.reset()
        self.cube_programmer.flash_obk(self.provisioning_config.get_config_data_path(), mode=obk_mode)
        self.cube_programmer.flash_obk(key_path_obk, mode=obk_mode)


class ProgramOBStep(Step):
    """
    Represents the substep for programming option bytes.

    Args:
        example_config (Example_Config): example.json object for retrieving the option bytes values.
        cube_programmer (CubeProgrammer): The CubeProgrammer instance for programming the option bytes.

    """

    def __init__(self, example_config: ExampleConfig, cube_programmer: CubeProgrammer, flash_layout: OEMiRoTFlashLayout):
        super().__init__(installation_substeps["program_ob"])
        self.log_param = {"name": "after provisioning"}
        self.example_config = example_config
        self.cube_programmer = cube_programmer
        self.flash_layout = flash_layout

    def process_step(self):
        ob_oemirot_apply("postflash", self.example_config, self.flash_layout, self.cube_programmer)


class ProgramRDPKeyStep(Step):
    """
    Represents the substep for programming RDP keys.

    Args:
        config (OEMiRoTProvisioningConfig): The provisioning configuration object for retrieving RDP key file paths.
        cube_programmer_rdp (CubeProgrammerRDP): The CubeProgrammerRDP instance for programming the RDP keys.

    """

    def __init__(self, config: OEMiRoTProvisioningConfig, cube_programmer_rdp: CubeProgrammerRDP):
        super().__init__(installation_substeps["program_rdp_key"])
        self.provisioning_config = config
        self.cube_programmer_rdp = cube_programmer_rdp

    def process_step(self):
        # Get the regression and transition RDP keys
        regression_rdp_key = self.provisioning_config.lifecycle_config.get_rdp_key("regression")
        transition_bs_key = self.provisioning_config.lifecycle_config.get_rdp_key("transition")

        # Program the RDP2 key using CubeProgrammerRDP
        self.cube_programmer_rdp.rdp_provision_password(password_list=regression_rdp_key)

        # program the boundary scan key using CubeProgrammerRDP
        self.cube_programmer_rdp.rdp_provision_2bs_key(bs_key=transition_bs_key[0])


class ProgramFinalRDPLevelStep(Step):
    """
    Represents the substep for setting the final RDP level.

    Args:
        config (OEMiRoTProvisioningConfig): The provisioning configuration object for retrieving the RDP level values.
        cube_programmer (CubeProgrammer): The CubeProgrammer instance for setting the RDP level.

    """

    def __init__(self, config: OEMiRoTProvisioningConfig, cube_programmer: CubeProgrammer):
        super().__init__(installation_substeps["program_final_rdp_level"])
        self.provisioning_config = config
        self.cube_programmer = cube_programmer

    def check_skip(self):
        return self.provisioning_config.lifecycle_config.get_rdp_level("final").value == RDPLevel.RDP_0.value

    def process_step(self):
        final_rdp_level = self.provisioning_config.lifecycle_config.get_rdp_level("final").value
        if final_rdp_level == RDPLevel.RDP_0.value:
            final_rdp_value = "0xED"
            return  # No need to program RDP level 0
        elif final_rdp_level == RDPLevel.RDP_2_BS.value:
            final_rdp_value = "0xD1"
        elif final_rdp_level == RDPLevel.RDP_2.value:
            final_rdp_value = "0x72"
        else:
            raise RoTValueError(f"Invalid final RDP level: {final_rdp_level}")
        self.cube_programmer.set_option_bytes({"RDP_level": final_rdp_value},
                                              reset=False, mode=CubeProgrammerMode.HOT_PLUG)


def _build_lifecycle_programmer(lifecycle_type: str, tools_config: Tools_Config, cube_programmer_kwargs: dict):
    programmer_by_lifecycle = {
        LifecycleType.RDP: CubeProgrammerRDP,
        LifecycleType.PRODUCT_STATE: CubeProgrammerDA,
    }
    programmer_cls = programmer_by_lifecycle.get(lifecycle_type)
    if programmer_cls is None:
        raise RoTUnexpectedError(f"Unsupported lifecycle type {lifecycle_type} for installation step setup")
    return programmer_cls(tools_config, **cube_programmer_kwargs)


def _add_lifecycle_final_step(installation_step: InstallationStep, lifecycle_type: str,
                              config: OEMiRoTProvisioningConfig, cube_programmer) -> None:
    final_step_by_lifecycle = {
        LifecycleType.RDP: ProgramFinalRDPLevelStep,
        LifecycleType.PRODUCT_STATE: ProgramFinalProductStateStep,
    }
    final_step_cls = final_step_by_lifecycle.get(lifecycle_type)
    if final_step_cls is None:
        raise RoTUnexpectedError(f"Unsupported lifecycle type {lifecycle_type} for installation step setup")
    installation_step.add_step(final_step_cls(config, cube_programmer))


def SetupInstallationStep(config: OEMiRoTProvisioningConfig, stlink_sn: str = None,
                          no_obk_provisioning: bool = False, dry_run: bool = False) -> Step:
    """
    Set up the installation step by adding all necessary substeps.

    Args:
        config (OEMiRoTProvisioningConfig): The provisioning configuration object.
        stlink_sn (str, optional): The serial number of the ST-Link device. Defaults to None.
        no_obk_provisioning (bool, optional): Flag to bypass the OBK provisioning step. Defaults to False.
        dry_run (bool, optional): If True, CubeProgrammer commands are logged but not executed. Defaults to False.
    Returns:
        Step: The fully configured installation step.
    """
    example_config = ExampleConfig(config.get_example_json_path())
    memory_config = OEMIROT_VARIANT.memory_config_cls(
        config.get_memory_config_ini_path(), example_config)
    flash_layout = OEMiRoTFlashLayout(example_config, memory_config, config.get_oemirot_installation_mode())
    tools_config = Tools_Config(config.get_tools_bin_env_name())
    board = example_config.get_board()
    lifecycle = example_config.get_lifecycle_type()
    cube_programmer_kwargs = {"stlink_sn": stlink_sn}
    if dry_run:
        cube_programmer_kwargs["dry_run"] = True
    cube_programmer = _build_lifecycle_programmer(lifecycle, tools_config, cube_programmer_kwargs)
    installation_step = InstallationStep(board_name=board.get("name"), lifecycle_type=lifecycle)
    installation_step.add_step(RemoveOBStep(example_config, cube_programmer, flash_layout))
    if lifecycle == LifecycleType.RDP:
        installation_step.add_step(ProgramRDPKeyStep(config, cube_programmer))
    installation_step.add_step(InstallationSubstep(config, cube_programmer))
    installation_step.add_step(ProgramOBStep(example_config, cube_programmer, flash_layout))

    if board.get("obk") == True:
        installation_step.add_step(OBKProgrammingSubstep(config, cube_programmer, no_obk_provisioning))
    _add_lifecycle_final_step(installation_step, lifecycle, config, cube_programmer)
    return installation_step

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

from helper.workflow.step import Step
from helper.workflow.common.installation_step import (
    program_da_obk,
    installation_substeps,
    InstallationStep,
    ProgramFinalProductStateStep,
)
from helper.tools.cube_programmer import CubeProgrammer
from helper.tools.cube_programmer_da import CubeProgrammerDA
from helper.config.example import ExampleConfig
from helper.tools.tools_config import Tools_Config
from helper.config.stirot.provisioning import STiRoTProvisioningConfig
from helper.config.stirot.option_bytes import ob_stirot_apply
from helper.config.stirot.appli_project import AppliProjectConfig
from helper.exception.rot_exception import RoTCLINonZeroExitError, RoTValueError
from helper.config.stirot.flash_layout import STiRoTFlashLayout
from helper.config.variant import STIROT_VARIANT
from helper.common.hxml import extract_output_file_path

BOOT0_RESET_WARNING = (
    "BOOT0 pin must be set to 1 (button pressed) at each reset if the final product state is OPEN"
)


def _validate_obk_skip(lifecycle_config, product_state, no_obk_provisioning: bool) -> None:
    if no_obk_provisioning and not lifecycle_config.is_open_product_state(product_state):
        raise RoTValueError("OBK provisioning cannot be skipped if the final product state is not OPEN.")


class RemoveOBStep(Step):
    """
    Represents the substep for removing option bytes.

    Args:
        example_config (Example_Config): example.json object for retrieving the default option bytes values.
        cube_programmer (CubeProgrammer): The CubeProgrammer instance for programming the option bytes.

    """

    def __init__(self, example_config: ExampleConfig, cube_programmer: CubeProgrammer):
        super().__init__(installation_substeps["remove_ob"])
        self.example_config = example_config
        self.cube_programmer = cube_programmer

    def process_step(self):
        ob_stirot_apply("default", self.example_config, self.cube_programmer)
        self.cube_programmer.erase_all_flash_sectors()


class InstallationSubstep(Step):
    """
    Represents the substep for flashing binaries during the installation process.

    Args:
        config (STiRoTProvisioningConfig): The provisioning object to retrieve binary path.
        cube_programmer (CubeProgrammer): The CubeProgrammer instance for flashing the binaries.
    """

    def __init__(self, config: STiRoTProvisioningConfig, cube_programmer: CubeProgrammer):
        super().__init__(installation_substeps["install"])
        self.provisioning_config = config
        self.appli_config = AppliProjectConfig(self.provisioning_config.get_appli_ini_path())
        self.cube_programmer = cube_programmer

    def process_step(self):
        self.cube_programmer.flash_binary(self.appli_config.get_image_binary_path("provisioning"))


class OBKProgrammingSubstep(Step):
    """
    Represents the substep for flashing OBK binary during the installation process.

    Args:
        config (STiRoTProvisioningConfig): The provisioning object to retrieve binary path.
        cube_programmer (CubeProgrammer): The CubeProgrammer instance for flashing the binaries.
        no_obk_provisioning (bool): Whether to bypass OBK provisioning when the final product state is OPEN.
    """

    def __init__(self, config: STiRoTProvisioningConfig, cube_programmer: CubeProgrammer, no_obk_provisioning: bool):
        super().__init__(installation_substeps["program_obk"])
        self.provisioning_config = config
        self.cube_programmer = cube_programmer
        self.example_config = ExampleConfig(self.provisioning_config.get_example_json_path())
        self.memory_config = STIROT_VARIANT.memory_config_cls(
            self.provisioning_config.get_memory_config_ini_path(), self.example_config)
        self.flash_layout = STiRoTFlashLayout(self.example_config, self.memory_config)
        self.no_obk_provisioning = no_obk_provisioning

    def check_skip(self) -> bool:
        final_product_state = self.provisioning_config.lifecycle_config.get_product_state("final")
        _validate_obk_skip(self.provisioning_config.lifecycle_config, final_product_state, self.no_obk_provisioning)
        return self.no_obk_provisioning

    def process_step(self):
        program_da_obk(self.provisioning_config, self.cube_programmer)
        self.cube_programmer.reset()
        if self.flash_layout.get_flash_layout("DATA_IMAGE_NUMBER") == 1:
            appli_data_path_obk = extract_output_file_path(
                self.provisioning_config.get_appli_data_obk_xml_path())
            self.cube_programmer.flash_obk(appli_data_path_obk)
            self.cube_programmer.reset()
        stirot_config_obk_path = extract_output_file_path(self.provisioning_config.get_stirot_config_xml_path())
        self.cube_programmer.flash_obk(stirot_config_obk_path)
        self.cube_programmer.reset()
        self.cube_programmer.flash_obk(self.provisioning_config.get_stirot_data_path())


class ProgramPostflashOBStep(Step):
    """
    Represents the substep for programming option bytes that must be set after flashing and before OBK programming.

    Args:
        config (STiRoTProvisioningConfig): The provisioning object to retrieve the example configuration.
        cube_programmer (CubeProgrammer): The CubeProgrammer instance for programming the option bytes.
    """

    def __init__(self, config: STiRoTProvisioningConfig, cube_programmer: CubeProgrammer):
        super().__init__(installation_substeps["program_ob"])
        self.log_param = {"name": "after provisioning"}
        self.config = config
        self.example_config = ExampleConfig(config.get_example_json_path())
        self.cube_programmer = cube_programmer

    def process_step(self):
        self.cube_programmer.reset()
        ob_stirot_apply(
            "postflash",
            self.example_config,
            self.cube_programmer,
            self.config.get_stirot_config_xml_path(),
        )


class ProgramPostobkOBStep(Step):
    """
    Represents the substep for programming option bytes after OBK programming.

    Args:
        config (STiRoTProvisioningConfig): The provisioning object to retrieve the example configuration.
        cube_programmer (CubeProgrammer): The CubeProgrammer instance for programming the option bytes.
    """

    def __init__(self, config: STiRoTProvisioningConfig, cube_programmer: CubeProgrammer):
        super().__init__(installation_substeps["program_ob"])
        self.log_param = {"name": "after OBK provisioning"}
        self.config = config
        self.example_config = ExampleConfig(config.get_example_json_path())
        self.cube_programmer = cube_programmer

    def process_step(self):
        self.cube_programmer.reset()
        try:
            ob_stirot_apply("postobk", self.example_config, self.cube_programmer)
        except RoTCLINonZeroExitError:
            if self.config.lifecycle_config.prevents_product_state_reconnect(
                    self.config.lifecycle_config.get_product_state("final")):
                raise


def SetupInstallationStep(config: STiRoTProvisioningConfig, stlink_sn: str = None,
                          no_obk_provisioning: bool = False, dry_run: bool = False) -> Step:
    """
    Set up the installation step by adding all necessary substeps.

    Args:
        config (STiRoTProvisioningConfig): The provisioning configuration object.
        stlink_sn (str, optional): The serial number of the ST-Link device. Defaults to None.
        no_obk_provisioning (bool, optional): Flag to bypass the OBK provisioning step. Defaults to False.
        dry_run (bool, optional): If True, CubeProgrammer commands are logged but not executed. Defaults to False.
    Returns:
        Step: The fully configured installation step.
    """
    example_config = ExampleConfig(config.get_example_json_path())
    tools_config = Tools_Config(config.get_tools_bin_env_name())
    cube_programmer_kwargs = {"stlink_sn": stlink_sn}
    if dry_run:
        cube_programmer_kwargs["dry_run"] = True
    cube_programmer = CubeProgrammerDA(tools_config, **cube_programmer_kwargs)
    board = example_config.get_board()
    installation_step = InstallationStep(board_name=board.get("name"), final_warning=BOOT0_RESET_WARNING)
    installation_step.add_step(RemoveOBStep(example_config, cube_programmer))
    installation_step.add_step(InstallationSubstep(config, cube_programmer))
    installation_step.add_step(ProgramPostflashOBStep(config, cube_programmer))
    installation_step.add_step(OBKProgrammingSubstep(config, cube_programmer, no_obk_provisioning))
    installation_step.add_step(ProgramPostobkOBStep(config, cube_programmer))
    installation_step.add_step(ProgramFinalProductStateStep(config, cube_programmer))

    return installation_step

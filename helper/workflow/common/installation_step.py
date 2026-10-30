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
import time

from helper.common.hxml import extract_output_file_path
from helper.workflow.step import Step
from helper.tools.cube_programmer import CubeProgrammerMode
from helper.exception.rot_exception import RoTCLINonZeroExitError, RoTValueError
from helper.config.provisioning_base import BaseProvisioningConfig
from helper.tools.cube_programmer import CubeProgrammer

logger = logging.getLogger()

FINAL_PRODUCT_STATE_DELAY = 2

# Metadata for the installation step (product state lifecycle)
installation_step_product = {
    "id": "installation",
    "name": "Installation",
    "texts": [{"message": "The {board_name} must be in OPEN state", "type": "warning"}, {"message": "BOOT0 pin must be set to 0 (button not pressed)", "type": "warning"}],
    "wait_for_input": True,
    "success": "Successful installation"
}

# Substeps of the installation process (shared across RoT types)
installation_substeps = {
    "remove_ob":
    {
        "name": "Option Bytes removing",
        "wait_for_input": False,
        "process": "Option Bytes removing starts ...",
        "success": "Successful Option Bytes removing"
    },
    "install":
    {
        "name": "Installation",
        "wait_for_input": False,
        "process": "Provisioning starts ...",
        "success": "Successful Provisioning"
    },
    "program_ob":
    {
        "name": "Option Bytes programming {name}",
        "wait_for_input": False,
        "process": "Option Bytes programming starts ...",
        "success": "Successful Option Bytes programming"
    },
    "program_obk":
    {
        "name": "OBK programming",
        "texts": [{"message": "BOOT0 pin must be set to 1 (button pressed) if the final product state is OPEN", "type": "warning"}],
        "wait_for_input": True,
        "process": "OBK programming starts ...",
        "success": "Successful OBK programming"
    },

    "program_final_product_state":
    {
        "name": "Final Product State programming",
        "wait_for_input": True,
        "process": "Final Product State programming starts ...",
        "success": "Successful Final Product State programming"
    },
}


def program_da_obk(provisioning_config: BaseProvisioningConfig, cube_programmer: CubeProgrammer,
                   handle_product_state: bool = True) -> None:
    """Program the DA OBK, optionally preparing the installation product state."""

    lifecycle_config = provisioning_config.lifecycle_config
    final_product_state = lifecycle_config.get_product_state("final")
    # DA regression always flashes the OBK; normal provisioning also sets the
    # provisioning state and flashes the OBK only for a non-OPEN final state.
    if handle_product_state:
        if lifecycle_config.is_open_product_state(final_product_state):
            # Normal provisioning skips the DA OBK when the final state is OPEN.
            return
        provisioning_state = lifecycle_config.get_provisioning_state()["name"]
        provisioning_option_bytes = lifecycle_config.get_product_state_option_bytes(provisioning_state)
        cube_programmer.set_option_bytes(
            provisioning_option_bytes, reset=False, mode=CubeProgrammerMode.HOT_PLUG)
    da_config_obk_path = extract_output_file_path(lifecycle_config.get_da_config_xml_path())
    cube_programmer.reset()
    cube_programmer.flash_obk(da_config_obk_path)
    cube_programmer.reset()


def program_final_product_state(provisioning_config: BaseProvisioningConfig, cube_programmer: CubeProgrammer) -> None:
    """
    Programs the requested final product state after installation completes.

    CubeProgrammer reports a non-zero exit code when the device reaches a
    terminal state where it cannot reconnect, so non-open final states are
    treated as successful terminal states.
    """
    lifecycle_config = provisioning_config.lifecycle_config
    final_product_state = lifecycle_config.get_product_state("final")
    final_product_state_option_bytes = lifecycle_config.get_product_state_option_bytes(final_product_state)

    if (provisioning_config.example_config.get_board()["da"]
            and not lifecycle_config.is_open_product_state(final_product_state)):
        da_provisioning_valid = cube_programmer.is_da_provisioning_valid()
        if not cube_programmer.dry_run and not da_provisioning_valid:
            raise RoTValueError(
                "DA provisioning integrity status is not VALID. Final product state was not "
                "programmed. Verify the DA OBK and configuration, then retry provisioning."
            )

    try:
        cube_programmer.set_option_bytes(
            final_product_state_option_bytes, reset=False, mode=CubeProgrammerMode.HOT_PLUG)
    except RoTCLINonZeroExitError:
        if not lifecycle_config.prevents_product_state_reconnect(final_product_state):
            raise


class ProgramFinalProductStateStep(Step):
    """
    Represents the substep for setting the final product state.

    Args:
        config: The provisioning configuration object for retrieving the product state.
        cube_programmer: The CubeProgrammer instance for setting the product state.
    """

    def __init__(self, config, cube_programmer):
        super().__init__(installation_substeps["program_final_product_state"])
        self.provisioning_config = config
        self.cube_programmer = cube_programmer

    def process_step(self):
        program_final_product_state(self.provisioning_config, self.cube_programmer)
        time.sleep(FINAL_PRODUCT_STATE_DELAY)


class InstallationStep(Step):
    """
    Represents the main installation step in the workflow.

    Args:
        board_name (str): The name of the board being provisioned.
        final_warning (str, optional): A warning message logged once the installation
            step completes successfully. Defaults to None (no extra warning).
    """

    def __init__(self, board_name: str, final_warning: str = None):
        super().__init__(installation_step_product)
        self.log_param = {"board_name": board_name}
        self.final_warning = final_warning

    def process_step(self):
        pass

    def print_step_success(self) -> None:
        super().print_step_success()
        if self.final_warning:
            logger.warning(f"{self.get_prefix()}{self.final_warning}")

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

from helper.tools.cube_programmer_da import CubeProgrammerDA
from helper.tools.tools_config import Tools_Config
from helper.config.provisioning_base import BaseProvisioningConfig
from helper.workflow.step import Step


discovery_step = {
    "id": "discovery",
    "name": "DA discovery",
    "wait_for_input": False,
    "success": "Successful DA discovery",
    "skip_if_auto": False
}


class DiscoveryStep(Step):
    """Run DA discovery through STM32CubeProgrammer."""

    def __init__(self, config: BaseProvisioningConfig, **kwargs):
        super().__init__(discovery_step)
        tools_config = Tools_Config(config.get_tools_bin_env_name())
        self.cube_programmer_da = CubeProgrammerDA(tools_config, **kwargs)

    def process_step(self):
        self.cube_programmer_da.da_discovery()

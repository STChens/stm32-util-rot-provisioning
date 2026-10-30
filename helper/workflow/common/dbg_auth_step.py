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

from helper.config.product_state_lifecycle import DAType
from helper.config.provisioning_base import BaseProvisioningConfig
from helper.tools.cube_programmer_da import CubeProgrammerDA
from helper.tools.tools_config import Tools_Config
from helper.workflow.step import Step
from helper.exception.rot_exception import RoTValueError


dbg_auth_step = {
    "id": "dbg_auth",
    "name": "Debug authentication",
    "wait_for_input": False,
    "success": "Successful debug authentication",
}


class DbgAuthStep(Step):
    """Authenticate a debug session using a user-selected permission."""

    def __init__(self, config: BaseProvisioningConfig, choice=None, **kwargs):
        super().__init__(dict(dbg_auth_step))
        self.choice = choice
        tools_config = Tools_Config(config.get_tools_bin_env_name())
        self.cube_programmer_da = CubeProgrammerDA(tools_config, **kwargs)
        if config.lifecycle_config.get_da_type() == DAType.PASSWORD:
            self.key_path = None
            self.certificate_path = None
            self.password_path = config.lifecycle_config.get_da_password_path()
        elif config.lifecycle_config.get_da_type() == DAType.CERTIFICATES:
            self.key_path = config.lifecycle_config.get_da_key_path()
            self.certificate_path = config.lifecycle_config.get_da_certificate_path()
            self.password_path = None
        else:
            raise RoTValueError(f"Unsupported DA type: {config.lifecycle_config.get_da_type()}")

    def process_step(self):
        self.cube_programmer_da.dbg_auth(
            permission=self.choice,
            key=self.key_path,
            certificate=self.certificate_path,
            password=self.password_path,
        )

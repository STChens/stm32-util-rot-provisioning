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
from helper.config.provisioning_base import BaseProvisioningConfig
from helper.config.product_state_lifecycle import DAType, get_st_lifecycle_description
from helper.workflow.common.installation_step import program_da_obk
from helper.tools.cube_programmer_rdp import CubeProgrammerRDP
from helper.tools.cube_programmer_da import CubeProgrammerDA
from helper.exception.rot_exception import RoTValueError

# Metadata for the overall regression step
regression_step = {
    "id": "regression",
    "name": "Regression",
    "wait_for_input": False,
    "success": "Successful regression",
    "skip_if_auto": False
}

# Substeps for the Product State regression process
da_regression_substeps = {
    "da_regression_certificates": {
        "name": "DA regression",
        "texts": [{"message": "DA regression using the key ({key_path}) and certificate ({cert_path})", "type": "warning"}, {"type": "warning", "message": "This will erase all the content of the device!"}],
        "skip_if_auto": False,
        "wait_for_input": True,
    },
    "da_regression_password": {
        "name": "DA regression",
        "texts": [{"message": "DA regression using the password ({password_path})", "type": "warning"}, {"type": "warning", "message": "This will erase all the content of the device!"}],
        "skip_if_auto": False,
        "wait_for_input": True,
    },
    "da_regression_open": {
        "type": "info",
        "message": "Board is already in OPEN state. DA regression is not needed.",
    },
}


# Substeps for the RDP configuration process
rdp_regression_substeps = {
    "rdp_regression": {
        "name": "RDP regression",
        "texts": [{"message": "RDP regression using the RDP key ({path})", "type": "warning"}, {"type": "warning", "message": "This will erase all the content of the device!"}],
        "skip_if_auto": False,
        "wait_for_input": True,
    },
}


class RegressionStep(Step):
    """
    Represents the main regression step in the workflow.
    """

    def __init__(self):
        super().__init__(regression_step)

    def process_step(self):
        pass


class RDPRegressionStep(Step):
    """
    Represents the substep for perform an RDP regression.

    Args:
        config (BaseProvisioningConfig): The provisioning configuration object for retrieving RDP key file paths.
        cube_programmer_rdp (CubeProgrammerRDP): The CubeProgrammerRDP instance for programming the RDP keys.

    """

    def __init__(self, config: BaseProvisioningConfig, cube_programmer_rdp: CubeProgrammerRDP):
        super().__init__(rdp_regression_substeps["rdp_regression"])
        self.log_param = {'path': config.lifecycle_config.get_regression_rdp_key_path()}
        self.provisioning_config = config
        self.cube_programmer_rdp = cube_programmer_rdp

    def process_step(self):
        # check and get the regression RDP key
        regression_rdp_key = self.provisioning_config.lifecycle_config.get_rdp_key("regression")

        # Program the RDP2 key using CubeProgrammerRDP
        self.cube_programmer_rdp.rdp_regression_password(password_list=regression_rdp_key)


class DARegressionStep(Step):
    """
    Represents the substep for performing a DA regression.

    Args:
        config (BaseProvisioningConfig): The provisioning configuration object for retrieving DA key file path.
        cube_programmer_da (CubeProgrammerDA): The CubeProgrammerDA instance for programming the DA keys.

    """

    def __init__(self, config: BaseProvisioningConfig, cube_programmer_da: CubeProgrammerDA):
        self.da_type = config.lifecycle_config.get_da_type()
        if self.da_type == DAType.PASSWORD:
            super().__init__(da_regression_substeps["da_regression_password"])
            self.password_path = config.lifecycle_config.get_da_password_path()
            self.log_param = {'password_path': self.password_path}
        elif self.da_type == DAType.CERTIFICATES:
            super().__init__(da_regression_substeps["da_regression_certificates"])
            self.key_path = config.lifecycle_config.get_da_key_path()
            self.cert_path = config.lifecycle_config.get_da_certificate_path()
            self.log_param = {'key_path': self.key_path, 'cert_path': self.cert_path}
        else:
            raise RoTValueError(f"Unsupported DA type: {self.da_type}")
        self.provisioning_config = config
        self.cube_programmer_da = cube_programmer_da

    def process_step(self):
        lifecycle_state = self.cube_programmer_da.get_lifecycle_state()
        open_states = self.provisioning_config.lifecycle_config.get_open_states()
        open_descriptions = {
            get_st_lifecycle_description(state["name"])
            for state in open_states
        }
        if lifecycle_state in open_descriptions:
            self._print_line(da_regression_substeps["da_regression_open"])
            return

        provisioning_state = self.provisioning_config.lifecycle_config.get_provisioning_state()
        if lifecycle_state == get_st_lifecycle_description(provisioning_state["name"]):
            program_da_obk(self.provisioning_config, self.cube_programmer_da, handle_product_state=False)

        # Program the DA key using CubeProgrammerDA
        if self.da_type == DAType.PASSWORD:
            self.cube_programmer_da.da_regression_password(password=self.password_path)
        elif self.da_type == DAType.CERTIFICATES:
            self.cube_programmer_da.da_regression_certificate(certificate=self.cert_path, key=self.key_path)
        else:
            raise RoTValueError(f"Unsupported DA type: {self.da_type}")

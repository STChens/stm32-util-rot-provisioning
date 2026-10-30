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
from helper.workflow.common.regression_step import RegressionStep, RDPRegressionStep, DARegressionStep
from helper.tools.tools_config import Tools_Config
from helper.config.stirot.provisioning import STiRoTProvisioningConfig
from helper.config.example import ExampleConfig, LifecycleType
from helper.exception.rot_exception import RoTUnexpectedError
from helper.tools.cube_programmer_da import CubeProgrammerDA
from helper.tools.cube_programmer_rdp import CubeProgrammerRDP
from stirot.installation_step import RemoveOBStep


def SetupRegressionStep(config: STiRoTProvisioningConfig, stlink_sn: str = None, remove_ob: bool = True,
                        dry_run: bool = False) -> Step:
    """
    Set up the regression step by adding all necessary substeps.

    Args:
        config: The provisioning configuration object containing paths and settings.
        stlink_sn: Optional ST-Link serial number to use to perform DA regression.
        dry_run: If True, CubeProgrammer commands are logged but not executed.

    Returns:
        Step: The fully configured regression step.
    """
    cube_programmer_kwargs = {"stlink_sn": stlink_sn, "dry_run": dry_run}
    tools_config = Tools_Config(config.get_tools_bin_env_name())
    regressionStep = RegressionStep()
    cube_programmer = CubeProgrammerDA(tools_config, **cube_programmer_kwargs)
    regressionStep.add_step(DARegressionStep(config, cube_programmer))

    if remove_ob:
        example_config = ExampleConfig(config.get_example_json_path())
        regressionStep.add_step(RemoveOBStep(example_config, cube_programmer))

    return regressionStep

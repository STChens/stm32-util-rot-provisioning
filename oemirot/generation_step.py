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
import os
from helper.common.hxml import (
    extract_output_file_path,
    update_xml_value_by_title,
    update_xml_value_by_name,
)
from helper.workflow.step import Step
from helper.workflow.common.generation_step import (
    bin_log,
    appli_data_configuration_substeps,
    GenerationStep,
    BinaryGeneration,
    ProductStateSelection,
    DATypeSelection,
    SetupProductStateConfigurationStep,
    DAConfig,
    UserMemoryConfigurationStep,
    AppliDataStep,
)
from helper.tools.tpc import TPC
from helper.tools.tools_config import Tools_Config
from helper.config.oemirot.appli_project import AppliProjectConfig
from helper.config.oemirot.project import OEMiRoTProjectConfig
from helper.config.variant import OEMIROT_VARIANT
from helper.config.oemirot.provisioning import OEMiRoTInstallationMode, OEMiRoTProvisioningConfig
from helper.config.rdp_lifecycle import RDPLevel
from helper.config.oemirot.flash_layout import OEMiRoTFlashLayout
from helper.config.example import ExampleConfig, LifecycleType
from helper.exception.rot_exception import RoTValueError
from helper.config.oemirot.installation_mode_xml import update_installation_mode_xml_param

logger = logging.getLogger()

# Metadata for the RDP configuration step
rdp_configuration_step = {
    "id": "rdp_configuration",
    "name": "RDP Configuration",
    "wait_for_input": False,
    "success": "Successful RDP configuration",
    "skip_if_auto": True
}

# Substeps for the RDP configuration process
rdp_configuration_substeps = {
    "rdp_key_update": {
        "name": "{name} update",
        "texts": [{"message": "Update the {name} ({path}) and continue"}],
        "skip_if_auto": True,
    },
    "rdp_selection": {
        "name": "{name} RDP level selection",
        "texts": [{"message": "Updating the {name} RDP level ({path})"}],
        "questions": {
            "message": "Select the {name} RDP level: ",
            "options": ["RDP_0", "RDP_2_BS", "RDP_2"]
        },
        "skip_if_auto": True,
        "wait_for_input": False,
    },
}

# Substeps for the key configuration process
key_configuration_substeps = {
    "key_config":
    {
        "name": "Keys Configuration",
        "texts": [
            {"message": "From TrustedPackageCreator (OBKey/Data Generation tab in Secure panel)"},
            {"message": "Select {key_config_xml} as the configuration file"},
            {"message": "Default keys must NOT be used in a product. Make sure to regenerate your own keys !", "type": "warning"},
            {"message": "Update the configuration (if/as needed) then generate the {key_config_output_path} file"}
        ],
        "wait_for_input": True,
        "skip_if_auto": False,
        "process": bin_log["processing"],
        "success": bin_log["success"],
    },
}

oemirot_configuration_substeps = {
    "installation_mode_selection": {
        "name": "OEMiRoT installation mode selection",
        "texts": [{"message": "Updating the OEMiRoT installation mode ({path})"}],
        "questions": {
            "message": "Select the OEMiRoT installation mode: ",
            "options": [mode.value for mode in OEMiRoTInstallationMode]
        },
        "skip_if_auto": True,
        "wait_for_input": False,
        "success": "Successful OEMiRoT installation mode selection",
    },
}


class RDPConfigurationStep(Step):
    """
    Represents the RDP configuration step in the workflow.
    """

    def __init__(self):
        super().__init__(rdp_configuration_step)

    def process_step(self):
        pass


class AppliDataConfig(Step):
    """
    Represents the appli data configuration and generation substep.

    Args:
        config: The configuration object containing paths and settings.
    """

    def __init__(self, appli_data_xml_type: str, config: OEMiRoTProvisioningConfig):
        super().__init__(appli_data_configuration_substeps["appli_data_config"])
        self.config = config
        self.key_config_xml = config.get_config_keys_xml_path()
        self.appli_data_bin_xml = config.get_appli_data_xml_path(appli_data_xml_type)
        self.appli_data_type = appli_data_xml_type
        self.log_param = {
            'appli_data_xml_type': self.appli_data_type,
            'appli_data_xml': self.appli_data_bin_xml,
            'appli_data_output_bin_path': extract_output_file_path(self.appli_data_bin_xml)}
        self.tpc = TPC(Tools_Config(config.get_tools_bin_env_name()))
        self.example_config = ExampleConfig(config.get_example_json_path())

    def _data_xml_update(self):
        flash_layout = OEMiRoTFlashLayout(
            self.example_config,
            OEMIROT_VARIANT.memory_config_cls(
                self.config.get_memory_config_ini_path(), self.example_config),
            self.config.get_oemirot_installation_mode(),
        )
        if self.appli_data_type == "provisioning":
            data_offset = hex(flash_layout.get_flash_layout("DATA_HEX_FORMAT"))
            update_xml_value_by_name(self.appli_data_bin_xml, "Param",
                                     "Firmware download area offset", "Value", data_offset)

        installation_mode = self.config.get_oemirot_installation_mode()
        update_installation_mode_xml_param(self.appli_data_bin_xml, installation_mode)

        data_size = hex(flash_layout.get_flash_layout("FLASH_PRIMARY_DATA_SLOT_SIZE"))
        update_xml_value_by_name(self.appli_data_bin_xml, "Param", "Firmware area size", "Value", data_size)
        rel_path_in_image_xml = os.path.relpath(
            self.key_config_xml, os.path.dirname(self.appli_data_bin_xml))
        update_xml_value_by_title(self.appli_data_bin_xml, "GlobalParam",
                                  "Data image generation", "LinkedXML", rel_path_in_image_xml)

    def process_step(self):
        self._data_xml_update()
        self.tpc.gen_image(self.appli_data_bin_xml)


class RDPKeyUpdate(Step):
    """
    Represents the RDP key update substep in the generation process.

    Args:
        name (str): The name of the RDP key being updated.
        rdp_key_path (str): The path where the RDP key will be updated.
    """

    def __init__(self, name: str, config: OEMiRoTProvisioningConfig):
        super().__init__(rdp_configuration_substeps["rdp_key_update"])
        if name == "Regression RDP key file":
            rdp_key_path = config.lifecycle_config.get_regression_rdp_key_path()
            self.type = "regression"
        elif name == "Transition RDP bs key file":
            rdp_key_path = config.lifecycle_config.get_transition_bs_key_path()
            self.type = "transition"
        self.log_param = {'name': name, 'path': rdp_key_path}
        self.name = name
        self.config = config

    def process_step(self):
        message = f"Updating {self.log_param['name']} at {self.log_param['path']}"
        logger.debug(message)
        rdp_key = self.config.lifecycle_config.get_rdp_key(self.type)
        logger.debug(f"{self.log_param['name']}: {rdp_key}")


class RDPSelection(Step):
    """
    Represents the RDP selection substep in the generation process.

    Args:
        name (str): The name of the final RDP level being selected.
        config (OEMiRoTProvisioningConfig): The configuration object containing paths and settings.
    """

    def __init__(self, name: str, config: OEMiRoTProvisioningConfig):
        super().__init__(rdp_configuration_substeps["rdp_selection"])
        self.name = name
        self.log_param = {'name': self.name.capitalize(), 'path': config.config_path}
        self.config = config

    def _get_question_default_candidate(self, question: dict) -> object:
        return self.config.lifecycle_config.get_rdp_level(self.name)

    def process_step(self):
        # Compare final choice with min RDP level
        if self.name == "final":
            self._compare_final_with_min_rdp_levels()
        self.config.lifecycle_config.set_rdp_level(self.name, self.choice)

    def _compare_final_with_min_rdp_levels(self) -> None:
        """
        Compare the final choice RDP level with the min RDP levels from the config.
        Raises:
            RoTValueError: If the final choice RDP level is lower than the min RDP level.
        """
        rdp_order = {
            RDPLevel.RDP_0: 0,
            RDPLevel.RDP_2_BS: 1,
            RDPLevel.RDP_2: 2
        }
        min_level = RDPLevel(self.config.lifecycle_config.get_rdp_level("min"))
        final_level = RDPLevel(self.choice)
        if rdp_order[final_level] < rdp_order[min_level]:
            raise RoTValueError(
                f"Final RDP level '{self.choice}' cannot be lower than minimum RDP level ('{min_level.value}').")


class KeyConfigurationStep(Step):
    """
    Represents the key update substep in the generation process.

    Args:
        config: The configuration object containing paths and settings.
    """

    def __init__(self, config: OEMiRoTProvisioningConfig):
        super().__init__(key_configuration_substeps["key_config"])
        self.key_config_xml = config.get_config_keys_xml_path()
        self.log_param = {'key_config_xml': self.key_config_xml,
                          'key_config_output_path': extract_output_file_path(self.key_config_xml)}
        self.tpc = TPC(Tools_Config(config.get_tools_bin_env_name()))

    def process_step(self):
        self.tpc.gen_obk(self.key_config_xml)


class OEMiRoTInstallationModeSelection(Step):
    """
    Represents the OEMiRoT installation mode selection substep.

    Args:
        config: The OEMiRoT provisioning configuration object.
    """

    def __init__(self, config: OEMiRoTProvisioningConfig):
        step_config = dict(oemirot_configuration_substeps["installation_mode_selection"])
        step_config["questions"] = dict(step_config["questions"])
        if int(config.memory_config.get_secondary_app_size(), 16) == 0:
            step_config["questions"]["options"] = [OEMiRoTInstallationMode.OVERWRITE.value]
        super().__init__(step_config)
        self.config = config
        self.log_param = {'path': config.config_path}

    def _get_question_default_candidate(self, question: dict) -> object:
        return self.config.get_oemirot_installation_mode()

    def process_step(self):
        self.config.set_oemirot_installation_mode(self.choice)


def SetupGenerationStep(config: OEMiRoTProvisioningConfig) -> Step:
    """
    Set up the generation step by adding all necessary substeps.

    Args:
        config: The configuration object containing paths and settings.

    Returns:
        Step: The fully configured generation step.
    """
    generationStep = GenerationStep()
    static_config = config.get_static_config()
    generationStep.set_static_config(static_config)
    if static_config is not True:
        generationStep.add_step(OEMiRoTInstallationModeSelection(config))

    def _flash_layout_factory():
        ec = ExampleConfig(config.get_example_json_path())
        return OEMiRoTFlashLayout(
            ec,
            OEMIROT_VARIANT.memory_config_cls(config.get_memory_config_ini_path(), ec),
            config.get_oemirot_installation_mode())

    oemirot_config = OEMiRoTProjectConfig(config.get_oemirot_ini_path())
    if static_config is not True:
        memoryConfigStep = UserMemoryConfigurationStep(
            config.get_memory_config_ini_path(), flash_layout_factory=_flash_layout_factory)
        generationStep.add_step(memoryConfigStep)
    else:
        _flash_layout_factory()
    key_config_step = KeyConfigurationStep(config)
    generationStep.add_step(key_config_step)
    example_config = ExampleConfig(config.get_example_json_path())
    if example_config.get_lifecycle_type() == LifecycleType.RDP:
        generationStep.add_step(SetupRDPConfigurationStep(config))
    elif example_config.get_lifecycle_type() == LifecycleType.PRODUCT_STATE:
        generationStep.add_step(SetupProductStateConfigurationStep(config))
        if config.lifecycle_config.get_da_certificates_supported():
            generationStep.add_step(DATypeSelection(config))
        generationStep.add_step(DAConfig(config))
    generationStep.add_step(BinaryGeneration("OEMiRoT boot binary",
                            oemirot_config.get_build_binary_path()))
    appli_config = AppliProjectConfig(config.get_appli_ini_path())
    generationStep.add_step(BinaryGeneration("Application image", appli_config.get_image_binary_path("provisioning")))
    memory_config = OEMIROT_VARIANT.memory_config_cls(
        config.get_memory_config_ini_path(), example_config)
    appli_data_nb = int(memory_config.get_data_image_number(), 16)
    if appli_data_nb > 0:
        generationStep.add_step(SetupAppliDataConfigurationStep(config))
    return generationStep


def SetupAppliDataConfigurationStep(config: OEMiRoTProvisioningConfig) -> Step:
    """
    Set up the Appli Data configuration and generation step by adding all necessary substeps.

    Args:
        config: The configuration object containing paths and settings.

    Returns:
        Step: The fully configured Appli Data configuration step.
    """
    appliDataStep = AppliDataStep()
    appliDataStep.add_step(AppliDataConfig("provisioning", config))
    appliDataStep.add_step(AppliDataConfig("fwu", config))
    return appliDataStep


def SetupRDPConfigurationStep(config: OEMiRoTProvisioningConfig) -> Step:
    """
    Set up the RDP configuration step by adding all necessary substeps.

    Args:
        config: The configuration object containing paths and settings.

    Returns:
        Step: The fully configured RDP configuration step.
    """
    rdpConfigStep = RDPConfigurationStep()
    rdpConfigStep.add_step(RDPKeyUpdate("Transition RDP bs key file", config))
    rdpConfigStep.add_step(RDPKeyUpdate("Regression RDP key file", config))
    rdpConfigStep.add_step(RDPSelection("min", config))
    rdpConfigStep.add_step(RDPSelection("final", config))
    return rdpConfigStep

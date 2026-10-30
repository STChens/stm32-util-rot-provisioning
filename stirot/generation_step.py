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
from helper.common.hxml import extract_output_file_path, update_xml_value_by_title, update_xml_value_by_name
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
from helper.config.stirot.appli_project import AppliProjectConfig
from helper.config.stirot.provisioning import STiRoTProvisioningConfig
from helper.config.stirot.flash_layout import STiRoTFlashLayout
from helper.config.variant import STIROT_VARIANT
from helper.config.example import ExampleConfig
from helper.exception.rot_exception import RoTFatalError, RoTValueError
logger = logging.getLogger()

# Substeps for the key configuration process
stirot_configuration_substeps = {
    "stirot_config":
    {
        "name": "STiRoT Configuration",
        "texts": [
            {"message": "From TrustedPackageCreator (OBKey/Data Generation tab in Secure panel)"},
            {"message": "Select {stirot_config_xml} as the configuration file"},
            {"message": "Update the configuration (if/as needed) then generate the {stirot_config_output_path} file"}
        ],
        "wait_for_input": True,
        "skip_if_auto": False,
        "process": bin_log["processing"],
        "success": bin_log["success"],
    },
}


class STiRoTConfigurationStep(Step):
    """
    Represents the key update substep in the generation process.

    Args:
        config: The configuration object containing paths and settings.
    """

    def __init__(self, config: STiRoTProvisioningConfig):
        super().__init__(stirot_configuration_substeps["stirot_config"])
        self.stirot_config_xml = config.get_stirot_config_xml_path()
        self.log_param = {'stirot_config_xml': self.stirot_config_xml,
                          'stirot_config_output_path': extract_output_file_path(self.stirot_config_xml)}
        self.tpc = TPC(Tools_Config(config.get_tools_bin_env_name()))
        self.example_config = ExampleConfig(config.get_example_json_path())
        self.flash_layout = STiRoTFlashLayout(self.example_config,
                                              STIROT_VARIANT.memory_config_cls(
                                                  config.get_memory_config_ini_path(), self.example_config))
        self.base = int(self.example_config.get_memory()["base"], 16)
        self.config = config

    def _stirot_xml_update(self):
        nb_image = hex(self.flash_layout.get_flash_layout("DATA_IMAGE_NUMBER") + 1)
        app_installation_offset = hex(self.flash_layout.get_flash_layout("FLASH_PRIMARY_APP_SLOT_OFFSET"))
        app_download_offset = hex(self.flash_layout.get_flash_layout("FLASH_SECONDARY_APP_SLOT_OFFSET"))
        app_size = hex(self.flash_layout.get_flash_layout("FLASH_PRIMARY_APP_SLOT_SIZE"))
        data_installation_offset = hex(self.flash_layout.get_flash_layout("FLASH_PRIMARY_DATA_SLOT_OFFSET"))
        data_download_offset = hex(self.flash_layout.get_flash_layout("FLASH_SECONDARY_DATA_SLOT_OFFSET"))
        data_installation_size = hex(self.flash_layout.get_flash_layout("FLASH_PRIMARY_DATA_SLOT_SIZE"))
        data_download_size = hex(self.flash_layout.get_flash_layout("FLASH_SECONDARY_DATA_SLOT_SIZE"))
        min_product_state = self.config.lifecycle_config.get_product_state("min")
        product_state_value = self.config.lifecycle_config.get_stirot_product_state_value(min_product_state)

        update_xml_value_by_name(self.stirot_config_xml, "List", "Number of images", "Value", nb_image)
        update_xml_value_by_name(self.stirot_config_xml, "Data",
                                 "Application image installation slot offset", "Value", app_installation_offset)
        update_xml_value_by_name(self.stirot_config_xml, "Data",
                                 "Application image download slot offset", "Value", app_download_offset)
        update_xml_value_by_name(self.stirot_config_xml, "Data", "Application image slot size", "Value", app_size)
        update_xml_value_by_name(self.stirot_config_xml, "Data",
                                 "Data image installation slot offset in HDPL2 OBKeys", "Value", data_installation_offset)
        update_xml_value_by_name(self.stirot_config_xml, "Data",
                                 "Data image download slot offset", "Value", data_download_offset)
        update_xml_value_by_name(self.stirot_config_xml, "Data",
                                 "Data image installation slot size in HDPL2 OBKeys", "Value", data_installation_size)
        update_xml_value_by_name(self.stirot_config_xml, "Data",
                                 "Data image download slot size", "Value", data_download_size)
        update_xml_value_by_name(self.stirot_config_xml, "Data",
                                 "Size of the secure area inside the application image installation slot", "Value", app_size)
        update_xml_value_by_name(self.stirot_config_xml, "List",
                                 "Product state minimal allowed", "Value", product_state_value)

    def process_step(self):
        self._stirot_xml_update()
        self.tpc.gen_obk(self.stirot_config_xml)


class AppliDataConfig(Step):
    """
    Represents the appli data configuration and generation substep.

    Args:
        config: The configuration object containing paths and settings.
    """

    def __init__(self, appli_data_xml_type: str, config: STiRoTProvisioningConfig):
        super().__init__(appli_data_configuration_substeps["appli_data_config"])
        self.stirot_config_xml = config.get_stirot_config_xml_path()
        self.appli_data_bin_xml = config.get_appli_data_xml_path(appli_data_xml_type)
        self.appli_data_obk_xml = config.get_appli_data_obk_xml_path()
        self.appli_data_type = appli_data_xml_type
        self.appli_data_output_bin_path = extract_output_file_path(self.appli_data_bin_xml)
        self.log_param = {
            'appli_data_xml_type': self.appli_data_type,
            'appli_data_xml': self.appli_data_bin_xml,
            'appli_data_output_bin_path': self.appli_data_output_bin_path}
        self.tpc = TPC(Tools_Config(config.get_tools_bin_env_name()))
        self.example_config = ExampleConfig(config.get_example_json_path())
        self.flash_layout = STiRoTFlashLayout(self.example_config,
                                              STIROT_VARIANT.memory_config_cls(
                                                  config.get_memory_config_ini_path(), self.example_config))

    def _data_xml_update(self):
        if self.appli_data_type == "provisioning":
            data_offset = hex(self.flash_layout.get_flash_layout("DATA_OBK_ADDRESS"))
            update_xml_value_by_title(self.appli_data_obk_xml, "Info",
                                      "STiRoT data OBK HDPL2", "ObDestAddress", data_offset)
            rel_path_output_in_image_xml = os.path.relpath(
                self.appli_data_output_bin_path, os.path.dirname(self.appli_data_obk_xml))
            update_xml_value_by_name(self.appli_data_obk_xml, "File", "Data init image",
                                     "Value", rel_path_output_in_image_xml)

        rel_path_in_image_xml = os.path.relpath(
            self.stirot_config_xml, os.path.dirname(self.appli_data_bin_xml))
        update_xml_value_by_title(self.appli_data_bin_xml, "GlobalParam",
                                  "Data image generation", "LinkedXML", rel_path_in_image_xml)

    def process_step(self):
        self._data_xml_update()
        self.tpc.gen_image(self.appli_data_bin_xml)
        if self.appli_data_type == "provisioning":
            self.tpc.gen_obk(self.appli_data_obk_xml)


def SetupGenerationStep(config: STiRoTProvisioningConfig) -> Step:
    """
    Set up the generation step by adding all necessary substeps.

    Args:
        config: The configuration object containing paths and settings.

    Returns:
        Step: The fully configured generation step.
    """
    generationStep = GenerationStep()

    def _flash_layout_factory():
        ec = ExampleConfig(config.get_example_json_path())
        return STiRoTFlashLayout(
            ec,
            STIROT_VARIANT.memory_config_cls(config.get_memory_config_ini_path(), ec))

    memoryConfigStep = UserMemoryConfigurationStep(
        config.get_memory_config_ini_path(), flash_layout_factory=_flash_layout_factory)
    generationStep.add_step(memoryConfigStep)
    product_state_step = SetupProductStateConfigurationStep(config)
    generationStep.add_step(product_state_step)
    generationStep.add_step(DATypeSelection(config))
    generationStep.add_step(DAConfig(config))
    stirot_config_step = STiRoTConfigurationStep(config)
    generationStep.add_step(stirot_config_step)
    appli_config = AppliProjectConfig(config.get_appli_ini_path())
    generationStep.add_step(BinaryGeneration("Application image", appli_config.get_image_binary_path("provisioning")))
    memory_config = STIROT_VARIANT.memory_config_cls(
        config.get_memory_config_ini_path(), ExampleConfig(config.get_example_json_path()))
    appli_data_nb = int(memory_config.get_data_image_number(), 16)
    if appli_data_nb > 0:
        generationStep.add_step(SetupAppliDataConfigurationStep(config))
    return generationStep


def SetupAppliDataConfigurationStep(config: STiRoTProvisioningConfig) -> Step:
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

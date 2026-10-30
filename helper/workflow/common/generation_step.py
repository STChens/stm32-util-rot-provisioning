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

from helper.common.hxml import extract_output_file_path
from helper.workflow.step import Step
from helper.exception.rot_exception import RoTValueError
from helper.config.product_state_lifecycle import DAType
from helper.tools.tpc import TPC
from helper.tools.tools_config import Tools_Config

logger = logging.getLogger()

STATIC_CONFIG_WARNING = (
    "Memory config is static. Provisioning will use the default configuration."
)

# Metadata for the overall generation step
generation_step = {
    "id": "generation",
    "name": "Generation",
    "wait_for_input": False,
    "success": "Successful generation",
    "skip_if_auto": False
}

# Log messages for binary generation
bin_log = {
    "processing": "Processing xml file ...",
    "success": "Successful file generation"
}

# Substeps for the generation process
generation_substeps = {
    "bin_generation": {
        "name": "{name} generation",
        "texts": [{"message": "Build the {name} ({path}) and continue"}],
        "skip_if_auto": True,
    },
}

# Substeps for the user memory configuration process
user_memory_config_substep = {
    "user_memory_config": {
        "name": "User Memory Configuration",
        "texts": [{"message": "Check the memory configuration in {path}"}],
        "questions": {
            "message": "Is this user memory configuration correct ? ",
            "options": ["Yes", "No"]
        },
        "wait_for_input": False,
        "skip_if_auto": True,
    }
}

# Substeps for the generation process
appli_data_step = {
    "id": "appli_data",
    "name": "Appli data generation",
    "wait_for_input": False,
    "success": "Successful appli data generation",
    "skip_if_auto": False
}

# Substeps for the data configuration process
appli_data_configuration_substeps = {
    "appli_data_config":
    {
        "name": "Appli Data {appli_data_xml_type} configuration",
        "texts": [
            {
                "message": "From TrustedPackageCreator (Image Gen tab in Secure panel)"
            },
            {
                "message": "Select {appli_data_xml} as the configuration file"
            },
            {
                "message": "Update the configuration (if/as needed) then generate the {appli_data_output_bin_path} file"
            }
        ],
        "process": bin_log["processing"],
        "success": bin_log["success"],
    },
}

# Substeps for the product state configuration process
product_state_configuration_substeps = {
    "product_state_configuration": {
        "id": "product_state_configuration",
        "name": "Product State Configuration",
        "wait_for_input": False,
        "success": "Successful product state configuration",
        "skip_if_auto": True,
    },
    "product_state_selection": {
        "name": "{name} Product State selection",
        "texts": [{"message": "Updating the {name} product state ({path})"}],
        "questions": {
            "message": "Select the {name} product state: ",
            # Filled dynamically with available product states from the configuration
            "options": []
        },
        "skip_if_auto": True,
        "wait_for_input": False,
        "success": "Successful product state selection",
    },
}


da_configuration_substeps = {
    "da_config_certificates":
    {
        "name": "DA Configuration",
        "texts": [
            {"message": "From TrustedPackageCreator (OBKey/Data Generation tab in Security panel)"},
            {"message": "Select {da_config_xml} as the configuration file"},
            {"message": "Select or regenerate key and configure the permission (if/as needed) then generate the {da_config_output_path} file"},
            {"message": "Default keys must NOT be used in a product. Make sure to regenerate your own keys !", "type": "warning"},
            {"message": "Generate the certificate(s) needed from corresponding keys (if/as needed) from TrustedPackageCreator (Certificate Generation tab in Debug Auth panel)", "type": "warning"},
        ],
        "wait_for_input": True,
        "skip_if_auto": False,
        "process": bin_log["processing"],
        "success": bin_log["success"],
    },
    "da_config_password":
    {
        "name": "DA Configuration",
        "texts": [
            {"message": "From TrustedPackageCreator (OBKey/Data Generation tab in Security panel)"},
            {"message": "Select {da_config_xml} as the configuration file"},
            {"message": "Update the password (if/as needed) then generate the {da_config_output_path} file"},
            {"message": "The default password must NOT be used in a product. Make sure to set your own password !", "type": "warning"},
        ],
        "wait_for_input": True,
        "skip_if_auto": False,
        "process": bin_log["processing"],
        "success": bin_log["success"],
    },
}


da_type_selection_substep = {
    "da_type_selection": {
        "name": "DA authentication mode selection",
        "texts": [{"message": "Updating the DA authentication mode ({path})"}],
        "questions": {
            "message": "Select the DA authentication mode: ",
            "options": [da_type.value for da_type in DAType]
        },
        "skip_if_auto": True,
        "wait_for_input": False,
        "success": "Successful DA authentication mode selection",
    },
}


class GenerationStep(Step):
    """
    Represents the main generation step in the workflow.
    """

    def __init__(self):
        super().__init__(generation_step)
        self.static_config = False

    def set_static_config(self, static_config: bool) -> None:
        """Set whether the generation uses the fixed static configuration."""
        self.static_config = static_config

    def process_step(self):
        if self.static_config:
            logger.warning(STATIC_CONFIG_WARNING)


class BinaryGeneration(Step):
    """
    Represents the binary generation substep in the generation process.

    Args:
        name (str): The name of the binary being generated.
        bin_path (str): The path where the binary will be generated.
    """

    def __init__(self, name: str, bin_path: str):
        super().__init__(generation_substeps["bin_generation"])
        self.log_param = {'name': name, 'path': bin_path}

    def process_step(self):
        pass


class UserMemoryConfigurationStep(Step):
    """
    Represents the user memory configuration substep in the generation process.

    Args:
        memory_config_path (str): Path to mx_memory_config.ini.
        flash_layout_factory (callable, optional): Called after confirmation to validate
            the flash layout (e.g. appli/data slot sizes vs installation mode).
    """

    def __init__(self, memory_config_path: str, flash_layout_factory=None):
        super().__init__(user_memory_config_substep["user_memory_config"])
        self.log_param = {'path': memory_config_path}
        self.flash_layout_factory = flash_layout_factory

    def process_step(self):
        if self.choice == "No":
            raise RoTValueError(
                f"Update the memory configuration in '{self.log_param['path']}' and restart the provisioning.")
        if self.flash_layout_factory is not None:
            self.flash_layout_factory()


class AppliDataStep(Step):
    """
    Represents the appli data generation step in the workflow.
    """

    def __init__(self):
        super().__init__(appli_data_step)

    def process_step(self):
        pass


class ProductStateSelection(Step):
    """
    Represents the product state selection substep in the generation process.

    Args:
        config: The provisioning configuration object containing lifecycle settings.
    """

    def __init__(self, name: str, config):
        step_config = dict(product_state_configuration_substeps["product_state_selection"])
        # Keep the shared template unchanged when populating target-specific options.
        step_config["questions"] = dict(step_config["questions"])
        step_config["questions"]["options"] = config.lifecycle_config.get_product_state_names()
        super().__init__(step_config)
        self.name = name
        self.log_param = {'name': self.name.capitalize(), 'path': config.config_path}
        self.config = config

    def _get_question_default_candidate(self, question: dict) -> object:
        return self.config.lifecycle_config.get_product_state(self.name)

    def process_step(self):
        if self.name == "final":
            self._compare_final_with_min_product_states()
        self.config.lifecycle_config.set_product_state(self.name, self.choice)

    def _compare_final_with_min_product_states(self) -> None:
        lifecycle_config = self.config.lifecycle_config
        min_state = lifecycle_config.get_product_state("min")
        final_order = lifecycle_config.get_product_state_order(self.choice)
        min_order = lifecycle_config.get_product_state_order(min_state)
        if final_order < min_order:
            raise RoTValueError(
                f"Final product state '{self.choice}' cannot be lower than minimum product state ('{min_state}').")


class ProductStateConfigurationStep(Step):
    """
    Represents the product state configuration step in the workflow.
    """

    def __init__(self):
        super().__init__(product_state_configuration_substeps["product_state_configuration"])

    def process_step(self):
        pass


class DATypeSelection(Step):
    """Represents the DA authentication mode selection substep."""

    def __init__(self, config):
        super().__init__(da_type_selection_substep["da_type_selection"])
        self.config = config
        self.log_param = {'path': config.config_path}

    def _get_question_default_candidate(self, question: dict) -> object:
        return self.config.lifecycle_config.get_da_type()

    def check_skip(self) -> bool:
        return self.config.lifecycle_config.is_open_product_state(
            self.config.lifecycle_config.get_product_state("final"))

    def process_step(self):
        self.config.lifecycle_config.set_da_type(self.choice)


def SetupProductStateConfigurationStep(config) -> Step:
    """
    Set up the Product State configuration selections.
    """
    product_state_config_step = ProductStateConfigurationStep()
    product_state_config_step.add_step(ProductStateSelection("min", config))
    product_state_config_step.add_step(ProductStateSelection("final", config))
    return product_state_config_step


class DAConfig(Step):
    """
    Represents the debug authentication configuration and generation substep.

    Args:
        config: The configuration object containing paths and settings.
    """

    def __init__(self, config):
        self.config = config
        self._load_config()

    def _load_config(self):
        da_type = self.config.lifecycle_config.get_da_type()
        self.da_config_xml = self.config.lifecycle_config.get_da_config_xml_path()
        if da_type == DAType.PASSWORD:
            step_config = da_configuration_substeps["da_config_password"]
        elif da_type == DAType.CERTIFICATES:
            step_config = da_configuration_substeps["da_config_certificates"]
        else:
            raise RoTValueError(f"Unsupported DA type: {da_type}")
        if not hasattr(self, "step"):
            super().__init__(step_config)
        else:
            self.step = step_config
        self.log_param = {
            'da_config_xml': self.da_config_xml,
            'da_config_output_path': extract_output_file_path(self.da_config_xml),
        }
        self.tpc = TPC(Tools_Config(self.config.get_tools_bin_env_name()))

    def run_step(self) -> None:
        self._load_config()
        super().run_step()

    def check_skip(self) -> bool:
        return self.config.lifecycle_config.is_open_product_state(
            self.config.lifecycle_config.get_product_state("final"))

    def process_step(self):
        self.tpc.gen_obk(self.da_config_xml)

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

from helper.config.base import BaseConfig
from helper.config.example import ExampleConfig, LifecycleType
from helper.config.memory_base import BaseMemoryConfig
from helper.config.rdp_lifecycle import RDPLifecycleConfig
from helper.config.product_state_lifecycle import DAType, ProductStateLifecycleConfig
from helper.exception.rot_exception import RoTUnexpectedError


class BaseProvisioningConfig(BaseConfig):
    """
    Base class for provisioning configuration files shared by OEMiRoT and STiRoT.
    """

    def __init__(self, config_path: str):
        super().__init__(config_path)

    def _load_common_config(self):
        self.tools_bin_env_name = self.get_config_value('provisioning', 'tools_bin_env_name')
        self.rot_provisioning_path = self.get_absolute_path_from_config('provisioning', 'path')
        self.example_json_path = self.get_absolute_path_from_config('provisioning', 'example_json_path')
        self.memory_config_ini_path = self.get_absolute_path_from_config('provisioning', 'memory_config_ini_path')
        self.appli_ini_path = self.get_absolute_path_from_config('appli_config', 'appli_ini_path')
        self.example_config = ExampleConfig(self.example_json_path)
        self.static_config = self.example_config.get_static_config()
        # Keep the stored type generic, but build the concrete variant memory config
        # so its extra fields and validations are loaded before provisioning uses it.
        self.memory_config = self._create_memory_config()
        self.lifecycle_type = self.example_config.get_lifecycle_type()

        if self.lifecycle_type == LifecycleType.RDP:
            self.lifecycle_config = RDPLifecycleConfig(
                transition_bs_key_path=self.get_absolute_path_from_config('rdp', 'transition_bs_key_path'),
                regression_rdp_key_path=self.get_absolute_path_from_config('rdp', 'regression_rdp_key_path'),
                rdp_level={"min": self.get_config_value('rdp', 'min_rdp_level'),
                           "final": self.get_config_value('rdp', 'final_rdp_level')},
                config=self.config,
                config_path=self.config_path,
                update_config_file=self._update_config_file,
            )
        elif self.lifecycle_type == LifecycleType.PRODUCT_STATE:
            self.lifecycle_config = ProductStateLifecycleConfig(
                product_state={"min": self.get_config_value('da', 'min_product_state'),
                               "final": self.get_config_value('da', 'final_product_state')},
                config=self.config,
                config_path=self.config_path,
                update_config_file=self._update_config_file,
                lifecycle=self.example_config.get_lifecycle(),
                da_certificates_supported=self.example_config.get_da_certificates_supported(),
            )
        else:
            raise RoTUnexpectedError(f"Unsupported lifecycle type {self.lifecycle_type} in provisioning config.")

        self._load_data_image_number()
        if self.data_image_number == 1:
            self.appli_data_xml_path = {"provisioning": self.get_absolute_path_from_config('appli_data_image', 'provisioning_xml_path'),
                                        "fwu": self.get_absolute_path_from_config('appli_data_image', 'fwu_xml_path')}

    def _create_memory_config(self) -> BaseMemoryConfig:
        raise RoTUnexpectedError(
            "Provisioning subclasses must implement _create_memory_config() before loading provisioning config."
        )

    def _load_data_image_number(self):
        self.data_image_number = int(self.memory_config.get_data_image_number())

    def _set_common_print_dict(self):
        self.print_config_items["Tools Environment Variable Name"] = self.tools_bin_env_name
        self.print_config_items["Example JSON Path"] = self.example_json_path
        self.print_config_items["Memory Config INI Path"] = self.memory_config_ini_path
        self.print_config_items["ROT Provisioning Path"] = self.rot_provisioning_path
        self.print_config_items["Application INI Path"] = self.appli_ini_path
        self.lifecycle_config.set_print_dict(self.print_config_items)

        if self.data_image_number == 1:
            self.print_config_items["Appli Data Provisioning XML Path"] = self.appli_data_xml_path["provisioning"]
            self.print_config_items["Appli Data FWU XML Path"] = self.appli_data_xml_path["fwu"]

    def get_tools_bin_env_name(self) -> str:
        """
        Returns the environment variable name defined in provisioning.ini.

        Returns:
            str: The environment variable name where the STM32CubeProgrammer bin folder path is stored.
        """
        return self.tools_bin_env_name

    def get_rot_provisioning_path(self) -> str:
        """
        Returns the absolute rot_provisioning path for the project.

        Returns:
            str: The absolute provisioning path.
        """
        return self.rot_provisioning_path

    def get_example_json_path(self) -> str:
        """
        Returns the absolute path to the example JSON file.

        Returns:
            str: The absolute path to the example JSON file.
        """
        return self.example_json_path

    def get_memory_config_ini_path(self) -> str:
        """
        Returns the absolute path to the memory config ini file.

        Returns:
            str: The absolute path to the memory config ini file.
        """
        return self.memory_config_ini_path

    def get_static_config(self) -> bool:
        """Returns whether the example uses a fixed static configuration."""
        return self.static_config

    def get_appli_ini_path(self) -> str:
        """
        Returns the absolute path to the application ini file.

        Returns:
            str: The path to the application ini file.
        """
        return self.appli_ini_path

    def _update_config_file(self, config: BaseConfig) -> None:
        """
        Updates the configuration file with the current settings.

        Args:
            config (BaseConfig): The configuration object to save.
        """
        with open(self.config_path, 'w') as configfile:
            config.write(configfile)

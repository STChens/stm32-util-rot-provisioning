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

from enum import Enum
import logging

from helper.common.misc import format_values_with_or
from helper.config.oemirot.memory import OEMiRoTMemoryConfig
from helper.config.provisioning_base import BaseProvisioningConfig
from helper.exception.rot_exception import RoTUnexpectedError, RoTValueError

logger = logging.getLogger()


class OEMiRoTInstallationMode(Enum):
    """
    Enumeration representing the supported OEMiRoT installation modes.

    Attributes:
        OVERWRITE (str): Install by overwriting the previous image.
        SWAP (str): Install by swapping image slots.
    """
    OVERWRITE = "overwrite"
    SWAP = "swap"


INSTALLATION_MODE_HAL_DEFINES = {
    OEMiRoTInstallationMode.OVERWRITE: "INSTALLATION_MODE_OVERWRITE",
    OEMiRoTInstallationMode.SWAP: "INSTALLATION_MODE_SWAP",
}


class OEMiRoTProvisioningConfig(BaseProvisioningConfig):
    """
    Configuration handler for the OEMiRoT provisioning workflow.

    This class extends BaseProvisioningConfig with OEMiRoT-specific paths,
    lifecycle settings, and optional application data image configuration.

    Example ini file sections (path can be relative or absolute, relative paths are resolved
    relative to the location of the ini file):

        [provisioning]
        path = /path/to/rot_provisioning
        example_json_path = /path/to/example.json
        tools_bin_env_name = STM32_PRG_PATH
        memory_config_ini_path = /path/to/mx_memory_config.ini

        [appli_config]
        appli_ini_path = path/project_appli.ini

        [appli_data_image]
        provisioning_xml_path = /path/to/appli_provisioning_data_image.xml
        fwu_xml_path = /path/to/appli_fwu_data_image.xml

        [oemirot_config]
        installation_mode = overwrite
        oemirot_ini_path = path/project_oemirot.ini
        keys_xml_path = /path/to/oemirot_keys_config.xml
        data_bin_path = /path/oemirot_nvcounters_init.bin

        #If RDP product
        [rdp]
        transition_bs_key_path = /path/transition_bs_key.bin
        regression_rdp_key_path = /path/regression_rdp_key.bin
        min_rdp_level = RDP_0
        final_rdp_level = RDP_0

        #If DA product
        [da]
        type = certificates
        final_product_state = OPEN

        [da_certificates]
        config_xml_path = /path/da_config_certificate.xml
        certificate = /path/da_certificate.pem

        [da_password]
        config_xml_path = /path/da_config_password.xml

    Methods:
        get_config_keys_xml_path() -> str:
            Returns the absolute path to the config keys xml file.
        get_config_data_path() -> str:
            Returns the absolute path to the config data binary.
        get_oemirot_installation_mode() -> OEMiRoTInstallationMode:
            Returns the OEMiROT installation mode.
        set_oemirot_installation_mode(installation_mode: OEMiRoTInstallationMode) -> None:
            Sets the OEMiROT installation mode in the provisioning configuration file.
        get_appli_ini_path() -> str:
            Returns the absolute path to the application ini file.
        get_oemirot_ini_path() -> str:
            Returns the absolute path to the OEMiROT ini file.
        get_tools_bin_env_name() -> str:
            Returns the environment variable name defined in provisioning.ini containing the path to STM32CubeProgrammer bin folder.
        get_rot_provisioning_path() -> str:
            Returns the absolute rot_provisioning path for the project.
        get_example_json_path() -> str:
            Returns the absolute path to the example JSON file.
        get_memory_config_ini_path() -> str:
            Returns the absolute path to the memory config ini file.
        get_appli_data_xml_path(image_type: str) -> str:
            Returns the absolute path to the xml of the appli data
            for the provisioning or the fwu according to the image_type parameter.

        #If RDP product
        get_transition_bs_key_path() -> str:
            Returns the absolute path to the RDP transition BS key binary file.
        get_regression_rdp_key_path() -> str:
            Returns the absolute path to the RDP regression RDP key binary file.
        get_rdp_level(type: str) -> int:
            Returns the minimum or final RDP level to be set.
        set_rdp_level(type: str, rdp_level: str):
            Sets the minimum or final RDP level to be set.

        #If DA product
        get_da_config_xml_path(self) -> str:
            Returns the absolute path to the DA configuration XML file.
        get_da_key_path(self) -> str:
            Returns the absolute path to the DA key file extracted from the DA configuration XML file.
        get_da_certificate_path(self) -> str:
            Returns the absolute path to the DA certificate file.
        get_product_state(self) -> str:
            Returns the final product state.

    """

    def _load_config(self):
        """
        This method retrieves the configuration required for the boot project:
            - The path to config keys xml file.
            - The path to config data binary.
            - The path to OEMiROT output binary.
            - The path to application configuration file.
            - The environment variable name containing the path to STM32CubeProgrammer bin folder.
            - The path to rot_provisioning directory.
            - The path to example JSON file.
            - The path to memory configuration ini file.
            - The mode of installation for OEMiROT (overwrite or swap).
            If the data image number is equal to 1, it also retrieves:
            - The path to the appli data provisioning XML file.
            - The path to the appli data fwu XML file.
            If the lifecycle type is RDP, it also retrieves:
            - The path to RDP transition BS key.
            - The path to RDP regression RDP key.
            - The minimum RDP level to be set.
            - The final RDP level to be set.
            If the lifecycle type is DA, it also retrieves:
            - The path to DA OBK file.
            - The path to DA key file.
            - The path to DA certificate file.
            - The final product state.
        """
        self._load_common_config()
        self.config_keys_xml_path = self.get_absolute_path_from_config('oemirot_config', 'keys_xml_path')
        self.config_data_path = self.get_absolute_path_from_config('oemirot_config', 'data_bin_path')
        self.oemirot_ini_path = self.get_absolute_path_from_config('oemirot_config', 'oemirot_ini_path')
        self.oemirot_installation_mode = self.get_config_value('oemirot_config', 'installation_mode').lower()
        if (self.get_static_config()
                and self.get_oemirot_installation_mode() != OEMiRoTInstallationMode.OVERWRITE):
            raise RoTValueError(
                f"Static configuration requires OEMiROT installation mode 'overwrite' in '{self.config_path}'.")

    def _create_memory_config(self) -> OEMiRoTMemoryConfig:
        return OEMiRoTMemoryConfig(self.memory_config_ini_path, self.example_config)

    def _set_print_dict(self):
        self._set_common_print_dict()
        self.print_config_items["Config Keys XML Path"] = self.config_keys_xml_path
        self.print_config_items["Config Data Path"] = self.config_data_path
        self.print_config_items["OEMiROT INI Path"] = self.oemirot_ini_path
        self.print_config_items["OEMiROT Installation Mode"] = self.oemirot_installation_mode

    def get_config_keys_xml_path(self) -> str:
        """
        Returns the absolute path to the config keys xml file.
        Returns:
            str: The path to the config keys xml file.
        """
        return self.config_keys_xml_path

    def get_config_data_path(self) -> str:
        """
        Returns the absolute path to the config data.
        Returns:
            str: The path to the config data binary file.
        """
        return self.config_data_path

    def get_oemirot_ini_path(self) -> str:
        """
        Returns the absolute path to the OEMiROT ini file.
        Returns:
            str: The path to the OEMiROT ini file.
        """
        return self.oemirot_ini_path

    def get_oemirot_installation_mode(self) -> OEMiRoTInstallationMode:
        """
        Returns the OEMiROT installation mode.

        Returns:
            OEMiRoTInstallationMode: The OEMiROT installation mode.
        Raises:
            RoTValueError: If the configured installation mode is not supported.
        """
        try:
            return OEMiRoTInstallationMode(self.oemirot_installation_mode)
        except ValueError:
            raise RoTValueError(
                f"OEMiROT installation mode '{self.oemirot_installation_mode}' set in '{self.config_path}' is not valid. "
                f"Please select {format_values_with_or(mode.value for mode in OEMiRoTInstallationMode)}."
            )

    def set_oemirot_installation_mode(self, installation_mode: OEMiRoTInstallationMode) -> None:
        """
        Sets the OEMiROT installation mode in the provisioning configuration file.

        Args:
            installation_mode (OEMiRoTInstallationMode): The OEMiROT installation mode to set.
        Raises:
            RoTValueError: If the configured installation mode is not supported.
        """
        try:
            installation_mode = OEMiRoTInstallationMode(installation_mode)
            self.config['oemirot_config']['installation_mode'] = installation_mode.value
            self._update_config_file(self.config)
            self.oemirot_installation_mode = installation_mode
        except ValueError:
            raise RoTValueError(
                f"OEMiROT installation mode '{installation_mode}' set in '{self.config_path}' is not valid. "
                f"Please select {format_values_with_or(mode.value for mode in OEMiRoTInstallationMode)}."
            )

    def get_appli_data_xml_path(self, image_type: str) -> str:
        """
        Returns the absolute path to the xml of the appli data
        for the provisioning or the fwu depending on the type parameter.

        Args:
            image_type (str): The type of the appli data image xml to retrieve.
        Returns:
            str: The absolute path to the xml of the appli data provisioning.
        Raises:
            RoTUnexpectedError: If the data image number is not equal to 1.
        """
        if self.data_image_number != 1:
            raise RoTUnexpectedError("Appli Data XMLs are only available when data image number is equal to 1.")
        return self.appli_data_xml_path[image_type]

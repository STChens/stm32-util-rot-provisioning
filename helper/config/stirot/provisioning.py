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

from helper.config.stirot.memory import STiRoTMemoryConfig
from helper.config.provisioning_base import BaseProvisioningConfig
from helper.exception.rot_exception import RoTUnexpectedError

logger = logging.getLogger()


class STiRoTProvisioningConfig(BaseProvisioningConfig):
    """
    STiRoT provisioning configuration handler.
    """

    def _load_config(self):
        """
        Retrieves the configuration required for the STiRoT provisioning workflow.
        """
        self._load_common_config()
        if self.data_image_number == 1:
            self.appli_data_obk_xml_path = self.get_absolute_path_from_config(
                'stirot_config', 'appli_data_xml_obk_path')
        self.stirot_config_xml_path = self.get_absolute_path_from_config('stirot_config', 'config_xml_path')
        self.stirot_data_path = self.get_absolute_path_from_config('stirot_config', 'data_config_path')

    def _create_memory_config(self) -> STiRoTMemoryConfig:
        return STiRoTMemoryConfig(self.memory_config_ini_path, self.example_config)

    def _set_print_dict(self):
        self._set_common_print_dict()
        if self.data_image_number == 1:
            self.print_config_items["Appli Data OBK XML Path"] = self.appli_data_obk_xml_path
        self.print_config_items["STiRoT Config XML Path"] = self.stirot_config_xml_path
        self.print_config_items["STiRoT Data OBK Path"] = self.stirot_data_path

    def get_stirot_config_xml_path(self) -> str:
        """
        Returns the absolute path to the STiRoT Config XML file.

        Returns:
            str: The absolute path to the STiRoT Config XML file.
        """
        return self.stirot_config_xml_path

    def get_stirot_data_path(self) -> str:
        """
        Returns the absolute path to the STiRoT Data OBK file.

        Returns:
            str: The absolute path to the STiRoT Data OBK file.
        """
        return self.stirot_data_path

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

    def get_appli_data_obk_xml_path(self) -> str:
        """
        Returns the absolute path to the xml of the appli data obk
        which is flashed during the OBK programming substep.

        Returns:
            str: The absolute path to the xml of the appli data obk.
        Raises:
            RoTUnexpectedError: If the data image number is not equal to 1.
        """
        if self.data_image_number != 1:
            raise RoTUnexpectedError("Appli Data OBK XML is only available when data image number is equal to 1.")
        return self.appli_data_obk_xml_path

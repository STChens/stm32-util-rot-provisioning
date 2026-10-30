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

from helper.config.memory_base import BaseMemoryConfig
import logging

from helper.config.example import ExampleConfig
from helper.exception.rot_exception import RoTValueError
logger = logging.getLogger()


class STiRoTMemoryConfig(BaseMemoryConfig):
    """
    STiRoTMemoryConfig is a configuration handler for user memory settings for STiRoT example.
    This class extends BaseConfig to provide specialized configuration retrieval
    and management for memory configurations.

    Example ini file sections:

        [image_number]
        data_image = 0

        [partition_size]
        app_size = 0x100000
        data_size = 0x100

        [partition_offset]
        app_installation_offset = 0x0
        app_download_offset = 0x300000
        data_download_offset = 0x2FE000

    Methods:
        get_app_installation_offset() -> int:
            Returns the application installation offset.
        get_app_download_offset() -> int:
            Returns the application download offset.
        get_data_download_offset() -> int:
            Returns the data download offset.
    """

    def __init__(self, config_path: str, example_config: ExampleConfig):
        super().__init__(config_path, example_config)

    def _load_variant_config(self):
        """
        Loads STiRoT-specific config fields:
            - The application installation offset.
            - The application download offset.
            - The data download offset.
        """
        self.app_installation_offset = self.get_config_value('partition_offset', 'app_installation_offset')
        self.app_download_offset = self.get_config_value('partition_offset', 'app_download_offset')
        self.data_download_offset = self.get_config_value('partition_offset', 'data_download_offset')

    def _validate_variant_config(self) -> None:
        """
        Validates STiRoT-specific config fields.
        """

        self._validate_offset(self.app_installation_offset)
        self._validate_offset(self.app_download_offset)
        if self.data_image_nb == "1":
            self._validate_offset(self.data_download_offset)

    def _set_variant_print_dict(self) -> None:
        self.print_config_items["Application Installation Offset"] = self.app_installation_offset
        self.print_config_items["Application Download Offset"] = self.app_download_offset
        self.print_config_items["Data Download Offset"] = self.data_download_offset

    def _validate_offset(self, offset: str) -> None:
        """
        Validates the offset configuration parameter. It must be aligned to memory block size and be within total memory size.

        Arguments:
            offset (str): The offset to validate.

        Raises:
            RoTValueError: If the offset is invalid.
        """
        memory_total_size = int(self.memory["total_size"], 16)
        offset_int = int(offset, 16)
        if (offset_int % self.memory_block_size != 0):
            raise RoTValueError(
                f"Offset ({offset}) is not aligned to memory block size ({hex(self.memory_block_size)}). Please update {self.config_path}.")
        if (offset_int >= memory_total_size):
            raise RoTValueError(
                f"Offset ({offset}) cannot be greater or equal than memory total size ({hex(memory_total_size)}). Please update {self.config_path}.")

    def get_app_installation_offset(self) -> int:
        """
        Returns the application installation offset from the configuration.

        Returns:
            int: The application installation offset.
        """
        return self.app_installation_offset

    def get_app_download_offset(self) -> int:
        """
        Returns the application download offset from the configuration.

        Returns:
            int: The application download offset.
        """
        return self.app_download_offset

    def get_data_download_offset(self) -> int:
        """
        Returns the data download offset from the configuration.

        Returns:
            int: The data download offset.
        """
        return self.data_download_offset

    def _validate_data_size(self) -> None:
        """
        Validates the data size configuration parameter.

        Raises:
            RoTValueError: If the data size is invalid.
        """
        obk = self.example_config.get_obk()
        obk_size_max = int(obk["hdpl2_size"], 16) - int(obk["reserved"], 16)
        obk_prog_size = int(obk["prog_size"], 16)
        data_size_int = int(self.data_size, 16)
        if not data_size_int:
            raise RoTValueError(
                f"Data size is zero. Please update {self.config_path}.")
        if (data_size_int % obk_prog_size != 0):
            raise RoTValueError(
                f"Data size ({self.data_size}) is not aligned to OBK program size ({hex(obk_prog_size)}). Please update {self.config_path}.")
        if data_size_int > obk_size_max:
            raise RoTValueError(
                f"Data size ({self.data_size}) exceeds maximum allowed OBK size ({hex(obk_size_max)}). Please update {self.config_path}.")

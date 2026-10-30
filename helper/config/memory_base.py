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
import logging

from helper.config.example import ExampleConfig
from helper.exception.rot_exception import RoTNotImplementedError, RoTValueError
logger = logging.getLogger()


class BaseMemoryConfig(BaseConfig):
    """
    BaseMemoryConfig is a configuration handler for user memory settings.
    This class extends BaseConfig to provide specialized configuration retrieval
    and management for memory configurations.

    Example ini file sections:

        [image_number]
        data_image = 0

        [partition_size]
        app_size = 0xC0000
        data_size = 0x2000

    Methods:
        get_data_image_number() -> int:
            Returns the data image number.
        get_app_size() -> int:
            Returns the application size.
        get_data_size() -> int:
            Returns the data size.
    """

    def __init__(self, config_path: str, example_config: ExampleConfig):
        self.example_config = example_config
        self.memory = self.example_config.get_memory()
        self.memory_block_size = int(self.memory["block_size"], 16)
        super().__init__(config_path)

    def _load_config(self):
        """
        Loads only the base memory configuration (data image, app size, data size).
        """
        self.data_image_nb = self.get_config_value('image_number', 'data_image')
        self.app_size = self.get_config_value('partition_size', 'app_size')
        self.data_size = self.get_config_value('partition_size', 'data_size')
        self._load_variant_config()
        self._validate_config()

    def _set_print_dict(self):
        self.print_config_items["Data Image Number"] = self.data_image_nb
        self.print_config_items["Application Size"] = self.app_size
        self.print_config_items["Data Size"] = self.data_size
        self._set_variant_print_dict()

    def get_data_image_number(self) -> int:
        """
        Returns the number of data image from the configuration.

        Returns:
            int: The data image number.
        """
        return self.data_image_nb

    def get_app_size(self) -> int:
        """
        Returns the application size from the configuration.

        Returns:
            int: The application size.
        """
        return self.app_size

    def get_data_size(self) -> int:
        """
        Returns the data size from the configuration.

        Returns:
            int: The data size.
        """
        return self.data_size

    def _validate_config(self) -> bool:
        """
        Validates only the base memory configuration parameters.
        """
        self._validate_data_config()
        self._validate_app_size()
        if self.data_image_nb == "1":
            self._validate_data_size()
        self._validate_variant_config()

    def _load_variant_config(self) -> None:
        """
        Loads subclass-specific configuration values.
        """
        return None

    def _set_variant_print_dict(self) -> None:
        """
        Adds subclass-specific values to the printable config dictionary.
        """
        return None

    def _validate_variant_config(self) -> None:
        """
        Validates subclass-specific configuration values.
        """
        return None

    def _validate_data_config(self) -> bool:
        """
        Validates the data memory configuration parameters.

        Raises:
            RoTValueError: If any configuration parameter is invalid.
        """
        # Checking data image
        if (self.data_image_nb != "0" and self.data_image_nb != "1"):
            raise RoTValueError(f"Data image number must be 0 or 1. Please update '{self.config_path}'.")

    def _validate_app_size(self) -> bool:
        """
        Validates the application size configuration parameter.

        Raises:
            RoTValueError: If the application size is invalid.
        """
        memory_bank_size = int(self.memory["bank_size"], 16)
        app_size_int = int(self.app_size, 16)
        if (app_size_int % self.memory_block_size != 0):
            raise RoTValueError(
                f"Application size ({self.app_size}) is not aligned to memory block size ({hex(self.memory_block_size)}). Please update {self.config_path}.")
        if (app_size_int >= memory_bank_size):
            raise RoTValueError(
                f"Application size cannot be greater or equal than memory bank size ({hex(memory_bank_size)}). Please update {self.config_path}.")

    def _validate_data_size(self) -> bool:
        """
        Validates the data size configuration parameter.

        Subclasses can override this when data size validation is variant-specific.
        """
        raise RoTNotImplementedError("Subclasses should implement this method")

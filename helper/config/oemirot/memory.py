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


class OEMiRoTMemoryConfig(BaseMemoryConfig):
    """
    OEMiRoTMemoryConfig is a configuration handler for user memory settings.
    This class extends BaseConfig to provide specialized configuration retrieval
    and management for memory configurations.

    Example ini file sections:

        [image_number]
        data_image = 0

        [partition_size]
        oemirot_size = 0x18000
        app_size = 0xC0000
        data_size = 0x2000

    Methods:
        get_oemirot_size() -> int:
            Returns the OEMiROT size.
    """

    def __init__(self, config_path: str, example_config: ExampleConfig):
        super().__init__(config_path, example_config)

    def _load_variant_config(self) -> None:
        """
        Loads OEMiRoT-specific config fields.
        """
        self.oemirot_size = self.get_config_value('partition_size', 'oemirot_size')

    def _validate_variant_config(self) -> None:
        """
        Validates OEMiRoT-specific config fields.
        """
        self._validate_oemirot_size()

    def _set_variant_print_dict(self) -> None:
        self.print_config_items["OEMiRoT Size"] = self.oemirot_size

    def get_oemirot_size(self) -> int:
        """
        Returns the OEMiRoT size from the configuration.

        Returns:
            int: The OEMiRoT size.
        """
        return self.oemirot_size

    def _validate_oemirot_size(self) -> None:
        """
        Validates the OEMiRoT size configuration parameter.
        """
        wrp_grp_size = self.memory["wrpgrp_size"]
        has_obk = self.example_config.get_board()["obk"]
        oemirot_size_int = int(self.oemirot_size, 16)
        if ((oemirot_size_int % self.memory_block_size) != 0):
            raise RoTValueError(
                f"OEMiRoT size ({self.oemirot_size}) must be a multiple of the memory block size ({hex(self.memory_block_size)}). Please update {self.config_path}.")
        if ((not has_obk) and ((oemirot_size_int + self.memory_block_size) % (wrp_grp_size * self.memory_block_size)) != 0):
            raise RoTValueError(
                f"OEMiRoT size + memory block size ({hex(oemirot_size_int + self.memory_block_size)}) must be a multiple of the memory block size * WRP group size ({hex(wrp_grp_size * self.memory_block_size)}). Please update {self.config_path}.")
        if (has_obk and (oemirot_size_int % (wrp_grp_size * self.memory_block_size)) != 0):
            raise RoTValueError(
                f"OEMiRoT size ({self.oemirot_size}) must be a multiple of the memory block size * WRP group size ({hex(wrp_grp_size * self.memory_block_size)}). Please update {self.config_path}.")

    def _validate_data_size(self) -> None:
        """
        Validates the data size configuration parameter.

        Raises:
            RoTValueError: If the data size is invalid.
        """
        data_size_int = int(self.data_size, 16)
        if not data_size_int:
            raise RoTValueError(
                f"Data size is zero. Please update {self.config_path}.")
        if (data_size_int % self.memory_block_size != 0):
            raise RoTValueError(
                f"Data size ({self.data_size}) is not aligned to memory block size ({hex(self.memory_block_size)}). Please update {self.config_path}.")

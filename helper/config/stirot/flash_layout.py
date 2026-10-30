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

from helper.config.flash_layout_base import BaseFlashLayout
from helper.config.example import ExampleConfig
from helper.exception.rot_exception import RoTNotImplementedError, RoTValueError
from helper.config.stirot.memory import STiRoTMemoryConfig


class STiRoTFlashLayout(BaseFlashLayout):
    """
    FlashLayout is a class that calculates and manages the flash memory layout for a specific hardware configuration.

    Methods:
        _calculate_flash_layout() -> dict:
            Calculates all flash layout defines and returns them as a dictionary.
        _validate_flash_layout() -> None:
            Validates the computed flash layout to ensure memory regions do not exceed total available memory.
    Raises:
        RoTNotImplementedError: If the isolation flag is activated.
        RoTValueError: If the computed flash layout exceeds the total memory size.
    """

    def __init__(self, example_config: ExampleConfig, memory_config: STiRoTMemoryConfig):
        obk = example_config.get_obk()
        self.obk_base = int(obk["base"], 16)
        self.obk_hdpl2_offset = int(obk["hdpl2_offset"], 16)
        self.memory_total_size = int(example_config.get_memory()["total_size"], 16)
        super().__init__(example_config, memory_config)
        self.memory_config = memory_config

    def _calculate_flash_layout(self) -> dict:
        """
        Calculates the flash layout definitions for memory regions.
        This method computes the following flash layout definitions:
        - FLASH_PRIMARY_DATA_SLOT_OFFSET: Offset for the primary data slot.
        - FLASH_PRIMARY_DATA_SLOT_SIZE: Size of the primary data slot.
        - FLASH_PRIMARY_APP_SLOT_OFFSET: Offset for the primary application slot.
        - FLASH_PRIMARY_APP_SLOT_SIZE: Size of the primary application slot.
        - FLASH_SECONDARY_APP_SLOT_OFFSET: Offset for the secondary application slot.
        - FLASH_SECONDARY_APP_SLOT_SIZE: Size of the secondary application slot.
        - FLASH_SECONDARY_DATA_SLOT_OFFSET: Offset for the secondary data slot.
        - FLASH_SECONDARY_DATA_SLOT_SIZE: Size of the secondary data slot.
        - DATA_IMAGE_NUMBER: Number of data images.
        - FLASH_SECONDARY_APP_INSTALL_REQ_OFFSET: Offset for the secondary application install request.
        - FLASH_SECONDARY_DATA_INSTALL_REQ_OFFSET: Offset for the secondary data install request.
        - FLASH_PRIMARY_APP_VERSION_OFFSET: Offset for the primary application version.
        - FLASH_PRIMARY_DATA_VERSION_OFFSET: Offset for the primary data version.

        Returns:
            dict: A dictionary containing all calculated flash layout definitions and their corresponding values.
        """
        flash_layout = {}

        # Calculate flash layout definitions
        # Calculate the size and offset of application slots
        primary_app_slot_offset = int(self.memory_config.get_app_installation_offset(), 16)
        secondary_app_slot_offset = int(self.memory_config.get_app_download_offset(), 16)
        app_slot_size = self.app_size

        secondary_app_install_req_offset = self._compute_install_req_offset(
            secondary_app_slot_offset, app_slot_size, self.img_install_req_size
        )
        primary_app_version_offset = primary_app_slot_offset + self.img_version_offset

        # Calculate the size and offset of data slots
        primary_data_slot_offset = 0
        if self.nb_data_image == 0:
            secondary_data_slot_offset = 0
            primary_data_slot_size = 0
            secondary_data_slot_size = 0
            secondary_data_install_req_offset = 0
            primary_data_version_offset = 0
        else:
            secondary_data_slot_offset = int(self.memory_config.get_data_download_offset(), 16)
            primary_data_slot_size = self._compute_data_size(self.data_size, self.nb_data_image)
            secondary_data_slot_size = self.memory_block_size
            secondary_data_install_req_offset = self._compute_install_req_offset(
                secondary_data_slot_offset, secondary_data_slot_size, self.img_install_req_size
            )
            primary_data_version_offset = primary_data_slot_offset + self.img_version_offset

        rom_appli_address = self.base + primary_app_slot_offset + \
            self.vtor_alignment

        # Fill the dictionary with calculated flash layout definitions
        flash_layout["FLASH_PRIMARY_DATA_SLOT_OFFSET"] = primary_data_slot_offset
        flash_layout["FLASH_PRIMARY_DATA_SLOT_SIZE"] = primary_data_slot_size
        flash_layout["FLASH_PRIMARY_APP_SLOT_OFFSET"] = primary_app_slot_offset
        flash_layout["FLASH_PRIMARY_APP_SLOT_SIZE"] = app_slot_size
        flash_layout["FLASH_SECONDARY_APP_SLOT_OFFSET"] = secondary_app_slot_offset
        flash_layout["FLASH_SECONDARY_APP_SLOT_SIZE"] = app_slot_size
        flash_layout["FLASH_SECONDARY_DATA_SLOT_OFFSET"] = secondary_data_slot_offset
        flash_layout["FLASH_SECONDARY_DATA_SLOT_SIZE"] = secondary_data_slot_size

        flash_layout["DATA_IMAGE_NUMBER"] = self.nb_data_image
        flash_layout["FLASH_SECONDARY_APP_INSTALL_REQ_OFFSET"] = secondary_app_install_req_offset
        flash_layout["FLASH_SECONDARY_DATA_INSTALL_REQ_OFFSET"] = secondary_data_install_req_offset
        flash_layout["FLASH_PRIMARY_APP_VERSION_OFFSET"] = primary_app_version_offset
        flash_layout["FLASH_PRIMARY_DATA_VERSION_OFFSET"] = primary_data_version_offset

        # For application
        flash_layout["ROM_APPLI_ADDRESS"] = rom_appli_address
        flash_layout["ROM_APPLI_SIZE"] = app_slot_size - self.vtor_alignment
        flash_layout["ROM_APPLI_HEX_FORMAT"] = self.base + primary_app_slot_offset

        # For application data
        flash_layout["DATA_OBK_ADDRESS"] = self.obk_base + self.obk_hdpl2_offset + primary_data_slot_offset

        if (self.isolation):
            raise RoTNotImplementedError("Isolation mode is not supported yet.")

        return flash_layout

    def _validate_flash_layout(self) -> None:
        """
        Validates the computed STiRoT flash layout.

        The application installation and download areas must stay within the
        total memory range. Download areas are also checked against the
        application installation area, while overlap between download areas
        themselves remains allowed.

        Raises:
            RoTValueError: If an area exceeds total memory or overlaps the
                application installation area.
        """
        def raise_if_exceeding_total_memory(offset: int, size: int, area_name: str) -> None:
            if (offset + size) > self.memory_total_size:
                raise RoTValueError(
                    f"{area_name} (offset: {hex(offset)}, size: {hex(size)}) exceeds total memory size ({hex(self.memory_total_size)}). Please update the configuration.")

        def raise_if_overlapping_installation(offset: int, offset_name: str) -> None:
            if app_installation_offset <= offset < app_installation_end:
                raise RoTValueError(
                    f"{offset_name} ({offset}) overlaps with application installation area. Please update {self.memory_config.config_path}.")

        app_installation_offset = self.flash_layout["FLASH_PRIMARY_APP_SLOT_OFFSET"]
        app_download_offset = self.flash_layout["FLASH_SECONDARY_APP_SLOT_OFFSET"]
        app_size = self.flash_layout["FLASH_PRIMARY_APP_SLOT_SIZE"]
        app_installation_end = app_installation_offset + app_size

        raise_if_exceeding_total_memory(app_installation_offset, app_size, "Application installation area")
        raise_if_exceeding_total_memory(app_download_offset, app_size, "Application download area")
        raise_if_overlapping_installation(app_download_offset, "Application download offset")
        if self.nb_data_image == 1:
            data_download_offset = self.flash_layout["FLASH_SECONDARY_DATA_SLOT_OFFSET"]
            raise_if_overlapping_installation(data_download_offset, "Data download offset")

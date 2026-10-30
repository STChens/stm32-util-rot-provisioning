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

from helper.common.log import ROT_Logger
from helper.config.variant import OEMIROT_VARIANT
from helper.config.oemirot.project import OEMiRoTProjectConfig
from helper.project.base import BaseProject
from helper.config.oemirot.flash_layout import OEMiRoTFlashLayout
from helper.config.oemirot.provisioning import INSTALLATION_MODE_HAL_DEFINES
from helper.config.rdp_lifecycle import RDP_LEVEL_HAL_DEFINES
from helper.config.example import LifecycleType
from helper.common.update_file_handler import update_define_in_file


class OEMiRoTProjectBoot(BaseProject):

    def __init__(self, project_ini_path: str, logger: ROT_Logger):
        config = OEMiRoTProjectConfig(project_ini_path)
        super().__init__(config, logger, OEMIROT_VARIANT, has_postbuild=False, has_prebuild=True)

    def _custom_handle_prebuild(self, compiler: str):
        """
        Prebuild is updating:
        - the linker with ROM_ROT_ADDRESS and ROM_ROT_SIZE
        - the mcuboot_config.h and flash_layout.h headers with relevant defines
        - the boot_hal_cfg.h header with lifecycle-specific minimum option-byte define
        Args:
            compiler (str): The compiler type (e.g., 'iar').
        """
        # Updating linker
        self._update_linker_define(compiler, "ROM_ROT_ADDRESS")
        self._update_linker_define(compiler, "ROM_ROT_SIZE")

        # Updating mcuboot_config header
        self._update_mcuboot_config_header_file("MCUBOOT_S_DATA_IMAGE_NUMBER")
        self._update_mcuboot_config_header_file("MCUBOOT_NS_DATA_IMAGE_NUMBER")
        self._update_installation_mode_mcuboot_config_header_file()

        # Updating boot_hal_cfg header
        lifecycle_type = self.example_config.get_lifecycle_type()
        if lifecycle_type == LifecycleType.RDP:
            self._update_boot_hal_cfg_rdp_level_header_file()
        elif lifecycle_type == LifecycleType.PRODUCT_STATE:
            self._update_boot_hal_cfg_product_state_header_file()

        # Updating flash_layout header
        self._update_flash_layout_header_file("FLASH_ROT_CODE_OFFSET")
        self._update_flash_layout_header_file("FLASH_ROT_CODE_SIZE")
        if not self.example_config.get_board()["obk"]:
            self._update_flash_layout_header_file("FLASH_KEYS_OFFSET")
            self._update_flash_layout_header_file("FLASH_NVCNT_OFFSET")
            self._update_flash_layout_header_file("FLASH_HASH_REF_OFFSET")
        self._update_flash_layout_header_file("FLASH_PRIMARY_DATA_SLOT_OFFSET")
        self._update_flash_layout_header_file("FLASH_PRIMARY_DATA_SLOT_SIZE")
        self._update_flash_layout_header_file("FLASH_PRIMARY_APP_SLOT_OFFSET")
        self._update_flash_layout_header_file("FLASH_PRIMARY_APP_SLOT_SIZE")
        self._update_flash_layout_header_file("FLASH_SECONDARY_APP_SLOT_OFFSET")
        self._update_flash_layout_header_file("FLASH_SECONDARY_APP_SLOT_SIZE")
        self._update_flash_layout_header_file("FLASH_SECONDARY_DATA_SLOT_OFFSET")
        self._update_flash_layout_header_file("FLASH_SECONDARY_DATA_SLOT_SIZE")
        self._update_flash_layout_header_file("FLASH_ROT_WRP_START_OFFSET")
        self._update_flash_layout_header_file("FLASH_ROT_WRP_END_OFFSET")
        self._update_flash_layout_header_file("FLASH_ROT_HDP_END_OFFSET")

    def _compute_flash_layout(self):
        return OEMiRoTFlashLayout(self.example_config, self.memory_config,
                                  self.provisioning_config.get_oemirot_installation_mode())

    def _update_mcuboot_config_header_file(self, define_name: str):
        """
        Updates the define in mcuboot_config.h header file with the valuefrom flash layout.
        Args:
            define_name (str): The name of the define to update.
        """
        self._update_header_define("mcuboot_config", define_name)

    def _update_installation_mode_mcuboot_config_header_file(self):
        """
        Updates the define "INSTALLATION_MODE" in mcuboot_config.h header file
        with the installation mode value retrieved from the provisioning config.
        Raises:
            RoTValueError: If the configured installation mode is not supported.
        """
        installation_mode = self.provisioning_config.get_oemirot_installation_mode()
        header_path = self.config.get_header_path("mcuboot_config")
        update_define_in_file(header_path, "INSTALLATION_MODE", INSTALLATION_MODE_HAL_DEFINES[installation_mode])

    def _update_flash_layout_header_file(self, define_name: str):
        """
        Updates the define in flash_layout.h header file with the value from flash layout.
        Args:
            define_name (str): The name of the define to update.
        """
        self._update_header_define("flash_layout", define_name)

    def _update_boot_hal_cfg_rdp_level_header_file(self):
        """
        Updates the define "OEMIROT_OB_RDP_LEVEL_MIN" in boot_hal_cfg.h header file
        with the min RDP level value retrieved from the provisioning config.
        """
        header_path = self.config.get_header_path("boot_hal_cfg")
        rdp_min_level = self.provisioning_config.lifecycle_config.get_rdp_level("min")
        update_define_in_file(header_path, "OEMIROT_OB_RDP_LEVEL_MIN", RDP_LEVEL_HAL_DEFINES[rdp_min_level])

    def _update_boot_hal_cfg_product_state_header_file(self):
        """
        Updates the define "OEMIROT_OB_PRODUCT_STATE_MIN" in boot_hal_cfg.h header file
        with the min product state value retrieved from the provisioning config.
        """
        header_path = self.config.get_header_path("boot_hal_cfg")
        min_product_state = self.provisioning_config.lifecycle_config.get_product_state("min")
        hal_define = self.provisioning_config.lifecycle_config.get_product_state_hal_define(
            min_product_state)
        update_define_in_file(
            header_path,
            "OEMIROT_OB_PRODUCT_STATE_MIN",
            hal_define)

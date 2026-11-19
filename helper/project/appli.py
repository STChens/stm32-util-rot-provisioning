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

from helper.project.base import BaseProject


class BaseProjectAppli(BaseProject):

    def _common_handle_prebuild(self, compiler: str):
        """
        Prebuild is updating:
        - the linker with ROM_APPLI_ADDRESS and ROM_APPLI_SIZE
        - the provisioning xml with input path and hex format
        - the fwu xml with input path
        Args:
            compiler (str): The compiler type (e.g., 'iar').
        """
        # Updating linker
        self._update_linker_define(compiler, "ROM_APPLI_ADDRESS")
        self._update_linker_define(compiler, "ROM_APPLI_SIZE")

        # Updating provisioning xml
        self._update_image_xml_input_path('provisioning')
        self._update_image_xml_hex_format('provisioning')

        if 'fwu' in self.config.image_types:
            self._update_image_xml_input_path('fwu')

        # Updating header file
        self._update_app_flash_layout_header_file("DATA_IMAGE_NUMBER")
        self._update_app_flash_layout_header_file("FLASH_PRIMARY_DATA_SLOT_OFFSET")
        self._update_app_flash_layout_header_file("FLASH_PRIMARY_DATA_SLOT_SIZE")
        self._update_app_flash_layout_header_file("FLASH_PRIMARY_APP_SLOT_OFFSET")
        self._update_app_flash_layout_header_file("FLASH_PRIMARY_APP_SLOT_SIZE")
        self._update_app_flash_layout_header_file("FLASH_SECONDARY_APP_SLOT_OFFSET")
        self._update_app_flash_layout_header_file("FLASH_SECONDARY_APP_SLOT_SIZE")
        self._update_app_flash_layout_header_file("FLASH_SECONDARY_DATA_SLOT_OFFSET")
        self._update_app_flash_layout_header_file("FLASH_SECONDARY_DATA_SLOT_SIZE")
        self._update_app_flash_layout_header_file("FLASH_SECONDARY_APP_INSTALL_REQ_OFFSET")
        self._update_app_flash_layout_header_file("FLASH_SECONDARY_DATA_INSTALL_REQ_OFFSET")
        self._update_app_flash_layout_header_file("FLASH_PRIMARY_APP_VERSION_OFFSET")
        self._update_app_flash_layout_header_file("FLASH_PRIMARY_DATA_VERSION_OFFSET")

    def _write_default_image_xml(self):
        self._update_image_xml_hex_format('provisioning', field="Default")

    def _common_handle_postbuild(self, key_path: str):
        """
        Postbuild is:
        - updating the provisioning and fwu xml with keys and output path
        - generating the provisioning and fwu images
        """
        self._update_image_xml_keys_path('provisioning', key_path)
        self._update_image_xml_output_path('provisioning')
        self._generate_image('provisioning')
        if 'fwu' in self.config.image_types:
            self._update_image_xml_keys_path('fwu', key_path)
            self._update_image_xml_output_path('fwu')
            self._generate_image('fwu')

    def _update_app_flash_layout_header_file(self, define_name: str):
        """
        Updates a define in appli_flash_layout.h with the value from the flash layout.
        Args:
            define_name (str): The name of the define to update.
        """
        self._update_header_define("appli_flash_layout", define_name)

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
from helper.common.update_file_handler import update_define_in_file
from helper.config.oemirot.appli_project import AppliProjectConfig
from helper.config.oemirot.provisioning import INSTALLATION_MODE_HAL_DEFINES, OEMiRoTInstallationMode
from helper.config.variant import OEMIROT_VARIANT
from helper.config.oemirot.flash_layout import OEMiRoTFlashLayout
from helper.project.appli import BaseProjectAppli
from helper.config.oemirot.installation_mode_xml import update_installation_mode_xml_param


class OEMiRoTProjectAppli(BaseProjectAppli):

    def __init__(self, project_ini_path: str, logger: ROT_Logger):
        config = AppliProjectConfig(project_ini_path)
        super().__init__(config, logger, OEMIROT_VARIANT, has_postbuild=True, has_prebuild=True)

    def _custom_handle_prebuild(self, compiler: str):
        """
        Prebuild is updating:
        - the linker with ROM_APPLI_ADDRESS and ROM_APPLI_SIZE
        - the provisioning and fwu xml with input path, hex format and firmware area size
        - the appli_flash_layout.h header with relevant defines
        Args:
            compiler (str): The compiler type (e.g., 'iar').
        """
        # Updating linker
        self._common_handle_prebuild(compiler)

        # Updating header file
        self._update_app_flash_layout_header_file("FLASH_PRIMARY_APP_CONFIRM_OFFSET")
        self._update_app_flash_layout_header_file("FLASH_PRIMARY_DATA_CONFIRM_OFFSET")
        self._update_installation_mode_appli_flash_layout_header_file()

        # Updating installation mode in image XML files
        self._update_installation_mode_xml("provisioning")
        self._update_installation_mode_xml("fwu")

        # Updating firmware area size in image XML files
        self._update_image_xml_firmware_area_size('provisioning')
        self._update_image_xml_firmware_area_size('fwu')

    def _custom_handle_postbuild(self):
        """
        Postbuild is:
        - updating the provisioning and fwu xml with keys and output path
        - generating the provisioning and fwu images
        """
        self._common_handle_postbuild(self.provisioning_config.get_config_keys_xml_path())

    def _write_default_image_xml(self):
        super()._write_default_image_xml()
        self._update_image_xml_firmware_area_size('provisioning', field="Default")
        self._update_image_xml_firmware_area_size('fwu', field="Default")

    def _update_installation_mode_appli_flash_layout_header_file(self):
        """
        Updates the define "INSTALLATION_MODE" in appli_flash_layout.h header file
        with the installation mode value retrieved from the provisioning config.
        Raises:
            RoTValueError: If the configured installation mode is not supported.
        """
        installation_mode = self.provisioning_config.get_oemirot_installation_mode()
        header_path = self.config.get_header_path("appli_flash_layout")
        update_define_in_file(header_path, "INSTALLATION_MODE", INSTALLATION_MODE_HAL_DEFINES[installation_mode])

    def _update_installation_mode_xml(self, xml_type: str):
        """
        Updates the "Installation mode" <Param> in the given image XML file based on the
        provisioning config:
        - overwrite: ensures the param is present (adds it if missing).
        - swap: ensures the param is absent (removes it if present).
        Args:
            xml_type (str): The image XML type to update (e.g. 'provisioning' or 'fwu').
        Raises:
            RoTValueError: If the configured installation mode is not supported.
        """
        installation_mode = self.provisioning_config.get_oemirot_installation_mode()
        xml_path = self.config.get_image_xml_path(xml_type)
        update_installation_mode_xml_param(xml_path, installation_mode)

    def _compute_flash_layout(self):
        return OEMiRoTFlashLayout(self.example_config, self.memory_config,
                                  self.provisioning_config.get_oemirot_installation_mode())

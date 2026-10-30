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
from helper.config.stirot.appli_project import AppliProjectConfig
from helper.config.variant import STIROT_VARIANT
from helper.project.appli import BaseProjectAppli
from helper.config.stirot.flash_layout import STiRoTFlashLayout


class STiRoTProjectAppli(BaseProjectAppli):

    def __init__(self, project_ini_path: str, logger: ROT_Logger):
        config = AppliProjectConfig(project_ini_path)
        super().__init__(config, logger, STIROT_VARIANT, has_postbuild=True, has_prebuild=True)

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

    def _custom_handle_postbuild(self):
        """
        Postbuild is:
        - updating the provisioning and fwu xml with keys and output path
        - generating the provisioning and fwu images
        """
        self._common_handle_postbuild(self.provisioning_config.get_stirot_config_xml_path())

    def _compute_flash_layout(self) -> STiRoTFlashLayout:
        return STiRoTFlashLayout(self.example_config, self.memory_config)

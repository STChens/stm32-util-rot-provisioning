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

import xml.etree.ElementTree as ET

from helper.common.hxml import insert_xml_param_after_name, remove_xml_param_by_name
from helper.config.oemirot.provisioning import OEMiRoTInstallationMode
from helper.exception.rot_exception import RoTValueError

INSTALLATION_MODE_PARAM_NAME = "Installation mode"
INSTALLATION_MODE_PARAM = ET.fromstring(
    "<Param><Name>Installation mode</Name><Type>Data</Type>"
    "<Command>--overwrite-only</Command><Hidden>1</Hidden><Default /></Param>"
)
INSTALLATION_MODE_INSERT_AFTER = "Security version"


def update_installation_mode_xml_param(xml_path: str, installation_mode: OEMiRoTInstallationMode) -> None:
    """
    Updates the Installation mode parameter in an image XML based on OEMiRoT installation mode.

    - OVERWRITE: ensure the parameter is present.
    - SWAP: ensure the parameter is absent.
    """
    if installation_mode == OEMiRoTInstallationMode.OVERWRITE:
        insert_xml_param_after_name(xml_path, INSTALLATION_MODE_PARAM, INSTALLATION_MODE_INSERT_AFTER)
    elif installation_mode == OEMiRoTInstallationMode.SWAP:
        remove_xml_param_by_name(xml_path, INSTALLATION_MODE_PARAM_NAME)
    else:
        raise RoTValueError(f"Unknown installation mode: {installation_mode}")

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

from helper.common.log import ROT_Logger
from helper.project.oemirot.appli import OEMiRoTProjectAppli
from helper.project.stirot.appli import STiRoTProjectAppli
from helper.project.base import BaseProject
from helper.project.oemirot.boot import OEMiRoTProjectBoot
from helper.exception.rot_exception import RoTValueError


class ProjectType(Enum):
    OEMIROT_BOOT = 1
    OEMIROT_APPLICATION = 2
    STIROT_APPLICATION = 3


def create_project(project_type: ProjectType, project_ini_path: str, rot_logger: ROT_Logger) -> BaseProject:
    if project_type == ProjectType.OEMIROT_BOOT:
        return OEMiRoTProjectBoot(project_ini_path, rot_logger)

    if project_type == ProjectType.OEMIROT_APPLICATION:
        return OEMiRoTProjectAppli(project_ini_path, rot_logger)

    if project_type == ProjectType.STIROT_APPLICATION:
        return STiRoTProjectAppli(project_ini_path, rot_logger)

    raise RoTValueError(
        f"Project Type '{project_type}' is invalid.")

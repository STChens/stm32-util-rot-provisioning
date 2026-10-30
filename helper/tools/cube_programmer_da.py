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

import re
from typing import Optional

from helper.tools.cube_programmer import CubeProgrammer, CubeProgrammerMode, CubeProgrammerAccessPort
from helper.exception.rot_exception import RoTEmptyValueError, RoTValueError

DA_PROVISIONING_INTEGRITY_VALID = "discovery: ST provisioning integrity status message:VALID"
DA_LIFECYCLE = "PSA lifecycle"


class CubeProgrammerDA(CubeProgrammer):
    """
    CubeProgrammerDA extends the CubeProgrammer class to implement
    specific functionalities for provisioning and managing DA (Device Authentication) levels such as:
        - Performing full regression to product state OPEN
    """

    def dbg_auth(self, permission: str = None, key: str = None, certificate: str = None, password: str = None,
                 access_port: str = CubeProgrammerAccessPort.ACCESS_PORT_1) -> None:
        """Authenticate a debug session, prompting for permission when omitted.

        A key and a certificate are required unless a password file is provided.
        """
        if permission == "":
            raise RoTEmptyValueError("debug authentication permission")
        if permission is not None and re.fullmatch(r"[A-Za-z0-9]+", permission) is None:
            raise RoTValueError("The debug authentication permission must be alphanumeric.")
        if not password:
            if not key:
                raise RoTEmptyValueError("debug authentication key")
            if not certificate:
                raise RoTEmptyValueError("debug authentication certificate")

        command_args = []
        if permission:
            command_args.append(f"per={permission}")
        if key:
            command_args.append(f"key=\"{key}\"")
        if certificate:
            command_args.append(f"cert=\"{certificate}\"")
        if password:
            command_args.append(f"pwd=\"{password}\"")
        command_args.append("debugauth=1")
        command = " ".join(command_args)
        if permission is None:
            self.run_command(access_port=access_port, extra_args=command, interactive=True)
        else:
            self.run_command(access_port=access_port, extra_args=command)

    def da_regression_certificate(self, certificate: str, key: str, access_port: str = CubeProgrammerAccessPort.ACCESS_PORT_1) -> None:
        """
        Perform the regression from product state TZ-Closed/Closed to OPEN.

        Args:
            certificate (str): The certificate to be used for DA regression.
            key (str): The key to be used for DA regression.
            access_port (CubeProgrammerAccessPort, optional): Access port. Defaults to CubeProgrammerAccessPort.ACCESS_PORT_1.

        Returns:
            None

        Raises:
            RoTEmptyValueError: If the certificate or key is empty.
        """
        if not certificate:
            raise RoTEmptyValueError("certificate")
        if not key:
            raise RoTEmptyValueError("key")

        command = f"per=14 key={key} cert={certificate} debugauth=1"
        self.run_command(access_port=access_port, extra_args=command)

    def da_regression_password(self, password: str, access_port: str = CubeProgrammerAccessPort.ACCESS_PORT_1) -> None:
        """
        Perform the regression from product state TZ-Closed/Closed to OPEN using a password.

        Args:
            password (str): Path to the file holding the DA password.
            access_port (CubeProgrammerAccessPort, optional): Access port. Defaults to CubeProgrammerAccessPort.ACCESS_PORT_1.

        Returns:
            None

        Raises:
            RoTEmptyValueError: If the password is empty.
        """
        if not password:
            raise RoTEmptyValueError("password")

        command = f"pwd=\"{password}\" debugauth=1"
        self.run_command(access_port=access_port, extra_args=command)

    def da_discovery(self, access_port: str = CubeProgrammerAccessPort.ACCESS_PORT_1,
                     match_substring: Optional[str] = None, log_as_info: bool = True) -> Optional[str]:
        """Discover the device's debug authentication configuration."""
        return self.run_command(
            access_port=access_port,
            log_as_info=log_as_info,
            extra_args="debugauth=2",
            match_substring=match_substring,
        )

    def get_lifecycle_state(self, access_port: str = CubeProgrammerAccessPort.ACCESS_PORT_1) -> Optional[str]:
        """Return the current lifecycle state reported by DA discovery."""
        lifecycle_state = self.da_discovery(
            access_port=access_port,
            match_substring=DA_LIFECYCLE,
            log_as_info=False
        )
        if lifecycle_state is None:
            return None
        return lifecycle_state.split(":")[2].strip()

    def is_da_provisioning_valid(
            self, access_port: str = CubeProgrammerAccessPort.ACCESS_PORT_1) -> bool:
        """Return whether DA discovery reports valid provisioning integrity."""
        return self.da_discovery(
            access_port=access_port,
            match_substring=DA_PROVISIONING_INTEGRITY_VALID,
            log_as_info=False,
        ) is not None

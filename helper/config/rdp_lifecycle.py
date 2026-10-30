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

from helper.common.misc import format_values_with_or
from helper.exception.rot_exception import RoTValueError


class RDPLevel(Enum):
    """
    Enumeration representing different Readout Protection (RDP) levels for device provisioning.

    Attributes:
        RDP_0 (str): No readout protection.
        RDP_2_BS (str): Readout protection level 2 with boundary scan.
        RDP_2 (str): Full readout protection level 2.
    """
    RDP_0 = "RDP_0"
    RDP_2_BS = "RDP_2_BS"
    RDP_2 = "RDP_2"


RDP_LEVEL_HAL_DEFINES = {
    RDPLevel.RDP_0: "HAL_FLASH_ITF_OB_RDP_LEVEL_0",
    RDPLevel.RDP_2_BS: "HAL_FLASH_ITF_OB_RDP_LEVEL_2_WBS",
    RDPLevel.RDP_2: "HAL_FLASH_ITF_OB_RDP_LEVEL_2",
}


class RDPLifecycleConfig:
    """
    Holds all RDP-specific provisioning data and behaviour.

    Constructed by BaseProvisioningConfig._load_common_config() when the
    lifecycle type is RDP.  Callers access it via
    ``provisioning_config.lifecycle_config``.
    """

    def __init__(
        self,
        transition_bs_key_path: str,
        regression_rdp_key_path: str,
        rdp_level: dict,
        config: dict,
        config_path: str,
        update_config_file,
    ):
        self.transition_bs_key_path = transition_bs_key_path
        self.regression_rdp_key_path = regression_rdp_key_path
        self.rdp_level = rdp_level
        self._config = config
        self._config_path = config_path
        self._update_config_file = update_config_file

    def set_print_dict(self, print_config_items: dict) -> None:
        """Populates *print_config_items* with RDP-specific entries."""
        print_config_items["RDP Transition BS Key Path"] = self.transition_bs_key_path
        print_config_items["RDP Regression RDP Key Path"] = self.regression_rdp_key_path
        print_config_items["Minimum RDP Level"] = self.rdp_level["min"]
        print_config_items["Final RDP Level"] = self.rdp_level["final"]

    def get_transition_bs_key_path(self) -> str:
        """Returns the absolute path to the RDP transition BS key binary file."""
        return self.transition_bs_key_path

    def get_regression_rdp_key_path(self) -> str:
        """Returns the absolute path to the RDP regression RDP key binary file."""
        return self.regression_rdp_key_path

    def get_rdp_level(self, type: str) -> RDPLevel:
        """
        Returns the 'min' or 'final' RDP level.

        Raises:
            RoTValueError: If the stored value is not a valid RDPLevel member.
        """
        cap_type = type.capitalize()
        try:
            return RDPLevel(self.rdp_level[type])
        except ValueError:
            raise RoTValueError(
                f"{cap_type} RDP Level '{self.rdp_level[type]}' set in '{self._config_path}' "
                f"is not a valid RDP level. Please select "
                f"{format_values_with_or(level.value for level in RDPLevel)}.")

    def set_rdp_level(self, type: str, rdp_level: RDPLevel) -> None:
        """
        Persists the 'min' or 'final' RDP level to the INI file.

        Raises:
            RoTValueError: If *rdp_level* is not a valid RDPLevel member.
        """
        cap_type = type.capitalize()
        try:
            self._config['rdp'][f'{type}_rdp_level'] = RDPLevel(rdp_level).value
            self._update_config_file(self._config)
            self.rdp_level[type] = rdp_level
        except ValueError:
            raise RoTValueError(
                f"{cap_type} RDP Level '{rdp_level}' set in '{self._config_path}' "
                f"is not a valid RDP level. Please select "
                f"{format_values_with_or(level.value for level in RDPLevel)}.")

    def check_rdp_key_format(
        self, type: str, rdp_key: list, expected_key_length: int, key_path: str
    ) -> None:
        """
        Validates the content of an RDP key file.

        Raises:
            RoTValueError: If the key is the default value or has the wrong length.
        """
        if type == "transition":
            if rdp_key[0] == "0xAAAAAAAA":
                raise RoTValueError("RDP transition BS key cannot be the default value '0xAAAAAAAA'")

        if len(rdp_key) != expected_key_length:
            raise RoTValueError(
                f"RDP key file at '{key_path}' must contain exactly "
                f"{expected_key_length} element(s), got {len(rdp_key)}.")

    def get_rdp_key(self, type: str) -> list:
        """
        Reads and validates the RDP key from disk.

        Args:
            type (str): ``"transition"`` or ``"regression"``.

        Returns:
            list[str]: The key elements.
        """
        if type == "transition":
            key_path = self.get_transition_bs_key_path()
            expected_key_length = 1
        elif type == "regression":
            key_path = self.get_regression_rdp_key_path()
            expected_key_length = 4

        with open(key_path, "rb") as f:
            rdp_key = f.read().decode("utf-8").strip().split()

        self.check_rdp_key_format(type, rdp_key, expected_key_length, key_path)
        return rdp_key

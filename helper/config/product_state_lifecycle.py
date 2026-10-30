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

import os
from enum import Enum

from helper.common.hxml import extract_file_path_by_name, extract_output_file_path
from helper.common.misc import format_values_with_or
from helper.exception.rot_exception import RoTNotFoundError, RoTValueError


DA_ROOT_KEY_FILE_NAME = "Debug Authentication root key"
DA_PASSWORD_FILE_NAME = "password.bin"


def get_st_lifecycle_description(product_state: str) -> str:
    """Build the CubeProgrammer lifecycle description for a product state."""
    return f"ST_LIFECYCLE_{product_state.replace('-', '_')}"


class DAType(Enum):
    """Enumeration representing the debug authentication credential type."""
    PASSWORD = "password"
    CERTIFICATES = "certificates"


def get_product_state_hal_define(
    product_state: str,
    lifecycle: dict,
) -> str:
    """Returns the HAL product-state define for the configured state."""
    for state in lifecycle.get("states", []):
        if state.get("name") == product_state:
            hal_define = state.get("hal_define")
            if hal_define:
                return hal_define
            raise RoTValueError(f"HAL define is not configured for product state '{product_state}'.")
    raise RoTValueError(f"Product state '{product_state}' is not configured in the lifecycle.")


class ProductStateLifecycleConfig:
    """
    Holds all PRODUCT_STATE-specific provisioning data and behaviour.

    Constructed by BaseProvisioningConfig._load_common_config() when the
    lifecycle type is PRODUCT_STATE.  Callers access it via
    ``provisioning_config.lifecycle_config``.
    """

    def __init__(
        self,
        product_state: dict,
        config: dict,
        config_path: str,
        update_config_file,
        lifecycle: dict,
        da_certificates_supported: bool = True,
    ):
        self.product_state = product_state
        self._config = config
        self._config_path = config_path
        self._update_config_file = update_config_file
        self.lifecycle = lifecycle
        self.da_certificates_supported = da_certificates_supported
        self._lifecycle_states = self._validate_lifecycle_states(self.lifecycle)
        if "min" in self.product_state:
            self._validate_product_state_selection("min", self.product_state["min"])
        self._validate_product_state_selection("final", self.product_state["final"])
        self.get_da_type()

    @staticmethod
    def _validate_lifecycle_states(lifecycle: dict) -> list[dict]:
        if not isinstance(lifecycle, dict):
            raise RoTValueError("A lifecycle configuration is required for PRODUCT_STATE.")
        option_byte_name = lifecycle.get("ob_name")
        if not isinstance(option_byte_name, str) or not option_byte_name:
            raise RoTValueError("Lifecycle must define a non-empty 'ob_name'.")
        states = lifecycle.get("states")
        if not isinstance(states, list) or not states:
            raise RoTValueError("Lifecycle must define a non-empty 'states' list.")

        state_names = []
        for state in states:
            if not isinstance(state, dict) or not isinstance(state.get("name"), str) or not state["name"]:
                raise RoTValueError("Each lifecycle state must define a non-empty 'name'.")
            if (not isinstance(state.get("is_open"), bool)
                    or not isinstance(state.get("is_provisioning"), bool)
                    or not isinstance(state.get("prevents_reconnect"), bool)):
                raise RoTValueError(
                    f"Lifecycle state '{state.get('name')}' must define boolean 'is_open', 'is_provisioning' and "
                    "'prevents_reconnect'.")
            if not isinstance(state.get("ob_value"), str) or not state["ob_value"]:
                raise RoTValueError(
                    f"Lifecycle state '{state.get('name')}' must define a non-empty 'ob_value'.")
            if state["name"] in state_names:
                raise RoTValueError(f"Product state '{state['name']}' is defined more than once.")
            state_names.append(state["name"])
        provisioning_states = [state for state in states if state["is_provisioning"]]
        if len(provisioning_states) != 1:
            raise RoTValueError("Lifecycle must define exactly one provisioning state.")
        return states

    def get_lifecycle(self) -> dict:
        """Returns the configured lifecycle definition."""
        return self.lifecycle

    def get_product_state_names(self) -> list[str]:
        """Returns product-state names in their configured progression order."""
        return [
            state["name"]
            for state in self._lifecycle_states
            if not state["is_provisioning"]
        ]

    def _validate_product_state_selection(self, state_type: str, product_state: str) -> None:
        """Validate a product state selected for a user-selectable role."""
        if product_state not in self.get_product_state_names():
            raise RoTValueError(
                f"{state_type.capitalize()} Product State '{product_state}' set in '{self._config_path}' "
                f"is not a valid product state. Please select "
                f"{format_values_with_or(self.get_product_state_names())}.")

    def get_lifecycle_state(self, product_state: str) -> dict:
        """Returns the configured definition for a product state."""
        for state in self._lifecycle_states:
            if state["name"] == product_state:
                return state
        raise RoTValueError(
            f"Product state '{product_state}' set in '{self._config_path}' is not valid. Please select "
            f"{format_values_with_or(self.get_product_state_names())}.")

    def get_product_state_order(self, product_state: str) -> int:
        """Returns the zero-based progression index of a product state."""
        return self.get_product_state_names().index(product_state)

    def get_provisioning_state(self) -> dict:
        """Returns the state used while provisioning DA material."""
        return next(state for state in self._lifecycle_states if state["is_provisioning"])

    def get_open_states(self) -> list[dict]:
        """Returns the lifecycle states that permit open-device handling."""
        return [state for state in self._lifecycle_states if state["is_open"]]

    def get_product_state_hal_define(
        self,
        product_state: str,
    ) -> str:
        """Returns the configured HAL define for a product state."""
        return get_product_state_hal_define(product_state, self.lifecycle)

    def get_product_state_option_bytes(self, product_state: str) -> dict:
        """Returns the option bytes configured for a product state."""
        state = self.get_lifecycle_state(product_state)
        return {self.lifecycle["ob_name"]: state["ob_value"]}

    def get_stirot_product_state_value(self, product_state: str) -> str:
        """Derives the STiRoT product-state value from PRODUCT_STATE option bytes."""
        option_bytes = self.get_product_state_option_bytes(product_state)
        product_state_value = option_bytes.get("PRODUCT_STATE")
        try:
            return f"0x{int(product_state_value, 16) << 8:08X}"
        except (TypeError, ValueError):
            raise RoTValueError(
                f"PRODUCT_STATE option byte is not valid for product state '{product_state}'.")

    def is_open_product_state(self, product_state: str) -> bool:
        """Returns whether a product state permits open-device handling."""
        state = self.get_lifecycle_state(product_state)
        return state["is_open"]

    def prevents_product_state_reconnect(self, product_state: str) -> bool:
        """Returns whether a product state may prevent CubeProgrammer reconnects."""
        state = self.get_lifecycle_state(product_state)
        return state["prevents_reconnect"]

    def set_print_dict(self, print_config_items: dict) -> None:
        """Populates *print_config_items* with PRODUCT_STATE-specific entries."""
        da_type = self.get_da_type()
        print_config_items["DA Type"] = da_type.value
        print_config_items["DA Config XML Path"] = self.get_da_config_xml_path()
        if da_type == DAType.CERTIFICATES:
            print_config_items["DA Certificate Path"] = self.get_da_certificate_path()
        if "min" in self.product_state:
            print_config_items["Minimum Product State"] = self.product_state["min"]
        print_config_items["Final Product State"] = self.product_state["final"]

    def _get_da_config_path(self, field: str) -> str:
        """Resolve a path from the companion section for the selected DA type."""
        section = f"da_{self.get_da_type().value}"
        try:
            path = self._config[section][field]
        except KeyError as error:
            if error.args == (section,):
                raise RoTNotFoundError(f"Section '{section}' is not found in '{self._config_path}'.")
            raise RoTNotFoundError(
                f"Key '{field}' is not found in section '{section}' in '{self._config_path}'.")
        if not os.path.isabs(path):
            path = os.path.join(os.path.dirname(self._config_path), path)
        return os.path.normpath(path)

    def get_da_config_xml_path(self) -> str:
        """Returns the absolute path to the DA configuration XML file."""
        return self._get_da_config_path("config_xml_path")

    def get_da_key_path(self) -> str:
        """Returns the absolute path to the DA key file."""
        return extract_file_path_by_name(self.get_da_config_xml_path(), DA_ROOT_KEY_FILE_NAME)

    def get_da_certificate_path(self) -> str:
        """Returns the absolute path to the DA certificate file."""
        if self.get_da_type() != DAType.CERTIFICATES:
            return None
        return self._get_da_config_path("certificate")

    def get_da_password_path(self) -> str:
        """Returns the absolute path to the DA password file generated next to the DA root key."""
        da_config_obk_path = extract_output_file_path(self.get_da_config_xml_path())
        return os.path.join(os.path.dirname(da_config_obk_path), DA_PASSWORD_FILE_NAME)

    def get_da_certificates_supported(self) -> bool:
        """Returns whether certificate-based DA authentication is supported."""
        return self.da_certificates_supported

    def _get_supported_da_types(self) -> str:
        """Returns the DA type values supported by the configured board."""
        supported_types = [f"'{DAType.PASSWORD.value}'"]
        if self.da_certificates_supported:
            supported_types.insert(0, f"'{DAType.CERTIFICATES.value}'")
        if len(supported_types) == 1:
            return supported_types[0]
        return format_values_with_or(supported_types)

    def get_da_type(self) -> DAType:
        """Returns the configured debug authentication credential type."""
        try:
            configured_type = self._config['da']['type']
        except KeyError as error:
            if error.args == ('da',):
                raise RoTNotFoundError(f"Section 'da' is not found in '{self._config_path}'.")
            raise RoTNotFoundError(
                f"Key 'type' is not found in section 'da' in '{self._config_path}'.")
        try:
            da_type = DAType(configured_type)
        except ValueError:
            raise RoTValueError(
                f"DA type '{configured_type}' set in '{self._config_path}' is not valid. Please set "
                f"'type' to {self._get_supported_da_types()} in section '[da]'.")
        if da_type == DAType.CERTIFICATES and not self.da_certificates_supported:
            raise RoTValueError(
                f"DA type '{da_type.value}' is not supported by this board. Set "
                f"'type = {DAType.PASSWORD.value}' in section '[da]' in '{self._config_path}'.")
        return da_type

    def set_da_type(self, da_type: DAType) -> None:
        """Persists the selected debug authentication credential type."""
        try:
            selected_type = DAType(da_type)
        except ValueError:
            raise RoTValueError(
                f"DA type '{da_type}' set in '{self._config_path}' is not valid. Please set "
                f"'type' to {self._get_supported_da_types()} in section '[da]'.")
        if selected_type == DAType.CERTIFICATES and not self.da_certificates_supported:
            raise RoTValueError(
                f"DA type '{selected_type.value}' is not supported by this board. Set "
                f"'type = {DAType.PASSWORD.value}' in section '[da]' in '{self._config_path}'.")
        self._config['da']['type'] = selected_type.value
        self._update_config_file(self._config)

    def get_product_state(self, type: str) -> str:
        """
        Returns the 'min' or 'final' product state.

        Raises:
            RoTValueError: If the stored value is not a configured lifecycle state.
        """
        cap_type = type.capitalize()
        try:
            state_name = self.product_state[type]
            self._validate_product_state_selection(type, state_name)
            return state_name
        except (KeyError, ValueError, RoTValueError):
            raise RoTValueError(
                f"{cap_type} Product State '{self.product_state[type]}' set in '{self._config_path}' "
                f"is not a valid product state. Please select "
                f"{format_values_with_or(self.get_product_state_names())}.")

    def set_product_state(self, type: str, product_state: str) -> None:
        """
        Persists the 'min' or 'final' product state to the INI file.

        Raises:
            RoTValueError: If *product_state* is not a configured lifecycle state.
        """
        cap_type = type.capitalize()
        try:
            self._validate_product_state_selection(type, product_state)
            self._config['da'][f'{type}_product_state'] = product_state
            self._update_config_file(self._config)
            self.product_state[type] = product_state
        except (KeyError, ValueError, RoTValueError):
            raise RoTValueError(
                f"{cap_type} Product State '{product_state}' set in '{self._config_path}' "
                f"is not a valid product state. Please select "
                f"{format_values_with_or(self.get_product_state_names())}.")

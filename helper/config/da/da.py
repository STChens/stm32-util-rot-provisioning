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

from helper.config.base import BaseConfig
from helper.config.example import ExampleConfig, LifecycleType
from helper.config.product_state_lifecycle import ProductStateLifecycleConfig
from helper.exception.rot_exception import RoTValueError


class StandaloneDAProductStateLifecycleConfig(ProductStateLifecycleConfig):
    """Product-state lifecycle policy for the standalone DA workflow."""

    def get_product_state_names(self) -> list[str]:
        """Return closed, non-provisioning states selectable as final state."""
        return [
            state["name"]
            for state in self._lifecycle_states
            if not state["is_open"] and not state["is_provisioning"]
        ]


class DAConfig(BaseConfig):
    """
    Configuration handler for the standalone product-state DA workflow.

    The configuration combines a small INI file with a board example JSON.
    Relative paths in the INI file are resolved from the INI directory. The
    example must use the ``PRODUCT_STATE`` lifecycle and identify exactly one
    lifecycle state with ``is_provisioning: true``.

    Expected INI sections::

        [provisioning]
        path = /path/to/rot_provisioning
        example_json_path = /path/to/example.json
        tools_bin_env_name = STM32_PRG_PATH

        [da]
        type = certificates
        final_product_state = OPEN

        [da_certificates]
        config_xml_path = /path/to/da_config_certificate.xml
        certificate = /path/to/da_certificate.b64

        [da_password]
        config_xml_path = /path/to/da_config_password.xml
    """

    def _load_config(self):
        """Load paths, board metadata, and product-state lifecycle settings."""
        self.tools_bin_env_name = self.get_config_value("provisioning", "tools_bin_env_name")
        self.rot_provisioning_path = self.get_absolute_path_from_config("provisioning", "path")
        self.example_json_path = self.get_absolute_path_from_config(
            "provisioning", "example_json_path")
        self.example_config = ExampleConfig(self.example_json_path)

        if self.example_config.get_lifecycle_type() != LifecycleType.PRODUCT_STATE:
            raise RoTValueError("The standalone DA workflow only supports PRODUCT_STATE examples.")

        lifecycle = self.example_config.get_lifecycle()
        self.lifecycle_config = StandaloneDAProductStateLifecycleConfig(
            product_state={
                "final": self.get_config_value("da", "final_product_state"),
            },
            config=self.config,
            config_path=self.config_path,
            update_config_file=self._update_config_file,
            lifecycle=lifecycle,
            da_certificates_supported=self.example_config.get_da_certificates_supported(),
        )

    def _set_print_dict(self):
        """Populate the configuration summary printed when the file is loaded."""
        self.print_config_items["Tools Environment Variable Name"] = self.tools_bin_env_name
        self.print_config_items["Example JSON Path"] = self.example_json_path
        self.print_config_items["ROT Provisioning Path"] = self.rot_provisioning_path
        self.lifecycle_config.set_print_dict(self.print_config_items)

    def get_tools_bin_env_name(self) -> str:
        """Return the environment variable containing the tools binary path."""
        return self.tools_bin_env_name

    def get_rot_provisioning_path(self) -> str:
        """Return the absolute path to the RoT provisioning package."""
        return self.rot_provisioning_path

    def get_example_json_path(self) -> str:
        """Return the absolute path to the board example JSON file."""
        return self.example_json_path

    def _update_config_file(self, config):
        """Persist lifecycle selections to the standalone DA INI file."""
        with open(self.config_path, "w") as config_file:
            config.write(config_file)

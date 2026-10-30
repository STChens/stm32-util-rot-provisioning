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

import argparse
import logging

from helper.config.da.da import DAConfig
from helper.config.da.option_bytes import ob_da_apply
from helper.config.example import ExampleConfig
from helper.common.log import ROT_Logger
from helper.tools.cube_programmer import CubeProgrammer
from helper.tools.cube_programmer_da import CubeProgrammerDA
from helper.tools.tools_config import Tools_Config
from helper.workflow.common.generation_step import (
    DAConfig as DAConfigStep,
    DATypeSelection,
    GenerationStep,
    product_state_configuration_substeps,
)
from helper.workflow.common.installation_step import (
    InstallationStep,
    ProgramFinalProductStateStep,
    installation_substeps,
    program_da_obk,
)
from helper.workflow.common.discovery_step import DiscoveryStep
from helper.workflow.common.dbg_auth_step import DbgAuthStep
from helper.workflow.common.regression_step import DARegressionStep, RegressionStep
from helper.workflow.process import Process
from helper.workflow.step import Step


class FinalProductStateSelection(Step):
    """Select and persist the final product state for the DA workflow."""

    def __init__(self, config: DAConfig):
        step_config = dict(product_state_configuration_substeps["product_state_selection"])
        step_config["questions"] = dict(step_config["questions"])
        step_config["questions"]["options"] = config.lifecycle_config.get_product_state_names()
        super().__init__(step_config)
        self.config = config
        self.log_param = {"name": "Final", "path": config.config_path}

    def _get_question_default_candidate(self, _question: dict) -> object:
        return self.config.lifecycle_config.get_product_state("final")

    def process_step(self):
        self.config.lifecycle_config.set_product_state("final", self.choice)


class RemoveOBStep(Step):
    """Restore default option bytes and erase flash."""

    def __init__(self, example_config: ExampleConfig, cube_programmer: CubeProgrammer):
        super().__init__(installation_substeps["remove_ob"])
        self.example_config = example_config
        self.cube_programmer = cube_programmer

    def process_step(self):
        ob_da_apply("default", self.example_config, self.cube_programmer)
        self.cube_programmer.erase_all_flash_sectors()


class UserFlashStep(Step):
    """Wait for the user to flash application binaries or option bytes."""

    def __init__(self, name: str, message: str):
        super().__init__({
            "name": name,
            "texts": [{"message": message}],
            "wait_for_input": True,
            "skip_if_auto": True,
        })

    def process_step(self):
        pass


class DAOBKProgrammingStep(Step):
    """Flash only the generated DA OBK after user-managed device preparation."""

    def __init__(self, config: DAConfig, cube_programmer: CubeProgrammerDA):
        # Standalone DA only selects closed final states, so the shared OPEN-state warning does not apply.
        step_config = dict(installation_substeps["program_obk"])
        step_config["texts"] = []
        super().__init__(step_config)
        self.config = config
        self.cube_programmer = cube_programmer

    def process_step(self):
        program_da_obk(self.config, self.cube_programmer)


def SetupGenerationStep(config: DAConfig) -> Step:
    generation_step = GenerationStep()
    generation_step.add_step(FinalProductStateSelection(config))
    if config.lifecycle_config.get_da_certificates_supported():
        generation_step.add_step(DATypeSelection(config))
    generation_step.add_step(DAConfigStep(config))
    return generation_step


def SetupInstallationStep(config: DAConfig, stlink_sn: str = None,
                          dry_run: bool = False) -> Step:
    example_config = ExampleConfig(config.get_example_json_path())
    cube_programmer_kwargs = {"stlink_sn": stlink_sn, "dry_run": dry_run}
    cube_programmer = CubeProgrammerDA(
        Tools_Config(config.get_tools_bin_env_name()), **cube_programmer_kwargs)
    installation_step = InstallationStep(board_name=example_config.get_board().get("name"))
    installation_step.add_step(RemoveOBStep(example_config, cube_programmer))
    installation_step.add_step(UserFlashStep(
        "User binaries flashing",
        "Flash the application and any other binaries required by your product, then continue.",
    ))
    installation_step.add_step(UserFlashStep(
        "User option bytes flashing",
        "Flash the option bytes required by your product, then continue.",
    ))
    installation_step.add_step(DAOBKProgrammingStep(config, cube_programmer))
    installation_step.add_step(UserFlashStep(
        "User OBK flashing",
        "Flash the OBK required by your product, then continue.",
    ))
    installation_step.add_step(ProgramFinalProductStateStep(config, cube_programmer))
    return installation_step


def SetupRegressionStep(config: DAConfig, stlink_sn: str = None,
                        dry_run: bool = False) -> Step:
    """Set up standalone DA regression."""
    tools_config = Tools_Config(config.get_tools_bin_env_name())
    cube_programmer = CubeProgrammerDA(
        tools_config, stlink_sn=stlink_sn, dry_run=dry_run)
    regression_step = RegressionStep()
    regression_step.add_step(DARegressionStep(config, cube_programmer))
    return regression_step


def _add_common_args(parser: argparse.ArgumentParser, suppress_defaults: bool = False) -> None:
    defaults = {"default": argparse.SUPPRESS} if suppress_defaults else {}
    parser.add_argument("-a", "--auto", action="store_true", **defaults)
    parser.add_argument("-v", "--verbose", action="store_true", **defaults)
    parser.add_argument("-s", "--stlink-sn", **defaults)
    parser.add_argument("-d", "--dry-run", action="store_true", **defaults)


class Provisioning:
    """Example-facing command-line orchestration for standalone DA provisioning."""

    def __init__(self, path: str, logger: ROT_Logger):
        self.config_path = path
        self.logger = logger
        self.parser = self.set_up_argparse()

    @staticmethod
    def set_up_argparse() -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(description="DA provisioning script")
        _add_common_args(parser)

        subparsers = parser.add_subparsers(
            dest="command",
            required=True,
            metavar="{provisioning,regression,discovery,dbg-auth}",
        )
        provisioning_parser = subparsers.add_parser(
            "provisioning", help="Generate and install the DA OBK")
        _add_common_args(provisioning_parser, suppress_defaults=True)
        provisioning_parser.add_argument(
            "-g", "--no-gen", action="store_true",
            help="Only install a previously generated DA OBK")

        regression_parser = subparsers.add_parser(
            "regression", help="Regress the device using the DA credential")
        _add_common_args(regression_parser, suppress_defaults=True)

        discovery_parser = subparsers.add_parser(
            "discovery", help="Perform DA discovery")
        _add_common_args(discovery_parser, suppress_defaults=True)

        dbg_auth_parser = subparsers.add_parser(
            "dbg-auth", help="Authenticate a debug session")
        _add_common_args(dbg_auth_parser, suppress_defaults=True)
        dbg_auth_parser.add_argument(
            "permission", nargs="?", metavar="PERMISSION",
            help="Debug-authentication permission; omit for interactive selection")
        return parser

    def process_args(self):
        args = self.parser.parse_args()
        command = args.command
        if command == "provisioning" and args.auto:
            self.parser.error(
                "provisioning does not support --auto because binaries and "
                "option bytes must be flashed manually")
        if command == "dbg-auth" and args.permission is None and args.auto:
            self.parser.error("dbg-auth requires a permission with --auto")

        provisioning = Process(auto=args.auto)
        config = DAConfig(self.config_path)
        if args.verbose:
            self.logger.set_print_debug_level(logging.DEBUG)

        if command == "discovery":
            provisioning.add_step(DiscoveryStep(
                config, stlink_sn=args.stlink_sn, dry_run=args.dry_run))
            provisioning.run_process()
            return

        if command == "regression":
            provisioning.add_step(SetupRegressionStep(
                config, stlink_sn=args.stlink_sn, dry_run=args.dry_run))
            provisioning.run_process()
            return

        if command == "dbg-auth":
            provisioning.add_step(DbgAuthStep(
                config,
                choice=args.permission,
                stlink_sn=args.stlink_sn,
                dry_run=args.dry_run))
            provisioning.run_process()
            return
        if not args.no_gen:
            provisioning.add_step(SetupGenerationStep(config))
        provisioning.add_step(SetupInstallationStep(
            config, stlink_sn=args.stlink_sn, dry_run=args.dry_run))
        provisioning.run_process()

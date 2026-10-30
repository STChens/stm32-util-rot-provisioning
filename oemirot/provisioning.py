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

import sys
import os
import argparse
import logging

from helper.common.log import ROT_Logger
from helper.workflow.process import Process

from oemirot.generation_step import SetupGenerationStep
from oemirot.regression_step import SetupRegressionStep
from oemirot.installation_step import SetupInstallationStep

from helper.config.variant import OEMIROT_VARIANT
from helper.workflow.common.discovery_step import DiscoveryStep
from helper.workflow.common.dbg_auth_step import DbgAuthStep


def _add_common_args(parser, suppress_defaults=False):
    argument_defaults = {}
    if suppress_defaults:
        argument_defaults["default"] = argparse.SUPPRESS

    parser.add_argument('-a', '--auto', action="store_true", **argument_defaults,
                        help='Remove needs of user input')
    parser.add_argument('-v', '--verbose', action="store_true", **argument_defaults,
                        help='Set log to debug')
    parser.add_argument('-s', '--stlink-sn', action="store", **argument_defaults,
                        help='ST-Link serial number to use for provisioning')
    parser.add_argument('-d', '--dry-run', action="store_true", **argument_defaults,
                        help='Log STM32CubeProgrammer commands without executing them')


class Provisioning():
    def __init__(self, path: str, logger: ROT_Logger, expose_da: bool = True):
        self.config_path = path
        self.logger = logger
        self.expose_da = expose_da
        self.parser = self.set_up_argparse()

    def set_up_argparse(self):
        """
        Sets up the argparse for the ROT provisioning.
        This parser includes:
            - -v/--verbose flag for enabling debug logging.
            - -h/--help flag for displaying help information.
            - -g/--no-gen Only do the installation of a previously generated configuration.
            - -a/--auto flag for removing the need of user input
            - -w/--with-regression flag for running the regression step along with other steps.
            - -r/--regression flag for running only the regression step.
            - -s/--stlink-sn to specify the ST-Link serial number to use for provisioning.
            - -o/--no-obk-provisioning to bypass the OBK provisioning step during installation.
            - -d/--dry-run to log CubeProgrammer commands without executing them.
            - da -r/--regression for running only the regression step.
            - da -i/--discovery for performing DA discovery.
            - da -t/--dbg-auth for authenticating a debug session, with an optional permission argument.

        Returns:
            argparse.ArgumentParser: Configured argument parser for the ROT provisioning.
        """
        # Create the main parser
        parser = argparse.ArgumentParser(description='ROT provisioning script')

        # Add the arg
        parser.add_argument('-g', '--no-gen', action="store_true",
                            help="Only do the installation of a previously generated configuration")
        _add_common_args(parser)
        parser.add_argument('-w', '--with-regression', action="store_true",
                            help='Run regression step along with other steps')
        parser.add_argument('-r', '--regression', action="store_true",
                            help='Run only the regression step')
        parser.add_argument('-o', '--no-obk-provisioning', action="store_true",
                            help="Bypass the OBK provisioning step during installation (for testing purposes only in OPEN state)")
        parser.set_defaults(regression=False, discovery=False)

        if self.expose_da:
            subparsers = parser.add_subparsers(dest="command")
            da_parser = subparsers.add_parser('da', help='Run a DA workflow')
            _add_common_args(da_parser, suppress_defaults=True)
            da_modes = da_parser.add_mutually_exclusive_group(required=True)
            da_modes.add_argument('-r', '--regression', action="store_true",
                                  help='Run only the regression step')
            da_modes.add_argument('-i', '--discovery', action="store_true",
                                  help='Perform DA discovery')
            da_modes.add_argument('-t', '--dbg-auth', nargs='?', const=True, default=False,
                                  metavar='PERMISSION',
                                  help='Perform DA debug authentication; If no permission is provided, interactive menu will be displayed to select one.')

        return parser

    def process_args(self):
        """
        Processes command-line arguments for the ROT provisioning.
        """
        args = self.parser.parse_args()

        command = getattr(args, 'command', None)

        if command == 'da' and (args.no_gen or args.no_obk_provisioning):
            self.parser.error(
                'da cannot be combined with --no-gen or '
                '--no-obk-provisioning')

        if command == 'da' and args.with_regression:
            self.parser.error('da cannot be combined with --with-regression')

        if command == 'da' and args.dbg_auth == '':
            self.parser.error('da --dbg-auth requires a non-empty permission')

        if command == 'da' and args.dbg_auth is True and args.auto:
            self.parser.error('da --dbg-auth requires a permission with --auto')

        auto = args.auto
        dry_run = args.dry_run
        provisioning = Process(auto=auto)

        # Load provisioning configuration
        config = OEMIROT_VARIANT.provisioning_config_cls(self.config_path)

        # Set log level
        if args.verbose:
            self.logger.set_print_debug_level(logging.DEBUG)

        if command == 'da' and args.discovery:
            discovery_kwargs = {
                "stlink_sn": args.stlink_sn,
                "dry_run": dry_run,
            }
            provisioning.add_step(DiscoveryStep(config, **discovery_kwargs))
            provisioning.run_process()
            return

        if command == 'da' and args.dbg_auth is not False:
            debug_auth_kwargs = {"stlink_sn": args.stlink_sn, "dry_run": dry_run,
                                 "choice": None if args.dbg_auth is True else args.dbg_auth}
            provisioning.add_step(DbgAuthStep(config, **debug_auth_kwargs))
            provisioning.run_process()
            return

        # Process regression step
        if args.regression or args.with_regression:
            regression_kwargs = {"stlink_sn": args.stlink_sn, "remove_ob": args.regression, "dry_run": dry_run}
            regression_step = SetupRegressionStep(config, **regression_kwargs)
            provisioning.add_step(regression_step)
            if args.regression:
                # Execute only the regression step
                provisioning.run_process()
                return

        # Process generation step
        if not args.no_gen:
            generation_step = SetupGenerationStep(config)
            provisioning.add_step(generation_step)

        # Process installation step
        installation_kwargs = {"stlink_sn": args.stlink_sn,
                               "no_obk_provisioning": args.no_obk_provisioning, "dry_run": dry_run}
        installation_step = SetupInstallationStep(config, **installation_kwargs)
        provisioning.add_step(installation_step)

        # Execute the provisioning workflow, which includes generation
        # and installation steps based on the provided arguments.
        provisioning.run_process()

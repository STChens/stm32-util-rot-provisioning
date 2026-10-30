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

from dataclasses import dataclass
from typing import Type

from helper.config.memory_base import BaseMemoryConfig
from helper.config.provisioning_base import BaseProvisioningConfig
from helper.config.oemirot.provisioning import OEMiRoTProvisioningConfig
from helper.config.oemirot.memory import OEMiRoTMemoryConfig
from helper.config.stirot.provisioning import STiRoTProvisioningConfig
from helper.config.stirot.memory import STiRoTMemoryConfig


@dataclass(frozen=True)
class RoTVariant:
    """
    Describes the concrete config classes used by one RoT variant.

    The memory config class is exposed for runtime steps that instantiate
    memory configs directly. The provisioning config class is the entry
    point used by helper code to load the full provisioning configuration.
    """

    # Concrete memory config class associated with the variant.
    memory_config_cls: Type[BaseMemoryConfig]
    # Concrete provisioning config class associated with the variant.
    provisioning_config_cls: Type[BaseProvisioningConfig]


# Predefined variant descriptor for OEMiRoT workflows.
OEMIROT_VARIANT = RoTVariant(
    memory_config_cls=OEMiRoTMemoryConfig,
    provisioning_config_cls=OEMiRoTProvisioningConfig,
)


# Predefined variant descriptor for STiRoT workflows.
STIROT_VARIANT = RoTVariant(
    memory_config_cls=STiRoTMemoryConfig,
    provisioning_config_cls=STiRoTProvisioningConfig,
)

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

import math
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../"))
from helper.exception.rot_exception import RoTUnexpectedError, RoTValueError


def compute_wrp(start_address: int, end_address: int, wrpgrp_size: int, wrpgrp_ob_length: int, bank_size: int, block_size: int, wrp_ob_name: list[list[str]]) -> dict:
    """
    Computes WRP option bytes starting from start_address up to end_address in a continuous manner.
    Args:
        start_address (int): Start address. (e.g. 0x0)
        end_address (int): End address. (e.g. 0x1FFF)
        wrpgrp_size (int): Number of WRP groups per bank.
        wrpgrp_ob_length (int): Number of option bytes used to represent WRP groups per bank.
        bank_size (int): Size of each bank in bytes.
        block_size (int): Size of each block in bytes.
        wrp_ob_name (list[list[str]]): List of option byte names per bank. (example : [["WRP1SGn1", "WRP1SGn2"], ["WRP2SGn1", "WRP2SGn2"]])
    Raises:
        RoTUnexpectedError: If input parameters are invalid.
        RoTValueError: If end_address exceeds total memory size.
    Returns:
        dict: Mapping option byte names to computed values.
    """
    if bank_size <= 0 or block_size <= 0 or wrpgrp_size <= 0:
        raise RoTUnexpectedError("bank_size, block_size, wrpgrp_size must be > 0")
    if (bank_size * len(wrp_ob_name) <= end_address):
        raise RoTValueError("end_address exceeds total size.")
    bank_count = len(wrp_ob_name)
    wrp_gn_count = len(wrp_ob_name[0])
    size_to_protect = end_address - start_address + 1
    # Each group is represented by wrpgrp_ob_length bytes
    base_mask = (1 << (wrp_gn_count * (wrpgrp_ob_length * 8))) - 1
    result = {}

    size_left = size_to_protect
    current_start = start_address
    for bank in range(bank_count):
        bank_start_addr = bank * bank_size
        bank_end_addr = bank_start_addr + bank_size
        wrp_mask = base_mask

        # If the current protection range starts after this bank, leave it open
        if current_start >= bank_end_addr:
            # No protection needed in this bank
            pass
        # If no size left to protect, leave it open
        elif size_left <= 0:
            pass
        else:
            # Determine the protection range within this bank
            protect_start = max(current_start, bank_start_addr)
            protect_end = min(current_start + size_left, bank_end_addr)
            first_bit = (protect_start - bank_start_addr) // (wrpgrp_size * block_size)
            bits_to_clear = math.ceil((protect_end - protect_start) / (wrpgrp_size * block_size))

            if protect_start < protect_end:
                for i in range(first_bit, first_bit + bits_to_clear):
                    wrp_mask &= ~(1 << i)
                size_left -= (protect_end - protect_start)
                current_start = protect_end
        for name, i in zip(wrp_ob_name[bank], range(wrp_gn_count)):
            # Extract the value for this group, using wrpgrp_ob_length bytes
            shift = (wrpgrp_ob_length * 8) * i
            mask = (1 << (wrpgrp_ob_length * 8)) - 1
            value = (wrp_mask >> shift) & mask
            result[name] = f"0x{{:0{wrpgrp_ob_length * 2}x}}".format(value)
    return result


def compute_hdp(hdp_end_offset: int, bank_size: int, hdp_block_size: int, hdp_ob_name: list[list[str]]) -> dict:
    """
    Computes the HDP OB values starting from 0 up to hdp_end_offset in a continuous manner.
    Args:
        hdp_end_offset (int): The end offset (in bytes) up to which HDP should be enabled. (e.g. 0x1FFF means first 8KB are HDP protected)
        bank_size (int): The size (in bytes) of each HDP bank.
        hdp_block_size (int): The size (in bytes) of each HDP block within a bank.
        hdp_ob_name (list[list[str]]): List of option bytes name per bank, (example : [["HDP1_STRT", "HDP1_END"], ["HDP2_STRT", "HDP2_END"]])
    Raises:
        RoTUnexpectedError: If input parameters are invalid.
        RoTValueError: If hdp_end_offset exceeds total memory size.
    Returns:
        dict: A dictionary mapping option byte names to their computed values as strings.
    """

    if (hdp_end_offset < 0 or bank_size <= 0 or hdp_block_size <= 0):
        raise RoTUnexpectedError("hdp_end_offset must be >= 0 and bank_size, hdp_block_size must be > 0")
    if (bank_size * len(hdp_ob_name) <= hdp_end_offset):
        raise RoTValueError("hdp_end_offset exceeds total size.")
    remaining_blocks = math.ceil((hdp_end_offset + 1) / hdp_block_size)

    blocks_in_bank = bank_size // hdp_block_size
    ob = {}
    for hdp in hdp_ob_name:
        if remaining_blocks == 0:
            ob[hdp[0]] = "0x1"
            ob[hdp[1]] = "0x0"
            continue
        if remaining_blocks >= blocks_in_bank:
            ob[hdp[0]] = "0x0"
            ob[hdp[1]] = hex(blocks_in_bank - 1)
            remaining_blocks -= blocks_in_bank
        else:
            ob[hdp[0]] = "0x0"
            ob[hdp[1]] = hex(remaining_blocks - 1)
            remaining_blocks = 0
    return ob

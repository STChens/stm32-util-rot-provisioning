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

import copy
import xml.etree.ElementTree as ET
import os
import logging

from helper.exception.rot_exception import RoTNotFoundError

logger = logging.getLogger()


def _build_absolute_path_from_xml(xml, value_text):
    return os.path.abspath(os.path.join(os.path.dirname(xml), value_text))


def _extract_value_from_xml(xml):
    tree = ET.parse(xml)
    root = tree.getroot()
    value_tag = root.find(".//Output/Value")
    if value_tag is None or value_tag.text is None:
        raise RoTNotFoundError(f"No '<Output><Value>' found in XML file: {xml}.")
    return value_tag.text


def extract_output_file_path(xml):
    """
    Extracts the output file path from an XML file.
    Absolute path is always returned. If the path in the XML is relative,
    it is converted to an absolute path based on the XML file's location.

    Example XML structure:
    <Root>
        <Output>
            <Value>relative/or/absolute/path/to/binary.bin</Value>
        </Output>
    </Root>

    Args:
        xml (str): Path to the XML file.
    Returns:
        str: Absolute path to the output binary file.
    Raises:
        RoTNotFoundError: If the <Value> tag is not found within <Output> or is empty.
    """
    output_value = _extract_value_from_xml(xml)

    if (os.path.isabs(output_value)):
        return output_value
    return _build_absolute_path_from_xml(xml, output_value)


def _find_xml_field(xml_path: str, tag_name: str, field_name_tag: str, field_name: str):
    """
    Parses an XML file and returns the field matching the provided selector.

    Raises:
        RoTNotFoundError: If the field is not found in the XML file.
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()
    field = root.find(f".//{tag_name}[{field_name_tag}='{field_name}']")
    if field is None:
        raise RoTNotFoundError(f"The field {field_name_tag}='{field_name}' was not found in the '{xml_path}' file.")
    return tree, field


def _extract_xml_value(xml_path: str, tag_name: str, field_name_tag: str, field_name: str, field_to_extract: str) -> str:
    """
    Extracts the value of a field in an XML file based on the field name and its tag (e.g. Name, Title).

    Args:
        xml_path (str): Path to the XML file.
        tag_name (str): The tag to search for (e.g. "File", "Param", "Output").
        field_name_tag (str): The tag to search for the field name (e.g. "Name", "Title").
        field_name (str): The name of the field to extract.
        field_to_extract (str): The child field containing the value to return (e.g. "Value").

    Returns:
        str: The extracted value.

    Raises:
        RoTNotFoundError: If the field or extracted value is not found in the XML file.
    """
    _, field = _find_xml_field(xml_path, tag_name, field_name_tag, field_name)
    value_element = field.find(field_to_extract)
    if value_element is None or value_element.text is None:
        raise RoTNotFoundError(
            f"The field {field_name_tag}='{field_name}' does not have a '{field_to_extract}' element in '{xml_path}'.")

    return value_element.text


def extract_file_path_by_name(xml_path: str, file_name: str) -> str:
    """
    Extracts the file path from a File entry identified by its Name and returns an absolute path.
    """
    file_value = _extract_xml_value(xml_path, "File", "Name", file_name, "Value")
    if os.path.isabs(file_value):
        return file_value
    return _build_absolute_path_from_xml(xml_path, file_value)


def extract_xml_value_by_name(xml_path: str, tag_name: str, field_name: str, field_to_extract: str) -> str:
    """
    Extracts the value of a field in an XML file where the field name is specified by the <Name> tag.

    This is a convenience wrapper for _extract_xml_value, defaulting the field name tag to 'Name'.

    Args:
        xml_path (str): Path to the XML file to parse.
        tag_name (str): The tag to search for (e.g., "Bool", "File").
        field_name (str): The name of the field to extract (matched in <Name> tag).
        field_to_extract (str): The field of the value to extract (e.g., "Value").

    Returns:
        str: The extracted value matching the specified field.

    Raises:
        RoTNotFoundError: If no matching entry is found.
    """
    return _extract_xml_value(xml_path, tag_name, "Name", field_name, field_to_extract)


def _write_xml_to_file(xml_path: str, root: ET.Element) -> None:
    """Serializes the XML root element and writes it to file with the standard UTF-8 header."""
    xml_string = ET.tostring(root, encoding='unicode')
    xml_string = xml_string.replace("encoding='UTF-8'", 'encoding="UTF-8"')
    with open(xml_path, 'w', encoding='UTF-8') as xml_file:
        xml_file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
        xml_file.write(xml_string)


def _update_xml_value(xml_path: str, tag_name: str, field_name_tag: str, field_name: str, field_to_update: str, new_value: str) -> None:
    """
    Updates the value of a field in an XML file based on the field name and its tag (e.g., Name, Title).
    All the empty field <NAME_FIELD><NAME_FIELD/> are updated with <NAME_FIELD />.

    Args:
        xml_path (str): Path to the XML file.
        tag_name (str): The tag to search for (e.g., "Param", "Output").
        field_name (str): The name of the field to update (e.g., "Firmware area Size").
        field_name_tag (str): The tag to search for the field name (e.g., "Name", "Title").
        field_to_update (str): The field of the value to update (e.g., "Value").
        new_value (str): The new value to assign to the field. Can be a path, size, or address.

    Assumptions:
     - The file path is an existing absolute path (no check is performed).

    Raises:
        RoTNotFoundError: If the field with the given name is not found in the XML file.
    """
    tree, field = _find_xml_field(xml_path, tag_name, field_name_tag, field_name)
    value_element = field.find(field_to_update)
    if value_element is None:
        raise RoTNotFoundError(
            f"The field {field_name_tag}='{field_name}' does not have a '{field_to_update}' element to update.")

    if (value_element.text == new_value):
        logger.debug(
            f"No changes made to '{field_to_update}' in '{tag_name}'/{field_name_tag}='{field_name}' in '{xml_path}'; the value is already '{new_value}'.")
        return  # No changes made, exit early

    value_element.text = new_value
    _write_xml_to_file(xml_path, tree.getroot())
    logger.debug(
        f"Updated the field '{field_to_update}' in '{tag_name}'/{field_name_tag}='{field_name}' to '{new_value}' in '{xml_path}'.")


def update_xml_value_by_name(xml_path: str, tag_name: str, field_name: str, field_to_update: str, new_value: str) -> None:
    """
    Updates the value of a field in an XML file where the field name is specified by the <Name> tag.

    This is a convenience wrapper for update_xml_value, defaulting the field name tag to 'Name'.

    Args:
        xml_path (str): Path to the XML file.
        tag_name (str): The tag to search for (e.g., "Param", "Output").
        field_name (str): The name of the field to update (matched in <Name> tag).
        field_to_update (str): The field of the value to update (e.g., "Value").
        new_value (str): The new value to assign to the field.
    """
    _update_xml_value(xml_path, tag_name, "Name", field_name, field_to_update, new_value)


def update_xml_value_by_title(xml_path: str, tag_name: str, field_name: str, field_to_update: str, new_value: str) -> None:
    """
    Updates the value of a field in an XML file where the field name is specified by the <Title> tag.

    This is a convenience wrapper for update_xml_value, defaulting the field name tag to 'Title'.

    Args:
        xml_path (str): Path to the XML file.
        tag_name (str): The tag to search for (e.g., "Param", "Output").
        field_name (str): The name of the field to update (matched in <Title> tag).
        field_to_update (str): The field of the value to update (e.g., "Value").
        new_value (str): The new value to assign to the field.
    """
    _update_xml_value(xml_path, tag_name, "Title", field_name, field_to_update, new_value)


def remove_xml_param_by_name(xml_path: str, param_name: str) -> None:
    """
    Removes the <Param> block identified by its <Name> from the XML file.
    If no such param exists, does nothing.

    Args:
        xml_path (str): Path to the XML file.
        param_name (str): The value of the <Name> tag identifying the <Param> to remove.
    """
    try:
        tree, param = _find_xml_field(xml_path, "Param", "Name", param_name)
    except RoTNotFoundError:
        logger.debug(f"Param '{param_name}' not found in '{xml_path}', nothing to remove.")
        return
    root = tree.getroot()
    root.find(f".//Param[Name='{param_name}']/..").remove(param)
    _write_xml_to_file(xml_path, root)
    logger.debug(f"Removed Param '{param_name}' from '{xml_path}'.")


def insert_xml_param_after_name(
    xml_path: str,
    new_param: ET.Element,
    after_param_name: str,
) -> None:
    """
    Inserts a new <Param> block after the param named `after_param_name`, unless a param with
    the same <Name> already exists (no-op in that case).

    The indentation of the new element is derived from the `after_param_name` element so the
    output formatting stays consistent with the rest of the file.

    Args:
        xml_path (str): Path to the XML file.
        new_param (ET.Element): The <Param> element to insert.
        after_param_name (str): The <Name> value of the existing param after which to insert.
    Raises:
        RoTNotFoundError: If no param named `after_param_name` is found in the XML.
    """
    new_param_name = new_param.find("Name").text
    tree = ET.parse(xml_path)
    root = tree.getroot()

    if root.find(f".//Param[Name='{new_param_name}']") is not None:
        logger.debug(f"Param '{new_param_name}' already exists in '{xml_path}', nothing to insert.")
        return

    for parent in root.iter():
        for param in parent.findall("Param"):
            name_el = param.find("Name")
            if name_el is not None and name_el.text == after_param_name:
                inner_indent = param.text or "\n        "
                param_tail = param.tail or "\n    "
                last_child_tail = param[-1].tail if len(param) > 0 else "\n    "

                elem = copy.deepcopy(new_param)
                elem.text = inner_indent
                elem.tail = param_tail
                for i, child in enumerate(list(elem)):
                    child.tail = inner_indent if i < len(list(elem)) - 1 else last_child_tail

                all_children = list(parent)
                parent.insert(all_children.index(param) + 1, elem)

                _write_xml_to_file(xml_path, root)
                logger.debug(f"Inserted Param '{new_param_name}' after '{after_param_name}' in '{xml_path}'.")
                return

    raise RoTNotFoundError(f"Could not find Param '{after_param_name}' in '{xml_path}' to insert after.")

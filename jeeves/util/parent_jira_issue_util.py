from typing import Dict

from jeeves.model.custom_types import JSON
from jeeves.model.jira_document import JiraDocument

# By default, categories will be sorted by count unless they are included here
_PARENT_CATEGORIES_TO_SORT_BY_KEY = {
    "app_version",
    "os_version",
}


def parse_parent_description(body_text: str) -> Dict[str, Dict[str, int]]:
    """
    Given the body text of a parent "hub" issue for duplicates, extracts
    the aggregated information in that body text and returns it as a
    dictionary.

    The returned dictionary is a mapping from strings, representing
    information field names, to another layer of dictionaries. These inner
    dictionaries are mappings from strings, representing instance types, to
    ints, representing instance occurances. Overall, the body text of a
    parent issue consists of several groups of information (such as
    platforms a bug has been reported in, courses a bug has been reported
    in, etc) that form the keys in the outer dictionary. Each inner
    dictionary entry represents a count of an instance appropriate for that
    group.

    The expected format of the body text is as follows:
    - Zero or more paragraphs separated by exactly one empty line.
    - A paragraph consists of:
        - A line of text that ends in a colon (this is the group title)
        - Zero or more data entries, each on their own line, with no
            empty lines between them. A data entry consists of a string,
            representing the instance type, then a colon and a space, and
            finally an integer representing the instance count of that
            instance type.

    Parameters:
        body_text: The body text of a parent issue to parse. Note that there
                    is currently no error checking on this function, so if
                    you provide garbage in you're likely to get garbage out.
    Returns:
        A dictionary of strings mapped to dictionaries of strings mapped to
        ints, as described above.
    """
    category_mapping = JiraDocument.get_parent_category_mappings()
    extracted_stats = {}
    body_lines = [line.strip() for line in body_text.splitlines()]
    line_rover = 0
    while line_rover < len(body_lines):
        category_header = body_lines[line_rover][:-1]
        # Skip over lines that aren't known category headers
        if category_header not in category_mapping:
            line_rover += 1
            continue
        category = category_mapping[category_header]
        extracted_stats[category] = {}
        line_rover += 1
        while line_rover < len(body_lines) and body_lines[line_rover] != "":
            instance_type = body_lines[line_rover].split(": ")[0]
            instance_count = int(body_lines[line_rover].split(": ")[1])
            extracted_stats[category][instance_type] = instance_count
            line_rover += 1
        while line_rover < len(body_lines) and body_lines[line_rover] == "":
            line_rover += 1

    return extracted_stats


def _create_paragraph_block(block_contents: str) -> JSON:
    """
    Simple wrapper to create a paragraph block with the given contents.

    Parameters:
        block_contents: The text we want to put in the paragraph block

    Returns:
        A paragraph block with the given contents as text.
    """
    paragraph_json = {
        "type": "paragraph",
        "content": [
            {
                "type": "text",
                "text": block_contents,
            }
        ],
    }
    return paragraph_json


def generate_parent_body_text_from_data(description: str, data: Dict[str, Dict[str, int]]) -> JSON:
    """
    Given data aggregated from several duplicate issues, constructs the body
    text for the parent issue of those duplicate issues.

    Parameters:
        data: A dictionary representing data aggregated from duplicates, see
                the return value of parse_parent_description for details. This
                must have as keys each of the values of the JiraDocument
                parent category mappings.

    Returns:
        A JSON blob that can be directly passed as body text into a Jira
        API call.
    """
    paragraph_blocks = []

    # Description
    if len(description.strip()) > 0:
        paragraph_blocks.append(_create_paragraph_block(description + "\n\n"))

    # Parent categories
    category_mapping = JiraDocument.get_parent_category_mappings()
    for human_name, data_name in category_mapping.items():
        block_contents = f"{human_name}:\n"
        sorted_data_items = (
            sorted(data[data_name].items(), key=lambda x: x[0])
            if data_name in _PARENT_CATEGORIES_TO_SORT_BY_KEY
            else sorted(data[data_name].items(), key=lambda x: x[1], reverse=True)
        )
        for data_type, data_count in sorted_data_items:
            block_contents = f"{block_contents}{data_type}: {data_count}\n"
        paragraph_blocks.append(_create_paragraph_block(block_contents))

    body_json = {
        "type": "doc",
        "version": 1,
        "content": paragraph_blocks,
    }
    return body_json


def update_parent_data_from_child(
    parent_data: Dict[str, Dict[str, int]], child: JiraDocument
) -> Dict[str, Dict[str, int]]:
    """
    Given a structure of parent issue data and a child issue, updates the
    parent data to include the information from the child issue.

    Parameters:
        parent_data: A structure of parent issue data. See
                        parse_parent_description for details.
        child: A document that has data we want to include in the parent.

    Returns:
        We return parent_data after modification for convenience, though
        the input argument will also be mutated and therefore this return
        value is optional and may be ignored.
    """
    child_json = child.serialize_to_json(child)
    for category in parent_data:
        if category in child_json:
            if category == "components":
                area_components = [
                    subcat for subcat in child_json[category] if subcat.endswith("Area")
                ]
                for area in area_components:
                    if area not in parent_data[category]:
                        parent_data[category][area] = 0
                    parent_data[category][area] += 1
            else:
                data_instance = "NOT PRESENT"
                if child_json[category]:
                    data_instance = child_json[category]
                if data_instance not in parent_data[category]:
                    parent_data[category][data_instance] = 0
                parent_data[category][data_instance] += 1

    return parent_data


def strip_parent_description(body_text: str) -> str:
    """
    Given the body text of a parent "hub" issue for duplicates, strips
    out the aggregated information in that body text and returns it as a
    string.

    "This is a description with no parent metadata." -> "This is a description with no parent metadata."

    "With metadata\nINTERFACE LANGUAGES:\nfr: 2\nNOT PRESENT: 1\nen: 1\n" -> "With metadata"

    "INTERFACE LANGUAGES:\nfr: 2\nNOT PRESENT: 1\nen: 1\n\nTrailing metadata" -> "Trailing metadata"

    Parameters:
        body_text: The body text of a parent issue to parse.

    Returns:
        A string representing the description of the issue with all of the
        parent data catgories stripped out.
    """
    stripped_description_lines = []
    category_mapping = JiraDocument.get_parent_category_mappings().keys()
    body_lines = [line.strip() for line in body_text.splitlines()]
    line_rover = 0
    while line_rover < len(body_lines):
        # If we're at a category header, skip to the end of the category
        if any(body_lines[line_rover].startswith(f"{category}:") for category in category_mapping):
            line_rover += 1  # Skip the header itself
            # Skip over all the content of the category
            while line_rover < len(body_lines) and body_lines[line_rover] != "":
                line_rover += 1
            # Skip over all the blank lines after the category
            while line_rover < len(body_lines) and body_lines[line_rover] == "":
                line_rover += 1
        else:
            stripped_description_lines.append(body_lines[line_rover])
            line_rover += 1
    return "\n".join(stripped_description_lines)

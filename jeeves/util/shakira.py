"""
Utils used for shakira.
"""

from typing import Optional


def format_description(description: str, generated_description: Optional[str]):
    description_blocks = [description]
    if generated_description:
        description_blocks.append(generated_description)
    return "\n".join(description_blocks)


JIRA_PROJ_TO_PLATFORM = {"DLAA": "Android", "DLAI": "iOS", "DLAW": "Web"}

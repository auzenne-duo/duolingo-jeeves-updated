"""
A set of priorities supported on jira.
"""

from __future__ import annotations

from enum import Enum
from typing import Optional


class JiraPriority(str, Enum):
    """Jira priorities"""

    HIGHEST = "Highest"
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"
    LOWEST = "Lowest"
    UNPRIORITIZED = "Unprioritized"

    @staticmethod
    def get_enum_from_string(value: str) -> Optional[JiraPriority]:
        return JiraPriority.__members__.get(value.strip().upper())

"""
A set of priorities supported on jira.
"""

from enum import Enum


class JiraPriority(Enum):
    """Jira priorities"""

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"

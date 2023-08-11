from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

FIXED_RESOLUTIONS = ["Fixed", "Done"]
UNRESOLVED_RESOLUTIONS = ["Unresolved", ""]

_FIXED_WITHIN_ONE_WEEK = True
_NOT_FIXED_WITHIN_ONE_WEEK = False


class PriorityValue(Enum):
    UNPRIORITIZED = "Unprioritized"
    LOW_LOWEST = "Low"
    MEDIUM = "Medium"
    HIGH_HIGHEST = "High"
    ACUTE = "Acute"


PRIORITY_SORTING_ORDER: Dict[PriorityValue, int] = {
    PriorityValue.ACUTE: 0,
    PriorityValue.HIGH_HIGHEST: 1,
    PriorityValue.MEDIUM: 2,
    PriorityValue.LOW_LOWEST: 3,
    PriorityValue.UNPRIORITIZED: 4,
}


class Resolution(Enum):
    FIXED = "Fixed"
    CLOSED_UNFIXED = "Closed"
    OPEN = "Open"


priority_map = {
    "Highest": PriorityValue.HIGH_HIGHEST,
    "High": PriorityValue.HIGH_HIGHEST,
    "Medium": PriorityValue.MEDIUM,
    "Low": PriorityValue.LOW_LOWEST,
    "Lowest": PriorityValue.LOW_LOWEST,
    "none": PriorityValue.UNPRIORITIZED,
    None: PriorityValue.UNPRIORITIZED,
    "Unprioritized": PriorityValue.UNPRIORITIZED,
}

score_map = {
    PriorityValue.ACUTE: {
        Resolution.FIXED: {_FIXED_WITHIN_ONE_WEEK: 200, _NOT_FIXED_WITHIN_ONE_WEEK: 100},
        Resolution.CLOSED_UNFIXED: 20,
        Resolution.OPEN: 200,
    },
    PriorityValue.HIGH_HIGHEST: {
        Resolution.FIXED: {_FIXED_WITHIN_ONE_WEEK: 100, _NOT_FIXED_WITHIN_ONE_WEEK: 50},
        Resolution.CLOSED_UNFIXED: 10,
        Resolution.OPEN: 100,
    },
    PriorityValue.MEDIUM: {
        Resolution.FIXED: {_FIXED_WITHIN_ONE_WEEK: 20, _NOT_FIXED_WITHIN_ONE_WEEK: 10},
        Resolution.CLOSED_UNFIXED: 2,
        Resolution.OPEN: 10,
    },
    PriorityValue.LOW_LOWEST: {
        Resolution.FIXED: {_FIXED_WITHIN_ONE_WEEK: 10, _NOT_FIXED_WITHIN_ONE_WEEK: 5},
        Resolution.CLOSED_UNFIXED: 1,
        Resolution.OPEN: 5,
    },
    PriorityValue.UNPRIORITIZED: {
        Resolution.FIXED: {_FIXED_WITHIN_ONE_WEEK: 10, _NOT_FIXED_WITHIN_ONE_WEEK: 5},
        Resolution.CLOSED_UNFIXED: 1,
        Resolution.OPEN: 50,
    },
}


@dataclass(frozen=True, eq=True)
class QualityScoreParams:
    is_done: bool
    is_fixed_within_one_week: bool
    group: PriorityValue
    resolution: Resolution
    score: int
    text: str

    @classmethod
    def init_from_jira_data(
        cls,
        creation_date: datetime,
        priority: str,
        resolution_date: Optional[datetime],
        labels: Optional[List[str]] = None,
        resolution: str = "",
    ) -> QualityScoreParams:
        """
        Initialize a score parameters object from Jira data
        """
        is_fixed = resolution in FIXED_RESOLUTIONS
        is_done = resolution not in UNRESOLVED_RESOLUTIONS
        is_fixed_within_one_week = False
        if is_fixed and resolution_date and creation_date:
            is_fixed_within_one_week = (resolution_date - creation_date).days <= 7

        group = priority_map[priority]
        if labels and any("acute" in label.lower() for label in labels):
            group = PriorityValue.ACUTE
        resolution = (
            Resolution.OPEN
            if not is_done
            else Resolution.FIXED
            if is_fixed
            else Resolution.CLOSED_UNFIXED
        )
        score = score_map[group][resolution]
        if resolution == Resolution.FIXED:
            score = score_map[group][resolution][is_fixed_within_one_week]
        text = f"{group.value} {resolution.value}"
        if is_fixed_within_one_week:
            text = f"{text} within one week"
        return QualityScoreParams(is_done, is_fixed_within_one_week, group, resolution, score, text)

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional

FIXED_RESOLUTIONS = ["Fixed", "Done"]
UNRESOLVED_RESOLUTIONS = ["Unresolved", ""]


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
    FIXED_WITHIN_ONE_WEEK = "Fixed within one week"
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

score_map: Dict[PriorityValue, Dict[Resolution, int]] = {
    PriorityValue.ACUTE: {
        Resolution.FIXED_WITHIN_ONE_WEEK: 200,
        Resolution.FIXED: 100,
        Resolution.CLOSED_UNFIXED: 20,
        Resolution.OPEN: 200,
    },
    PriorityValue.HIGH_HIGHEST: {
        Resolution.FIXED_WITHIN_ONE_WEEK: 100,
        Resolution.FIXED: 50,
        Resolution.CLOSED_UNFIXED: 10,
        Resolution.OPEN: 100,
    },
    PriorityValue.MEDIUM: {
        Resolution.FIXED_WITHIN_ONE_WEEK: 20,
        Resolution.FIXED: 10,
        Resolution.CLOSED_UNFIXED: 2,
        Resolution.OPEN: 10,
    },
    PriorityValue.LOW_LOWEST: {
        Resolution.FIXED_WITHIN_ONE_WEEK: 10,
        Resolution.FIXED: 5,
        Resolution.CLOSED_UNFIXED: 1,
        Resolution.OPEN: 5,
    },
    PriorityValue.UNPRIORITIZED: {
        Resolution.FIXED_WITHIN_ONE_WEEK: 10,
        Resolution.FIXED: 5,
        Resolution.CLOSED_UNFIXED: 1,
        Resolution.OPEN: 50,
    },
}


@dataclass(frozen=True, eq=True)
class QualityScoreParams:
    is_done: bool
    group: PriorityValue
    resolution: Resolution
    score: int
    text: str

    duplicates: Optional[int] = field(default=None, compare=False, hash=False)

    @classmethod
    def init_from_group_and_resolution(
        cls,
        group: PriorityValue,
        resolution: Resolution,
        duplicates: Optional[int] = None,
    ) -> QualityScoreParams:
        """
        Initialize a score params object from the priority group and resolution
        (with duplicate information, if available).
        """
        is_done = not resolution is Resolution.OPEN
        score = cls.get_score(group, resolution, duplicates or 0)
        text = cls.get_text(group, resolution, duplicates)
        return QualityScoreParams(is_done, group, resolution, score, text, duplicates=duplicates)

    @classmethod
    def init_from_jira_data(
        cls,
        creation_date: datetime,
        priority: str,
        resolution_date: Optional[datetime],
        duplicates: int,
        labels: Optional[List[str]] = None,
        resolution_str: str = "",
    ) -> QualityScoreParams:
        """
        Initialize a score parameters object from Jira data
        """
        is_fixed = resolution_str in FIXED_RESOLUTIONS
        is_done = resolution_str not in UNRESOLVED_RESOLUTIONS
        is_fixed_within_one_week = False
        if is_fixed and resolution_date and creation_date:
            is_fixed_within_one_week = (resolution_date - creation_date).days <= 7

        group = priority_map[priority]
        if labels and any("acute" in label.lower() for label in labels):
            group = PriorityValue.ACUTE

        if is_fixed:
            resolution = (
                Resolution.FIXED_WITHIN_ONE_WEEK if is_fixed_within_one_week else Resolution.FIXED
            )
        else:
            resolution = Resolution.OPEN if not is_done else Resolution.CLOSED_UNFIXED

        score = cls.get_score(group, resolution, duplicates)
        text = cls.get_text(group, resolution, duplicates)
        return QualityScoreParams(is_done, group, resolution, score, text, duplicates=duplicates)

    @classmethod
    def get_score(cls, group: PriorityValue, resolution: Resolution, duplicates: int) -> int:
        duplicate_bonus = duplicates if resolution != Resolution.OPEN else 0
        return score_map[group][resolution] + duplicate_bonus

    @classmethod
    def get_text(
        cls, group: PriorityValue, resolution: Resolution, duplicates: Optional[int]
    ) -> str:
        if duplicates is None:
            duplicates_suffix = ""
        else:
            string_plural_suffix = "" if duplicates == 1 else "s"
            duplicates_suffix = f" ({duplicates} duplicate{string_plural_suffix})"

        return f"{group.value} {resolution.value}{duplicates_suffix}"

    @classmethod
    def get_all_possible_score_params(cls) -> List[QualityScoreParams]:
        return [
            QualityScoreParams.init_from_group_and_resolution(group, resolution)
            for group in PriorityValue
            for resolution in Resolution
        ]

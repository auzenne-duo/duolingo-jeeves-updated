from enum import Enum
from typing import List


class PriorityValue(Enum):
    UNPRIORITIZED = 0
    LOW_LOWEST = 1
    MEDIUM = 2
    HIGH_HIGHEST = 3
    ACUTE = 4


class Resolution(Enum):
    FIXED = 1
    CLOSED_UNFIXED = 2
    OPEN = 3


class TimeToFix(Enum):
    WITHIN_ONE_WEEK = True
    NOT_WITHIN_ONE_WEEK = False


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
        Resolution.FIXED: {TimeToFix.WITHIN_ONE_WEEK: 200, TimeToFix.NOT_WITHIN_ONE_WEEK: 100},
        Resolution.CLOSED_UNFIXED: 20,
        Resolution.OPEN: 200,
    },
    PriorityValue.HIGH_HIGHEST: {
        Resolution.FIXED: {TimeToFix.WITHIN_ONE_WEEK: 100, TimeToFix.NOT_WITHIN_ONE_WEEK: 50},
        Resolution.CLOSED_UNFIXED: 10,
        Resolution.OPEN: 100,
    },
    PriorityValue.MEDIUM: {
        Resolution.FIXED: {TimeToFix.WITHIN_ONE_WEEK: 20, TimeToFix.NOT_WITHIN_ONE_WEEK: 10},
        Resolution.CLOSED_UNFIXED: 2,
        Resolution.OPEN: 10,
    },
    PriorityValue.LOW_LOWEST: {
        Resolution.FIXED: {TimeToFix.WITHIN_ONE_WEEK: 10, TimeToFix.NOT_WITHIN_ONE_WEEK: 5},
        Resolution.CLOSED_UNFIXED: 1,
        Resolution.OPEN: 5,
    },
    PriorityValue.UNPRIORITIZED: {
        Resolution.FIXED: {TimeToFix.WITHIN_ONE_WEEK: 10, TimeToFix.NOT_WITHIN_ONE_WEEK: 5},
        Resolution.CLOSED_UNFIXED: 1,
        Resolution.OPEN: 50,
    },
}


class IssueScoreParameters:
    """
    Keeps track of an issue's priority, resolution, and time to fix
    which are used to calculate a score for the issue
    """

    def __init__(
        self,
        priority: str,
        labels: List[str] = None,
        is_done: bool = False,
        is_fixed: bool = False,
        fixed_within_one_week: bool = False,
    ):
        self.group = priority_map[priority]
        if labels and any("acute" in label for label in labels):
            self.group = PriorityValue.ACUTE
        self.resolution = (
            Resolution.OPEN
            if not is_done
            else Resolution.FIXED
            if is_fixed
            else Resolution.CLOSED_UNFIXED
        )
        self.is_done = is_done
        self.time_to_fix = (
            TimeToFix.WITHIN_ONE_WEEK if fixed_within_one_week else TimeToFix.NOT_WITHIN_ONE_WEEK
        )
        self.calculate_score()
        self.priority = priority

    def calculate_score(self) -> None:
        """
        Calculate the score for the score parameters object and stores it in self.score
        """
        if self.resolution == Resolution.FIXED:
            self.score = score_map[self.group][self.resolution][self.time_to_fix]
        else:
            self.score = score_map[self.group][self.resolution]

    def __eq__(self, other) -> bool:
        if isinstance(self, other.__class__):
            return (
                self.group == other.group
                and self.resolution == other.resolution
                and self.time_to_fix == other.time_to_fix
            )
        return False

    def __lt__(self, other) -> bool:
        if isinstance(self, other.__class__):
            return self.score < other.score
        return TypeError(f"Cannot compare {type(other)} to priority object")

    def __hash__(self) -> int:
        return hash((self.group)) + hash(self.resolution) + hash(self.time_to_fix)

    def __str__(self) -> str:
        return f"{self.priority} ({self.score}) {self.is_done} {self.resolution} {self.time_to_fix}"

    def __repr__(self) -> str:
        return f"{self.priority} ({self.score}) {self.is_done} {self.resolution} {self.time_to_fix}"

    def get_resolution_text(self) -> str:
        if self.time_to_fix == TimeToFix.WITHIN_ONE_WEEK:
            return "Fixed within one week"
        elif self.resolution == Resolution.FIXED:
            return "Fixed"
        elif self.resolution == Resolution.OPEN:
            return "Open"
        return "Closed"

    def serialize(self) -> dict:
        """
        Serialize score parameters into a dict
        """
        return {
            "is_done": self.is_done,
            "priority": self.priority,
            "score": self.score,
            "group": self.group.name,
            "resolution": self.resolution.name,
            "time_to_fix": self.time_to_fix.name,
        }

    @classmethod
    def deserialize(cls, data: dict) -> "IssueScoreParameters":
        """
        Deserialize score parameters from a dict
        """
        issue_params = cls.__new__(cls)
        for key, value in data.items():
            setattr(issue_params, key, value)
        issue_params.time_to_fix = TimeToFix[data["time_to_fix"]]
        issue_params.resolution = Resolution[data["resolution"]]
        issue_params.group = PriorityValue[data["group"]]
        issue_params.calculate_score()
        return issue_params

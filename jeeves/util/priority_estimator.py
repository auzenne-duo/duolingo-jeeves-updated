from enum import Enum
from typing import Optional


class JiraPriority(Enum):
    """
    A set of priorities supported on jira.
    """

    LOW = "Low"
    MEDIUM = "Medium"
    HIGH = "High"


class PriorityEstimator:
    # Note, to counteract high priority words "freez", "break", and "kill",
    # the phrases "streak freez", "skill", and "line break" are added to low priority
    low_priority_words = {
        "align",
        "typo",
        "font",
        "spac",
        "polish",
        "position",
        "mismatch",
        "capital",
        "horizontal",
        "vertical",
        "large",
        "small",
        "depth",
        "separat",
        "text",
        "streak freez",
        "skill",
        "line break",
    }
    high_priority_words = {
        "block",
        "freez",
        "froze",
        "crash",
        "fail",
        "undid",
        "stuck",
        "blank",
        "force",
        "break",
        "broken",
        "prevent",
        "unreach",
        "purchase",
        "lock",
        "restart",
        "kill",
        "reboot",
        "not show",
        "nothing",
        "not visible",
    }

    @classmethod
    def estimate_priority(cls, text: str, num_dupes: Optional[int] = 0) -> JiraPriority:
        """
        Estimates the priority of a ticket based on the presence of keywords

        parameters:
            text: string of text
            num_dupes: int number of duplicates that the ticket has

        return:
            priority: JiraPriority of Low, Medium, or High
        """
        low_count = high_count = 0
        for word in cls.low_priority_words:
            low_count += word in text
        for word in cls.high_priority_words:
            high_count += word in text

        if high_count > low_count:
            severity = 3
        elif high_count == low_count:
            severity = 2
        else:
            severity = 1

        if num_dupes < 1:
            impact = 1
        elif 1 <= num_dupes < 3:
            impact = 2
        else:
            impact = 3

        priority = severity + impact
        if 0 < priority <= 3:
            return JiraPriority.LOW.value
        elif 3 < priority <= 4:
            return JiraPriority.MEDIUM.value
        else:
            return JiraPriority.HIGH.value

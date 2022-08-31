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
    low_priority_words = {
        "align",
        "capital",
        "center",
        "depth",
        "font",
        "horizontal",
        "large",
        "mismatch",
        "orient",
        "polish",
        "position",
        "separat",
        "small",
        "spac",
        "text",
        "typo",
        "vertical",
    }
    high_priority_words = {
        "blank",
        "block",
        "break",
        "broken",
        "crash",
        "error",
        "exit",
        "fail",
        "force",
        "freez",
        "froze",
        "kill",
        "lock",
        "not show",
        "not visible",
        "nothing",
        "prevent",
        "purchase",
        "reboot",
        "restart",
        "stuck",
        "undid",
        "unknown",
        "unreach",
        "unsupported",
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
        text = text.lower()
        high_keywords = []
        low_keywords = []
        low_count = high_count = 0
        for word in cls.low_priority_words:
            if word in text:
                low_count += 1
                low_keywords.append(word)
        for word in cls.high_priority_words:
            if word in text:
                high_count += 1
                high_keywords.append(word)

        if high_count:
            severity = 3
        elif low_count:
            severity = 1
        else:
            severity = 2

        if num_dupes < 3:
            impact = 0
        else:
            impact = 1

        priority = severity + impact
        if 0 < priority <= 1:
            return JiraPriority.LOW.value, low_keywords
        elif 1 < priority <= 2:
            return JiraPriority.MEDIUM.value, low_keywords
        else:
            return JiraPriority.HIGH.value, high_keywords

from enum import Enum
from typing import List


class QualityReportPriority:
    def __init__(self, text, rank, score):
        self.text = text
        self.rank = rank
        self.score = score

    def __eq__(self, other) -> bool:
        if isinstance(self, other.__class__):
            return self.text == other.text
        return False

    def __lt__(self, other) -> bool:
        if isinstance(self, other.__class__):
            return self.rank < other.rank
        return TypeError(f"Cannot compare {type(other)} to priority object")

    def __hash__(self) -> int:
        return hash((self.text))

    def __str__(self) -> str:
        return self.text

    def __repr__(self) -> str:
        return self.text


class PriorityValue(Enum):
    UNPRIORITIZED = QualityReportPriority("Unprioritized", -1, 5)
    LOW_LOWEST = QualityReportPriority("Low/Lowest", 1, 1)
    MEDIUM = QualityReportPriority("Medium", 3, 2)
    HIGH_HIGHEST = QualityReportPriority("High/Highest", 4, 10)
    ACUTE_0 = QualityReportPriority("Acute 0", 6, 15)
    ACUTE_1 = QualityReportPriority("Acute 1", 7, 20)
    ACUTE_2 = QualityReportPriority("Acute 2", 8, 25)
    ACUTE_3 = QualityReportPriority("Acute 3", 9, 30)


priority_map = {
    "Highest": PriorityValue.HIGH_HIGHEST.value,
    "High": PriorityValue.HIGH_HIGHEST.value,
    "Medium": PriorityValue.MEDIUM.value,
    "Low": PriorityValue.LOW_LOWEST.value,
    "Lowest": PriorityValue.LOW_LOWEST.value,
    "none": PriorityValue.UNPRIORITIZED.value,
    None: PriorityValue.UNPRIORITIZED.value,
    "Unprioritized": PriorityValue.UNPRIORITIZED.value,
}
label_map = {
    "acute-3": PriorityValue.ACUTE_3.value,
    "acute-2": PriorityValue.ACUTE_2.value,
    "acute-1": PriorityValue.ACUTE_1.value,
    "acute-0": PriorityValue.ACUTE_0.value,
    "acute": PriorityValue.ACUTE_0.value,
}


def get_quality_report_priority(priority: str, labels: List[str] = None):
    priority_value = priority_map[priority]
    if labels:
        for label in labels:
            if label in label_map and label_map[label] > priority_value:
                priority_value = label_map[label]
    return priority_value

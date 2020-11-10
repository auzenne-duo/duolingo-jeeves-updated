from enum import Enum


class ShakeToReportCategory(Enum):
    """
    Type representing different categories for shake-to-report documents.
    INTERNAL documents are those that come from internal testers, i.e. Duos.
    EXTERNAL documents are those that come from external testers, i.e. beta users.
    NON-STR documents are not associated with shake-to-report.
    """

    EXTERNAL = "EXTERNAL"
    INTERNAL = "INTERNAL"
    NON_STR = "NON_STR"

from enum import Enum


class ShakeToReportCategory(Enum):
    """
    Type representing different categories for documents, classifying both
    origin and shake-to-report status.
    - EXTERNAL documents are those that come from external shake-to-report
      testers, i.e. beta users.
    - INTERNAL documents are those that come from internal shake-to-report
      testers, i.e. Duos.
    - NON_STR_EXTERNAL documents are not associated with shake-to-report and
      originate from somewhere outside Duolingo, i.e. app store comments.
    - NON_STR_INTERNAL documents are not associated with shake-to-report and
      originate from somewhere inside Duolingo, i.e. Jira.
    """

    EXTERNAL = "EXTERNAL"
    INTERNAL = "INTERNAL"
    NON_STR_EXTERNAL = "NON_STR_EXTERNAL"
    NON_STR_INTERNAL = "NON_STR_INTERNAL"

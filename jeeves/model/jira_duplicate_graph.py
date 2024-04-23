from enum import Enum
from typing import Dict, Set, Tuple

import attr

from jeeves.model.jira_document import JiraDocument


class JiraDuplicateGraphOperationStatus(str, Enum):
    """Used for reporting the status of an operation performed en masse on the Jira Duplicate Graph.

    For example, when trying to add or remove a set of links, we will have to make a lot
    of Jira API calls, some of which may fail. We then use one of these statuses to make
    it clear what kinds of failures occurred and/or remediations are needed.

    Variants:
        FAILURE: The operation failed for all items.
        PARTIAL: The operation failed for some items.
        SUCCESS: The operation succeeded for all items.
    """

    FAILURE = "failure"
    PARTIAL = "partial"
    SUCCESS = "success"


@attr.s(kw_only=True)
class JiraDuplicateGraph:
    issue_keys_to_documents: Dict[str, JiraDocument] = attr.ib()
    existing_issue_links: Set[Tuple[str, str]] = attr.ib()

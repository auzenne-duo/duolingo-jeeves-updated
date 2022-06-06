from typing import Dict, Set, Tuple

import attr

from jeeves.model.jira_document import JiraDocument


@attr.s(kw_only=True)
class JiraDuplicateGraph:
    issue_keys_to_documents: Dict[str, JiraDocument] = attr.ib()
    existing_issue_links: Set[Tuple[str]] = attr.ib()

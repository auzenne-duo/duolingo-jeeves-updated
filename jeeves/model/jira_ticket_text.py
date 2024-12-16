from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import Optional

from jeeves.model.jira_document import JiraDocument
from jeeves.util.cleanup import extract_duolingo_metadata_and_body
from jeeves.util.parent_jira_issue_util import strip_parent_description

# Components of the request format (in YAML)
REQ_DESCRIPTION = "DESCRIPTION"
REQ_ID = "ID"  # The Jira ticket ID
REQ_TITLE = "TITLE"

# Components of the response format (in JSON)
RESP_DESCRIPTION = "description"
RESP_TITLE = "title"


@dataclass
class JiraTicketText:
    """
    A simplified container for the textual content of a Jira ticket (title and description).
    This makes it much easier to test and serialize and deserialize!
    """

    description: str
    title: str
    id: Optional[str] = None

    @classmethod
    def from_jira_doc(cls, doc: JiraDocument) -> JiraTicketText:
        # Remove Shake-to-Report metadata and parent issue descriptions from the child ticket descriptions
        # before sending to ai-completions-backend.
        description = strip_parent_description(extract_duolingo_metadata_and_body(doc.body_text)[0])

        return cls(description=description, id=doc.issue_key, title=doc.header_text)

    @classmethod
    def from_json(cls, json_str: str) -> JiraTicketText:
        # Sanitize all control characters from JSON string before parsing
        json_str = re.sub(r"[\x00-\x1F\x7F-\x9F]", " ", json_str)
        data = json.loads(json_str)
        return cls(description=data[RESP_DESCRIPTION], title=data[RESP_TITLE])

    def to_yaml(self) -> str:
        return (
            f"{REQ_ID}: {self.id}\n{REQ_TITLE}: {self.title}\n{REQ_DESCRIPTION}: {self.description}"
        )

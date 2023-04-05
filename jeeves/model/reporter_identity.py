from dataclasses import dataclass

from jeeves.model.appfigures_document import AppfiguresDocument
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.jira_document import JiraDocument
from jeeves.model.zendesk_document import ZendeskDocument


@dataclass(eq=True, frozen=True)
class ReporterIdentity:
    """Class for keeping track of a reporter's identity across various attributes."""

    author: str = None
    reporter: str = None
    requester_id: int = None
    username: str = None
    user_id: int = None

    @classmethod
    def from_doc(cls, doc: JeevesDocument) -> "ReporterIdentity":
        if doc.get_data_source_identifier() == JiraDocument.get_data_source_identifier():
            return cls(reporter=doc.reporter, username=doc.username, user_id=doc.user_id)
        elif doc.get_data_source_identifier() == ZendeskDocument.get_data_source_identifier():
            return cls(requester_id=doc.requester_id, username=doc.username, user_id=doc.user_id)
        elif doc.get_data_source_identifier() == AppfiguresDocument.get_data_source_identifier():
            return cls(author=doc.author, username=doc.username, user_id=doc.user_id)
        else:
            return cls(username=doc.username, user_id=doc.user_id)

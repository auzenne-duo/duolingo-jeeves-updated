import unittest
from typing import Any, Dict, Mapping

from jeeves.model.jira_document import JiraDocument
from jeeves.model.jira_ticket_text import JiraTicketText


def create_jira_document(args: Mapping[str, Any]) -> JiraDocument:
    """
    Creates a new JiraDocument with the attributes provided in the function argument.
    """
    attributes: Dict[str, Any] = {
        "app_version": None,
        "area": None,
        "assignee": None,
        "attachments": None,
        "child_issues": None,
        "codebase": None,
        "comments": [],
        "components": None,
        "course": None,
        "creation_date": None,
        "data_source": "JIRA",
        "date_time": None,
        "document_id": None,
        "duolingo_metadata": None,
        "experiment_conditions": None,
        "feature": None,
        "feature_url": "https://www.duolingo.com",
        "fullstory_url": None,
        "is_dev_related": None,
        "issue_links": None,
        "issue_type": None,
        "jeeves_uid": None,
        "jira_attachments": None,
        "labels": None,
        "language": None,
        "linked_duplicate_keys": None,
        "links": None,
        "os_version": None,
        "parent_issue": None,
        "platform": None,
        "priority": None,
        "project": None,
        "reporter": None,
        "reporter_email": None,
        "resolution": None,
        "resolution_date": None,
        "screen_content": None,
        "screen_size": None,
        "shake_to_report_category": "INTERNAL",
        "status": None,
        "team": None,
        "ui_language": None,
        "updated_date": None,
        "username": None,
    }
    attributes.update(args)
    return JiraDocument.deserialize_from_internal_json(attributes)


class TestJiraTicketText(unittest.TestCase):
    def test_to_yaml(self) -> None:
        """
        Tests that the generate_summary_user_prompt function generates the correct
        prompt for the Tutors service.
        """
        ticket = JiraTicketText(description="Description 1", id="DLAI-101", title="Header 1")

        yaml = ticket.to_yaml()
        assert yaml == "ID: DLAI-101\nTITLE: Header 1\nDESCRIPTION: Description 1"

    def test_from_json(self) -> None:
        json = """\
{
    "description": "Description 2",
    "title": "Header 2"
}
    """
        ticket2 = JiraTicketText.from_json(json)
        assert ticket2.description == "Description 2"
        assert ticket2.title == "Header 2"

    def test_from_jira_doc(self) -> None:
        doc = create_jira_document(
            {"body_text": "Body text 3", "header_text": "Header 3", "issue_key": "DLAI-103"}
        )

        ticket = JiraTicketText.from_jira_doc(doc)
        assert ticket.description == "Body text 3"
        assert ticket.title == "Header 3"
        assert ticket.id == "DLAI-103"


if __name__ == "__main__":
    unittest.main()

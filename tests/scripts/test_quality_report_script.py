import unittest
from datetime import datetime
from typing import Dict, List
from unittest.mock import MagicMock, patch

from jeeves.model.jira_document import JiraDocument
from jeeves.model.jira_duplicate_graph import JiraDuplicateGraph
from jeeves.model.shake_to_report_category import ShakeToReportCategory
from jeeves.scripts.quality_report_script import resolve_duplicate_graphs, search_for_issues
from jeeves.util.date_util import parse_external_datetime
from jeeves.util.quality_report_priority import get_quality_report_priority

JiraDocument.set_feature_field_key("feature_field")

JIRA_EXTERNAL_JSON_1 = {
    "id": "",
    "key": "DLAI-2001",
    "fields": {
        "description": {
            "type": "text",
            "text": "Reported with shake-to-report \n View Controller Name: \n VCActivity\nSystem Information:\nplatform:iOS",
        },
        "summary": "",
        "course": "",
        "fullstory_url": "",
        "os_version": "",
        "ui_language": "",
        "username": "",
        "key": "",
        "project": {"key": "DLAI"},
        "created": "2022-09-09",
        "updated": "2022-09-09",
        "status": {"statusCategory": {"name": "Done"}},
        "components": [],
        "feature_field": {"value": "Onboarding", "self": "Onboarding"},
        "priority": {"name": "Medium"},
        "reporter": {"displayName": ""},
        "labels": [],
        "resolutiondate": "",
        "resolution": "",
        "assignee": "",
    },
}

JIRA_EXTERNAL_JSON_2 = {
    "id": "",
    "key": "DLAA-2002",
    "fields": {
        "id": "",
        "description": "",
        "summary": "",
        "course": "",
        "fullstory_url": "",
        "os_version": "",
        "platform": "",
        "screen_size": "",
        "screen_content": "VCActivity",
        "ui_language": "",
        "username": "",
        "project": {"key": "DLAI"},
        "created": "2022-09-09",
        "updated": "2022-09-09",
        "status": {"statusCategory": {"name": "To Do"}},
        "components": [],
        "feature_field": {"value": "DarkMode", "self": "DarkMode"},
        "priority": {"name": "Low"},
        "reporter": {"displayName": ""},
        "labels": [],
        "resolutiondate": "",
        "resolution": "",
        "assignee": "",
    },
}


def create_jira_doc(
    issue_key,
    feature,
    status,
    priority,
    linked_duplicate_keys,
    duolingo_metadata=None,
    labels=None,
    body_text="",
    str_category=ShakeToReportCategory.INTERNAL,
):
    if labels is None:
        labels = []
    if duolingo_metadata is None:
        duolingo_metadata = {}
    datetime = parse_external_datetime("2022-09-09")
    return JiraDocument(
        issue_key=issue_key,
        project=issue_key[:4],
        linked_duplicate_keys=linked_duplicate_keys,
        creation_date=datetime,
        updated_date=datetime,
        resolution_date=None,
        status=status,
        feature=feature,
        priority=get_quality_report_priority(priority),
        reporter="",
        reporter_email="",
        assignee="UNASSIGNED",
        comments=[],
        labels=labels,
        embedding_vector=[],
        data_source="JIRA",
        document_id="",
        jeeves_uid="JIRA_",
        date_time=datetime,
        body_text=body_text,
        language="en",
        shake_to_report_category=str_category,
        attachments=[],
        duolingo_metadata=duolingo_metadata,
        app_version="",
        course="",
        fullstory_url="",
        os_version="",
        platform="iOS",
        screen_size="",
        screen_content="VCActivity",
        ui_language="",
        username="",
        issue_links=[],
        issue_type="",
        resolution="",
        components=[],
        feature_url="Onboarding",
        experiment_conditions={},
        jira_attachments=[],
    )


METADATA_1 = {
    "view_controller_name": "VCActivity",
    "system_information": {"platform": "iOS"},
    "raw": "platform:iOS",
}
PARSED_JIRA_DOCUMENT_1 = create_jira_doc(
    "DLAI-2001", "Onboarding", "Done", "Medium", [], METADATA_1, body_text="\n"
)
PARSED_JIRA_DOCUMENT_1.is_done = True

PARSED_JIRA_DOCUMENT_2 = create_jira_doc(
    "DLAA-2002", "DarkMode", "Done", "Low", [], str_category=ShakeToReportCategory.NON_STR_INTERNAL
)
PARSED_JIRA_DOCUMENT_2.is_done = False

JIRA_DOCUMENT_1 = create_jira_doc("DLAI-2001", "Onboarding", "Done", "Medium", ["DLAI-2004"])
JIRA_DOCUMENT_1.is_done = True

JIRA_DOCUMENT_2 = create_jira_doc("DLAI-2002", "DarkMode", "Done", "Low", ["DLAI-2003"])
JIRA_DOCUMENT_2.is_done = False

JIRA_DOCUMENT_3 = create_jira_doc(
    "DLAI-2003", "DarkMode", "Done", "Medium", ["DLAI-2002"], labels=["parent_bug"]
)
JIRA_DOCUMENT_3.is_done = True

JIRA_DOCUMENT_4 = create_jira_doc(
    "DLAI-2004", "DarkMode", "Done", "High", ["DLAI-2001", "DLAI-2005"]
)
JIRA_DOCUMENT_4.is_done = True

JIRA_DOCUMENT_5 = create_jira_doc(
    "DLAI-2005", "DarkMode", "To Do", "Medium", ["DLAI-2001", "DLAI-2004"]
)
JIRA_DOCUMENT_5.is_done = False


def document_copy(jira_document):
    copy = create_jira_doc(
        jira_document.issue_key,
        jira_document.feature,
        jira_document.status,
        "Low",
        jira_document.linked_duplicate_keys,
        jira_document.labels,
    )
    copy.priority = jira_document.priority
    copy.is_done = jira_document.is_done
    return copy


mock_jira_manager = MagicMock()
mock_jira_manager.download_bulk_issues_with_features = lambda keys: [
    JIRA_DOCUMENT_4,
    JIRA_DOCUMENT_5,
]


class TestQualityReportScript(unittest.TestCase):
    @patch("jeeves.scripts.quality_report_script.JiraDAL")
    @patch("jeeves.scripts.quality_report_script.JiraManager")
    def test_search_for_issues(self, MockJiraManager, MockJiraDAL):
        MockJiraDAL.paginate_search_issues.return_value = (
            issue for issue in [JIRA_EXTERNAL_JSON_1]
        )
        MockJiraManager.get_feature_field.return_value = "feature_field"

        result = search_for_issues(datetime(2001, 1, 1), datetime(2001, 2, 1))
        expected = [PARSED_JIRA_DOCUMENT_1]
        self.assertEqual(result, expected)

    @patch(
        "jeeves.scripts.quality_report_script.IDManagerMap",
        MagicMock(get_manager_for_identifier=MagicMock(return_value=mock_jira_manager)),
    )
    @patch("jeeves.scripts.quality_report_script.app_registry")
    def test_resolve_duplicate_graphs(self, mock_app_registry):
        def mock_get_duplicate_graph(
            issues: List[JiraDocument], key_to_doc: Dict[str, JiraDocument]
        ):
            if issues[0] in ["DLAI-2002", "DLAI-2003"]:
                return JiraDuplicateGraph(
                    issue_keys_to_documents={
                        "DLAI-2002": JIRA_DOCUMENT_2,
                        "DLAI-2003": JIRA_DOCUMENT_3,
                    },
                    existing_issue_links=set(),
                )
            else:
                return JiraDuplicateGraph(
                    issue_keys_to_documents={
                        "DLAI-2001": JIRA_DOCUMENT_1,
                        "DLAI-2004": JIRA_DOCUMENT_4,
                        "DLAI-2005": JIRA_DOCUMENT_5,
                    },
                    existing_issue_links=set(),
                )

        mock_app_registry.return_value.get_duplicate_graph.side_effect = mock_get_duplicate_graph
        result = resolve_duplicate_graphs([JIRA_DOCUMENT_1, JIRA_DOCUMENT_2, JIRA_DOCUMENT_3])
        expected_key_to_issue = {
            "DLAI-2001": JIRA_DOCUMENT_1,
            "DLAI-2002": JIRA_DOCUMENT_2,
            "DLAI-2003": JIRA_DOCUMENT_3,
            "DLAI-2004": JIRA_DOCUMENT_4,
            "DLAI-2005": JIRA_DOCUMENT_5,
        }
        self.assertEqual(result[1], expected_key_to_issue)
        self.assertEqual({issue.issue_key for issue in result[0]}, {"DLAI-2003", "DLAI-2005"})

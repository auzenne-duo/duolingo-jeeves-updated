import unittest
from typing import Dict, List
from unittest.mock import MagicMock, patch

from jeeves.model.jira_document import JiraDocument
from jeeves.model.jira_duplicate_graph import JiraDuplicateGraph
from jeeves.model.shake_to_report_category import ShakeToReportCategory
from jeeves.scripts.index_pipeline_and_spike_detector.sync_jira_tickets import (
    resolve_duplicate_graphs,
    search_for_issues,
    update_dev_related_issues,
)
from tests.testutil.test_util_quality_report import create_jira_doc

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
        "resolution": {"name": "Done"},
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
        "resolution": {"name": "Unresolved"},
        "assignee": "",
    },
}


METADATA_1 = {
    "view_controller_name": "VCActivity",
    "system_information": {"platform": "iOS"},
    "raw": "platform:iOS",
}
PARSED_JIRA_DOCUMENT_1 = create_jira_doc(
    "DLAI-2001",
    "Onboarding",
    "Done",
    "Medium",
    [],
    METADATA_1,
    body_text="\n",
    status="Done",
    area="Growth",
    team="Onboarding",
)
PARSED_JIRA_DOCUMENT_1.priority = "Medium"

PARSED_JIRA_DOCUMENT_2 = create_jira_doc(
    "DLAA-2002",
    "DarkMode",
    "Done",
    "Low",
    [],
    str_category=ShakeToReportCategory.NON_STR_INTERNAL,
    status="To Do",
)
PARSED_JIRA_DOCUMENT_2.priority = "Low"

JIRA_DOCUMENT_1 = create_jira_doc("DLAI-2001", "Onboarding", "Done", "Medium", ["DLAI-2004"])

JIRA_DOCUMENT_2 = create_jira_doc(
    "DLAI-2002",
    "DarkMode",
    "Done",
    "Low",
    ["DLAI-2003"],
    issue_links=[{"type": {"name": ["Relates"]}, "outwardIssue": {"key": "DLAI-2003"}}],
)

JIRA_DOCUMENT_3 = create_jira_doc(
    "DLAI-2003",
    "DarkMode",
    "Done",
    "Medium",
    ["DLAI-2002"],
    labels=["parent_bug"],
    issue_links=[{"type": {"name": ["Relates"]}, "inwardIssue": {"key": "DLAI-2005"}}],
    issue_type="Bug",
)

JIRA_DOCUMENT_4 = create_jira_doc(
    "DLAI-2004", "DarkMode", "Done", "High", ["DLAI-2001", "DLAI-2005"]
)

JIRA_DOCUMENT_5 = create_jira_doc(
    "DLAI-2005",
    "DarkMode",
    "Unresolved",
    "Medium",
    ["DLAI-2001", "DLAI-2004"],
    issue_type="Not a bug",
)


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
    @patch("jeeves.scripts.index_pipeline_and_spike_detector.sync_jira_tickets.JiraDAL")
    @patch("jeeves.scripts.index_pipeline_and_spike_detector.sync_jira_tickets.JiraManager")
    def test_search_for_issues(self, MockJiraManager, MockJiraDAL):
        MockJiraDAL.paginate_search_issues.return_value = (
            issue for issue in [JIRA_EXTERNAL_JSON_1]
        )
        MockJiraManager.get_feature_field.return_value = "feature_field"

        result = search_for_issues()
        expected = [PARSED_JIRA_DOCUMENT_1]
        self.assertEqual(result, expected)

    @patch(
        "jeeves.scripts.index_pipeline_and_spike_detector.sync_jira_tickets.IDManagerMap",
        MagicMock(get_manager_for_identifier=MagicMock(return_value=mock_jira_manager)),
    )
    @patch("jeeves.scripts.index_pipeline_and_spike_detector.sync_jira_tickets.app_registry")
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

        # Document 5 is the parent of 1 and 4 since it is the only one open
        self.assertEqual(
            JIRA_DOCUMENT_5.child_issues, [JIRA_DOCUMENT_1.issue_key, JIRA_DOCUMENT_4.issue_key]
        )
        self.assertEqual(JIRA_DOCUMENT_1.parent_issue, JIRA_DOCUMENT_5.issue_key)
        self.assertEqual(JIRA_DOCUMENT_4.parent_issue, JIRA_DOCUMENT_5.issue_key)
        # Document 3 is the parent of 2 according to the parent-bug label
        self.assertEqual(JIRA_DOCUMENT_3.child_issues, [JIRA_DOCUMENT_2.issue_key])
        self.assertEqual(JIRA_DOCUMENT_2.parent_issue, JIRA_DOCUMENT_3.issue_key)

        self.assertEqual(result, expected_key_to_issue)

    @patch(
        "jeeves.scripts.index_pipeline_and_spike_detector.sync_jira_tickets.IDManagerMap",
        MagicMock(get_manager_for_identifier=MagicMock(return_value=mock_jira_manager)),
    )
    def test_filter_dev_issues(self):
        update_dev_related_issues(
            [JIRA_DOCUMENT_1, JIRA_DOCUMENT_2, JIRA_DOCUMENT_3],
            {
                "DLAI-2001": JIRA_DOCUMENT_1,
                "DLAI-2002": JIRA_DOCUMENT_2,
                "DLAI-2003": JIRA_DOCUMENT_3,
            },
        )
        # JIRA_DOCUMENT_3 is related to a dev issue (JIRA_DOCUMENT_5)
        self.assertEqual(JIRA_DOCUMENT_1.is_dev_related, False)
        self.assertEqual(JIRA_DOCUMENT_2.is_dev_related, False)
        self.assertEqual(JIRA_DOCUMENT_3.is_dev_related, True)

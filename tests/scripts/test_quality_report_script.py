import unittest
from datetime import datetime
from typing import Dict, List
from unittest.mock import MagicMock, patch

from jeeves.model.jira_document import JiraDocument
from jeeves.model.jira_duplicate_graph import JiraDuplicateGraph
from jeeves.model.shake_to_report_category import ShakeToReportCategory
from jeeves.scripts.quality_report_script import (
    filter_dev_issues,
    generate_and_save_pdf,
    resolve_duplicate_graphs,
    search_for_issues,
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
    @patch("jeeves.scripts.quality_report_script.JiraDAL")
    @patch("jeeves.scripts.quality_report_script.JiraManager")
    def test_search_for_issues(self, MockJiraManager, MockJiraDAL):
        MockJiraDAL.paginate_search_issues.return_value = (
            issue for issue in [JIRA_EXTERNAL_JSON_1]
        )
        MockJiraManager.get_feature_field.return_value = "feature_field"

        result = search_for_issues(datetime(2001, 1, 1))
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

        self.assertEqual(result[0], {"DLAI-2003", "DLAI-2005"})
        self.assertEqual(result[1], expected_key_to_issue)

    @patch(
        "jeeves.scripts.quality_report_script.IDManagerMap",
        MagicMock(get_manager_for_identifier=MagicMock(return_value=mock_jira_manager)),
    )
    def test_filter_dev_issues(self):
        result = filter_dev_issues(
            ["DLAI-2001", "DLAI-2002", "DLAI-2003"],
            {
                "DLAI-2001": JIRA_DOCUMENT_1,
                "DLAI-2002": JIRA_DOCUMENT_2,
                "DLAI-2003": JIRA_DOCUMENT_3,
            },
        )
        expected = sorted([JIRA_DOCUMENT_1, JIRA_DOCUMENT_2])
        self.assertEqual(sorted(result), expected)

    @patch("jeeves.scripts.quality_report_script.makepdf", MagicMock(return_value="pdf"))
    @patch("jeeves.scripts.quality_report_script.send_email")
    @patch("jeeves.scripts.quality_report_script.upload_to_internal_static")
    @patch("jeeves.scripts.quality_report_script.upload_to_jeeves_s3")
    def test_generate_and_save_pdf(self, mock_upload_s3, mock_upload_static, mock_send_email):
        report = MagicMock(title="title", end_data=datetime(2001, 1, 1))
        generate_and_save_pdf(report)
        assert not mock_upload_s3.called
        assert not mock_upload_static.called
        assert not mock_send_email.called

        generate_and_save_pdf(report, send_emails=True)
        assert not mock_upload_s3.called
        assert not mock_upload_static.called
        mock_send_email.assert_called_once_with(report)

        generate_and_save_pdf(report, dry_run=False, send_emails=True)
        s3_expected_path = f"quality_reports/{report.title}/quality_report_{report.title.lower()}_{report.end_date.strftime('%Y_%m_%d')}.pdf"
        internal_expected_path = f"delight/{s3_expected_path}"
        mock_upload_s3.assert_called_once_with(s3_expected_path, "pdf")
        mock_upload_static.assert_called_once_with(internal_expected_path, "pdf")
        mock_send_email.assert_called_with(report)

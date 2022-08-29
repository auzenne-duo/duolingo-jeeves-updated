import unittest
from datetime import datetime
from typing import List
from unittest.mock import MagicMock, patch

import pytest

from jeeves.dal.elasticsearch_interface import ElasticsearchDAL
from jeeves.dal.jira_dal import JiraApiDAL
from jeeves.manager.duplicate_graph_resolver import DuplicateGraphResolver
from jeeves.model.jira_document import JiraDocument
from jeeves.model.shake_to_report_category import ShakeToReportCategory
from jeeves.util.date_util import get_n_days_ago
from jeeves.util.priority_estimator import JiraPriority

mock_es_dal = ElasticsearchDAL()
mock_jira_dal = JiraApiDAL()

now_datetime = datetime.now()
yesterday_datetime = get_n_days_ago(now_datetime, 1)


def _jira_document(
    issue_number,
    status="To Do",
    resolution="",
    updated_date=now_datetime,
    linked_duplicate_keys=None,
    labels=None,
    feature="",
    header_text="I am a header",
):
    doc = JiraDocument(
        data_source="JIRA",
        document_id="doc1",
        jeeves_uid="uid1",
        date_time=updated_date,
        header_text=header_text,
        body_text="I am body text",
        language="en",
        links=[],
        shake_to_report_category=ShakeToReportCategory.EXTERNAL,
        attachments=[],
        duolingo_metadata={},
        app_version="",
        course="",
        fullstory_url="",
        os_version="",
        platform="",
        screen_size="",
        screen_content="",
        ui_language="",
        username="",
        issue_key=f"DLAA-{issue_number}",
        issue_links=[],
        issue_type="Bug",
        project="DLAA",
        linked_duplicate_keys=linked_duplicate_keys if linked_duplicate_keys else [],
        creation_date=updated_date,
        updated_date=updated_date,
        resolution_date=None,
        status=status,
        resolution="",
        components=[],
        feature_url="",
        feature=feature,
        priority="High",
        reporter="",
        reporter_email="",
        assignee="",
        comments=[],
        labels=labels if labels else [],
        embedding_vector=[],
    )
    issue_number += 1
    return doc


parent_todo_today = _jira_document(issue_number=1)
parent_todo_yesterday = _jira_document(issue_number=2, updated_date=yesterday_datetime)

parent_inprogress_today = _jira_document(issue_number=3, status="In Progress")
parent_inprogress_yesterday = _jira_document(
    issue_number=4, status="In Progress", updated_date=yesterday_datetime
)

parent_resolved_today = _jira_document(issue_number=5, status="Done", resolution="Duplicate")
parent_resolved_yesterday = _jira_document(
    issue_number=6, status="Done", resolution="Duplicate", updated_date=yesterday_datetime
)

test_cases = [
    # Favor in-progress issues
    (
        [
            parent_todo_today,
            parent_resolved_today,
            parent_inprogress_today,
            parent_inprogress_yesterday,
        ],
        parent_inprogress_today,
        [parent_todo_today, parent_resolved_today, parent_inprogress_yesterday],
    ),
    # Favor to-do issues over done issues
    (
        [
            parent_todo_yesterday,
            parent_todo_today,
            parent_resolved_yesterday,
            parent_resolved_today,
        ],
        parent_todo_today,
        [parent_todo_yesterday, parent_resolved_yesterday, parent_resolved_today],
    ),
    # Choose the most recent issue
    (
        [parent_resolved_yesterday, parent_resolved_today],
        parent_resolved_today,
        [parent_resolved_yesterday],
    ),
]


@pytest.mark.parametrize("parent_issues,expected_parent,expected_other_parents", test_cases)
def test_choose_parent_issue(
    parent_issues: List[JiraDocument],
    expected_parent: JiraDocument,
    expected_other_parents: List[JiraDocument],
):
    duplicate_graph_resolver = DuplicateGraphResolver(mock_es_dal, mock_jira_dal)

    (
        actual_parent_issue_key,
        actual_other_parent_issues,
    ) = duplicate_graph_resolver.choose_parent_issue(parent_issues)
    case = unittest.TestCase()
    assert actual_parent_issue_key == expected_parent.issue_key
    case.assertCountEqual(
        [issue.issue_key for issue in actual_other_parent_issues],
        [issue.issue_key for issue in expected_other_parents],
    )


parent_of_dupes = _jira_document(
    issue_number=1, linked_duplicate_keys=["DLAA-2"], labels=["parent_bug"]
)
child_2 = _jira_document(issue_number=2, linked_duplicate_keys=["DLAA-1", "DLAA-3"])
child_3 = _jira_document(issue_number=3, linked_duplicate_keys=["DLAA-2"])
no_dupes = _jira_document(issue_number=4, feature="shake", header_text="site is crashing")
no_parent_5 = _jira_document(
    issue_number=5,
    linked_duplicate_keys=["DLAA-6"],
    feature="achievements",
    header_text="site crashed",
)
no_parent_6 = _jira_document(issue_number=6, linked_duplicate_keys=["DLAA-5"], feature="shake")
jira_documents = {
    "DLAA-1": parent_of_dupes,
    "DLAA-2": child_2,
    "DLAA-3": child_3,
    "DLAA-4": no_dupes,
    "DLAA-5": no_parent_5,
    "DLAA-6": no_parent_6,
}


mock_jira_manager = MagicMock()
mock_jira_manager.download_bulk_issues_with_features = lambda keys: [
    jira_documents[key] for key in keys
]

populate_parent_child_issue_fields_test_cases = [
    (parent_of_dupes, None, ["DLAA-2", "DLAA-3"]),
    (child_2, "DLAA-1", None),
    (child_3, "DLAA-1", None),
    (no_dupes, None, None),
    (no_parent_6, None, None),
]


@pytest.mark.parametrize(
    "jira_doc,expected_parent_issue,expected_child_issues",
    populate_parent_child_issue_fields_test_cases,
)
@patch(
    "jeeves.manager.duplicate_graph_resolver.IDManagerMap",
    MagicMock(get_manager_for_identifier=MagicMock(return_value=mock_jira_manager)),
)
def test_populate_parent_child_issue_fields(
    jira_doc: JiraDocument,
    expected_parent_issue: str,
    expected_child_issues: List[str],
):
    mock_jira_manager.download_bulk_issues_with_features = lambda keys: [
        jira_documents[key] for key in keys
    ]
    duplicate_graph_resolver = DuplicateGraphResolver(mock_es_dal, mock_jira_dal)

    duplicate_graph_resolver.populate_parent_child_issue_fields([jira_doc])
    unittest.TestCase()
    assert jira_doc.parent_issue == expected_parent_issue
    assert jira_doc.child_issues == expected_child_issues


class TestDuplicateGraphResolver(unittest.TestCase):
    @patch(
        "jeeves.manager.duplicate_graph_resolver.IDManagerMap",
        MagicMock(get_manager_for_identifier=MagicMock(return_value=mock_jira_manager)),
    )
    def test_connect_duplicates_remote(self):
        magic_mock_jira_dal = MagicMock()
        magic_mock_jira_dal.get_issue.return_value = MagicMock(
            body_text="APP VERSIONS:\nNOT PRESENT: 2\n6.117.0.1: 1\n\n\nPLATFORMS:\nNOT PRESENT: 2\niOS: 1\n\n\nCOURSES:\nNOT PRESENT: 2\nDUOLINGO_FR_EN: 1\n\n\nINTERFACE LANGUAGES:\nNOT PRESENT: 2\nen: 1\n\n\nOPERATING SYSTEMS:\nNOT PRESENT: 2\niOS 14.4.1: 1\n\n\nAREAS:\n\n"
        )
        magic_mock_jira_dal.create_bug_issue.return_value = "parent_key"

        duplicate_graph_resolver = DuplicateGraphResolver(mock_es_dal, magic_mock_jira_dal)
        duplicate_graph_resolver.connect_duplicates_remote(["DLAA-4", "DLAA-5"])
        expected_description = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "APP VERSIONS:\nNOT PRESENT: 5\n6.117.0.1: 1\n"}
                    ],
                },
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "PLATFORMS:\nNOT PRESENT: 5\niOS: 1\n"}],
                },
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "COURSES:\nNOT PRESENT: 5\nDUOLINGO_FR_EN: 1\n"}
                    ],
                },
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "INTERFACE LANGUAGES:\nNOT PRESENT: 5\nen: 1\n"}
                    ],
                },
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "OPERATING SYSTEMS:\nNOT PRESENT: 5\niOS 14.4.1: 1\n",
                        }
                    ],
                },
                {"type": "paragraph", "content": [{"type": "text", "text": "AREAS:\n"}]},
            ],
        }
        magic_mock_jira_dal.update_issue.assert_any_call(
            "parent_key",
            description=expected_description,
            feature="shake",
            priority=JiraPriority.HIGH.value,
        )

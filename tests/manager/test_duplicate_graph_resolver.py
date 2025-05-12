import unittest
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from unittest.mock import MagicMock, patch

import pytest

from jeeves.dal.jira_dal import JiraApiDAL
from jeeves.dal.opensearch_interface import OpenSearchDAL
from jeeves.manager.duplicate_graph_resolver import (
    DuplicateGraphOperationResults,
    DuplicateGraphResolver,
)
from jeeves.manager.parent_summary_manager import JiraTicketText
from jeeves.model.jira_document import JiraDocument
from jeeves.model.jira_duplicate_graph import JiraDuplicateGraph, JiraDuplicateGraphOperationStatus
from jeeves.model.shake_to_report_category import ShakeToReportCategory
from jeeves.util.date_util import get_n_days_ago

mock_es_dal = OpenSearchDAL()
mock_jira_dal = JiraApiDAL()
mock_parent_summary_generator = MagicMock()

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
        embeddings={},
        experiment_conditions={},
        jira_attachments=[],
        parent_issue=None,
        child_issues=[],
        is_dev_related=False,
        pillar="",
        area="",
        team="",
        codebase="",
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
    duplicate_graph_resolver = DuplicateGraphResolver(
        mock_es_dal, mock_jira_dal, mock_jira_manager, mock_parent_summary_generator
    )

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
no_parent_6 = _jira_document(
    issue_number=6,
    linked_duplicate_keys=["DLAA-5"],
    feature="shake",
    status="Done",
    resolution="Duplicate",
)
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


MOCK_SUMMARY = "Summary"
MOCK_DESCRIPTION = "Description"


class TestDuplicateGraphResolver(unittest.TestCase):
    @patch("jeeves.manager.duplicate_graph_resolver.asyncio", MagicMock())
    @patch("jeeves.manager.duplicate_graph_resolver.get_asyncio_loop")
    def test_connect_duplicates_remote(self, mock_get_asyncio_loop):
        expected_links = {
            ("DLAA-5", "parent_key"),
            ("DLAA-6", "parent_key"),
            ("DLAA-4", "parent_key"),
        }
        asyncio_return = [(inward, outward, True) for inward, outward in expected_links]
        mock_get_asyncio_loop.return_value.run_until_complete.return_value = asyncio_return
        magic_mock_jira_dal = MagicMock()
        parent_issue = MagicMock(
            body_text="Random description someone entered\nAPP VERSIONS:\nNOT PRESENT: 2\n6.117.0.1: 1\n\n\nPLATFORMS:\nNOT PRESENT: 2\niOS: 1\n\n\nCOURSES:\nNOT PRESENT: 2\nDUOLINGO_FR_EN: 1\n\n\nINTERFACE LANGUAGES:\nNOT PRESENT: 2\nen: 1\n\n\nOPERATING SYSTEMS:\nNOT PRESENT: 2\niOS 14.4.1: 1\n\n\nAREAS:\n\n"
        )
        magic_mock_jira_dal.get_issue.return_value = parent_issue
        magic_mock_jira_dal.create_bug_issue.return_value = "parent_key"

        mock_response = JiraTicketText(description=MOCK_DESCRIPTION, title=MOCK_SUMMARY)
        mock_parent_summary_generator.generate_summary_and_description.return_value = mock_response

        duplicate_graph_resolver = DuplicateGraphResolver(
            mock_es_dal, magic_mock_jira_dal, mock_jira_manager, mock_parent_summary_generator
        )
        duplicate_graph_resolver.connect_duplicates_remote(["DLAA-4", "DLAA-5"])
        expected_summary = f"[Parent] {MOCK_SUMMARY}"
        expected_description = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": f"{MOCK_DESCRIPTION}\n\n"}],
                },
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "APP VERSIONS:\n6.117.0.1: 1\nNOT PRESENT: 5\n"}
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
            summary=expected_summary,
            description=expected_description,
            feature="shake",
            priority="High",
        )
        magic_mock_jira_dal.mark_duplicates_async.assert_any_call(expected_links)

        # Test with an existing [Parent] already in the summary
        parent_issue = MagicMock(
            body_text="Random description someone entered\nAPP VERSIONS:\nNOT PRESENT: 2\n6.117.0.1: 1\n\n\nPLATFORMS:\nNOT PRESENT: 2\niOS: 1\n\n\nCOURSES:\nNOT PRESENT: 2\nDUOLINGO_FR_EN: 1\n\n\nINTERFACE LANGUAGES:\nNOT PRESENT: 2\nen: 1\n\n\nOPERATING SYSTEMS:\nNOT PRESENT: 2\niOS 14.4.1: 1\n\n\nAREAS:\n\n",
            summary="[Parent] Parent Issue",
        )
        magic_mock_jira_dal.reset_mock()
        magic_mock_jira_dal.get_issue.return_value = parent_issue
        duplicate_graph_resolver.connect_duplicates_remote(["DLAA-4", "DLAA-5"])
        magic_mock_jira_dal.update_issue.assert_any_call(
            "parent_key",
            summary=expected_summary,
            description=expected_description,
            feature="shake",
            priority="High",
        )

    @patch("jeeves.scripts.index_pipeline_and_spike_detector.sync_jira_tickets.app_registry")
    def test_resolve_duplicate_graphs(self, mock_app_registry):
        magic_mock_jira_dal = MagicMock()
        duplicate_graph_resolver = DuplicateGraphResolver(
            mock_es_dal, magic_mock_jira_dal, mock_jira_manager, mock_parent_summary_generator
        )
        list_of_parents, key_to_issue = duplicate_graph_resolver.resolve_duplicate_graphs(
            [parent_of_dupes, child_2, no_parent_5]
        )
        expected_key_to_issue = {
            "DLAA-1": parent_of_dupes,
            "DLAA-2": child_2,
            "DLAA-3": child_3,
            "DLAA-5": no_parent_5,
            "DLAA-6": no_parent_6,
        }
        expected_list_of_parents = [
            parent_of_dupes,
            no_parent_5,
        ]

        # Document DLAA-1 is the parent of DLAA-2 and DLAA-3 according to the parent-bug label
        self.assertEqual(parent_of_dupes.child_issues, [child_2.issue_key, child_3.issue_key])
        self.assertEqual(child_2.parent_issue, parent_of_dupes.issue_key)
        self.assertEqual(child_3.parent_issue, parent_of_dupes.issue_key)
        # Document DLAA-5 is the parent of DLAA-6 since DLAA-6 is closed as duplicate while DLAA-5 is open
        self.assertEqual(no_parent_5.child_issues, [no_parent_6.issue_key])
        self.assertEqual(no_parent_6.parent_issue, no_parent_5.issue_key)

        self.assertEqual(key_to_issue, expected_key_to_issue)
        self.assertEqual(list_of_parents, expected_list_of_parents)


@pytest.mark.parametrize(
    ("graph", "expected_results"),
    (
        pytest.param(
            {
                ("0", "1"): "1",
                ("1", "2"): "2",
                ("2", "3"): "3",
            },
            DuplicateGraphOperationResults(
                status=JiraDuplicateGraphOperationStatus.SUCCESS,
                edge_failures=[],
                edge_successes=[("0", "1"), ("1", "2"), ("2", "3")],
            ),
            id="path_graph",
        ),
        pytest.param(
            {
                ("0", "1"): "1",
                ("1", "2"): "2",
                ("2", "3"): "3",
                ("3", "1"): "4",
            },
            DuplicateGraphOperationResults(
                status=JiraDuplicateGraphOperationStatus.SUCCESS,
                edge_failures=[],
                edge_successes=[("0", "1"), ("1", "2"), ("2", "3"), ("3", "1")],
            ),
            id="cycle_graph",
        ),
        pytest.param(
            {
                ("0", "1"): "1",
                ("1", "0"): "2",
                ("1", "2"): "3",
                ("2", "1"): "4",
                ("2", "3"): "5",
                ("3", "2"): "6",
            },
            DuplicateGraphOperationResults(
                status=JiraDuplicateGraphOperationStatus.SUCCESS,
                edge_failures=[],
                edge_successes=[
                    ("0", "1"),
                    ("1", "0"),
                    ("1", "2"),
                    ("2", "1"),
                    ("2", "3"),
                    ("3", "2"),
                ],
            ),
            id="fully_connected_graph",
        ),
        pytest.param(
            {},
            DuplicateGraphOperationResults(
                status=JiraDuplicateGraphOperationStatus.SUCCESS,
                edge_failures=[],
                edge_successes=[],
            ),
            id="empty_graph",
        ),
    ),
)
def test_disconnect_duplicates_remote_jira_always_succeeds(
    graph: Dict[Tuple[str, str], str],
    expected_results: DuplicateGraphOperationResults,
) -> None:
    # Yield ID if it's in our graph
    def get_issue_link(_graph, vertex1: str, vertex2: str) -> Optional[str]:
        return {"id": graph[(vertex1, vertex2)]} if (vertex1, vertex2) in graph else None

    # Always return True for deletion
    def get_deletion_results(link_ids: List[str]) -> List[Tuple[str, bool]]:
        return [(link_id, True) for link_id in link_ids]

    resolver = DuplicateGraphResolver(
        mock_es_dal, mock_jira_dal, mock_jira_manager, mock_parent_summary_generator
    )
    duplicate_graph = JiraDuplicateGraph(
        issue_keys_to_documents={}, existing_issue_links=set(graph)
    )
    with patch.object(resolver, "_get_duplicate_issue_link", get_issue_link):
        with patch.object(resolver, "get_duplicate_graph", return_value=duplicate_graph):
            with patch.object(resolver, "_get_deletion_results", get_deletion_results):
                result = resolver.disconnect_duplicates_remote("foo")
    # Standardize order
    result["edge_failures"].sort()
    result["edge_successes"].sort()
    expected_results["edge_failures"].sort()
    expected_results["edge_successes"].sort()
    assert result == expected_results


@pytest.mark.parametrize(
    ("graph", "expected_results"),
    (
        pytest.param(
            {
                ("0", "1"): "1",
                ("1", "2"): "2",
                ("2", "3"): "3",
            },
            DuplicateGraphOperationResults(
                status=JiraDuplicateGraphOperationStatus.FAILURE,
                edge_failures=[("0", "1"), ("1", "2"), ("2", "3")],
                edge_successes=[],
            ),
            id="path_graph",
        ),
        pytest.param(
            {
                ("0", "1"): "1",
                ("1", "2"): "2",
                ("2", "3"): "3",
                ("3", "1"): "4",
            },
            DuplicateGraphOperationResults(
                status=JiraDuplicateGraphOperationStatus.FAILURE,
                edge_failures=[("0", "1"), ("1", "2"), ("2", "3"), ("3", "1")],
                edge_successes=[],
            ),
            id="cycle_graph",
        ),
        pytest.param(
            {
                ("0", "1"): "1",
                ("1", "0"): "2",
                ("1", "2"): "3",
                ("2", "1"): "4",
                ("2", "3"): "5",
                ("3", "2"): "6",
            },
            DuplicateGraphOperationResults(
                status=JiraDuplicateGraphOperationStatus.FAILURE,
                edge_failures=[
                    ("0", "1"),
                    ("1", "0"),
                    ("1", "2"),
                    ("2", "1"),
                    ("2", "3"),
                    ("3", "2"),
                ],
                edge_successes=[],
            ),
            id="fully_connected_graph",
        ),
        pytest.param(
            {},
            DuplicateGraphOperationResults(
                status=JiraDuplicateGraphOperationStatus.SUCCESS,
                edge_failures=[],
                edge_successes=[],
            ),
            id="empty_graph",
        ),
    ),
)
def test_disconnect_duplicates_remote_jira_always_fails(
    graph: Dict[Tuple[str, str], str],
    expected_results: DuplicateGraphOperationResults,
) -> None:
    # Yield ID if it's in our graph
    def get_issue_link(_graph, vertex1: str, vertex2: str) -> Optional[str]:
        return {"id": graph[(vertex1, vertex2)]} if (vertex1, vertex2) in graph else None

    # Always return True for deletion
    def get_deletion_results(link_ids: List[str]) -> List[Tuple[str, bool]]:
        return [(link_id, False) for link_id in link_ids]

    resolver = DuplicateGraphResolver(
        mock_es_dal, mock_jira_dal, mock_jira_manager, mock_parent_summary_generator
    )
    duplicate_graph = JiraDuplicateGraph(
        issue_keys_to_documents={}, existing_issue_links=set(graph)
    )
    with patch.object(resolver, "_get_duplicate_issue_link", get_issue_link):
        with patch.object(resolver, "get_duplicate_graph", return_value=duplicate_graph):
            with patch.object(resolver, "_get_deletion_results", get_deletion_results):
                result = resolver.disconnect_duplicates_remote("foo")
    # Standardize order
    result["edge_failures"].sort()
    result["edge_successes"].sort()
    expected_results["edge_failures"].sort()
    expected_results["edge_successes"].sort()
    assert result == expected_results


@pytest.mark.parametrize(
    ("graph", "expected_results"),
    (
        pytest.param(
            {
                ("0", "1"): "1",
                ("1", "2"): "2",
                ("2", "3"): "3",
            },
            DuplicateGraphOperationResults(
                status=JiraDuplicateGraphOperationStatus.PARTIAL,
                edge_failures=[("1", "2"), ("2", "3")],
                edge_successes=[("0", "1")],
            ),
            id="path_graph",
        ),
        pytest.param(
            {
                ("0", "1"): "1",
                ("1", "2"): "2",
                ("2", "3"): "3",
                ("3", "1"): "4",
            },
            DuplicateGraphOperationResults(
                status=JiraDuplicateGraphOperationStatus.PARTIAL,
                edge_failures=[("1", "2"), ("2", "3"), ("3", "1")],
                edge_successes=[("0", "1")],
            ),
            id="cycle_graph",
        ),
        pytest.param(
            {
                ("0", "1"): "1",
                ("1", "0"): "2",
                ("1", "2"): "3",
                ("2", "1"): "4",
                ("2", "3"): "5",
                ("3", "2"): "6",
            },
            DuplicateGraphOperationResults(
                status=JiraDuplicateGraphOperationStatus.PARTIAL,
                edge_failures=[("1", "0"), ("1", "2"), ("2", "1"), ("2", "3"), ("3", "2")],
                edge_successes=[("0", "1")],
            ),
            id="fully_connected_graph",
        ),
        pytest.param(
            {},
            DuplicateGraphOperationResults(
                status=JiraDuplicateGraphOperationStatus.SUCCESS,
                edge_failures=[],
                edge_successes=[],
            ),
            id="empty_graph",
        ),
    ),
)
def test_disconnect_duplicates_remote_jira_succeeds_once(
    graph: Dict[Tuple[str, str], str],
    expected_results: DuplicateGraphOperationResults,
) -> None:
    # Yield ID if it's in our graph
    def get_issue_link(_graph, vertex1: str, vertex2: str) -> Optional[str]:
        return {"id": graph[(vertex1, vertex2)]} if (vertex1, vertex2) in graph else None

    # Always return True for deletion
    def get_deletion_results(link_ids: List[str]) -> List[Tuple[str, bool]]:
        return [(link_id, link_id == "1") for link_id in link_ids]

    resolver = DuplicateGraphResolver(
        mock_es_dal, mock_jira_dal, mock_jira_manager, mock_parent_summary_generator
    )
    duplicate_graph = JiraDuplicateGraph(
        issue_keys_to_documents={}, existing_issue_links=set(graph)
    )
    with patch.object(resolver, "_get_duplicate_issue_link", get_issue_link):
        with patch.object(resolver, "get_duplicate_graph", return_value=duplicate_graph):
            with patch.object(resolver, "_get_deletion_results", get_deletion_results):
                result = resolver.disconnect_duplicates_remote("foo")
    # Standardize order
    result["edge_failures"].sort()
    result["edge_successes"].sort()
    expected_results["edge_failures"].sort()
    expected_results["edge_successes"].sort()
    assert result == expected_results

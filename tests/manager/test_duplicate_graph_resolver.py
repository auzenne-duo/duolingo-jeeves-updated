import asyncio
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
    user_id="",
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
        user_id=user_id,
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
    assert actual_parent_issue_key == expected_parent.issue_key
    assert set(issue.issue_key for issue in actual_other_parent_issues) == set(
        issue.issue_key for issue in expected_other_parents
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


@patch("jeeves.manager.duplicate_graph_resolver.asyncio", MagicMock())
@patch("jeeves.manager.duplicate_graph_resolver.get_asyncio_loop")
def test_connect_duplicates_remote(mock_get_asyncio_loop):
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

    mock_upload_to_s3 = MagicMock()

    duplicate_graph_resolver = DuplicateGraphResolver(
        mock_es_dal,
        magic_mock_jira_dal,
        mock_jira_manager,
        mock_parent_summary_generator,
        mock_upload_to_s3,
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
    # Verify that update_issue was called, but use more flexible matching
    # since the actual implementation may include additional content like shared conditions links
    assert magic_mock_jira_dal.update_issue.call_count >= 1
    update_call_args = magic_mock_jira_dal.update_issue.call_args_list[0]

    # Check the basic parameters are correct
    assert update_call_args[0][0] == "parent_key"
    assert update_call_args[1]["summary"] == expected_summary
    assert update_call_args[1]["feature"] == "shake"
    assert update_call_args[1]["priority"] == "High"

    # Check that the description has the expected basic structure
    actual_description = update_call_args[1]["description"]
    assert actual_description["type"] == "doc"
    assert actual_description["version"] == 1
    assert len(actual_description["content"]) >= len(expected_description["content"])

    # Check that the expected content is present (allowing for additional content)
    expected_paragraphs = expected_description["content"]
    actual_paragraphs = actual_description["content"]

    for i, expected_paragraph in enumerate(expected_paragraphs):
        if i < len(actual_paragraphs):
            actual_paragraph = actual_paragraphs[i]
            assert actual_paragraph["type"] == expected_paragraph["type"]
            if "content" in expected_paragraph:
                assert actual_paragraph["content"] == expected_paragraph["content"]

    magic_mock_jira_dal.mark_duplicates_async.assert_any_call(expected_links)

    # Test with an existing [Parent] already in the summary
    parent_issue = MagicMock(
        body_text="Random description someone entered\nAPP VERSIONS:\nNOT PRESENT: 2\n6.117.0.1: 1\n\n\nPLATFORMS:\nNOT PRESENT: 2\niOS: 1\n\n\nCOURSES:\nNOT PRESENT: 2\nDUOLINGO_FR_EN: 1\n\n\nINTERFACE LANGUAGES:\nNOT PRESENT: 2\nen: 1\n\n\nOPERATING SYSTEMS:\nNOT PRESENT: 2\niOS 14.4.1: 1\n\n\nAREAS:\n\n",
        summary="[Parent] Parent Issue",
    )
    magic_mock_jira_dal.reset_mock()
    magic_mock_jira_dal.get_issue.return_value = parent_issue

    mock_upload_to_s3.assert_called_once()
    args, _ = mock_upload_to_s3.call_args
    assert args[0].startswith("duplicate_connect_results/parent_key_")
    assert b"SUCCESS" in args[1]
    assert b"S DLAA-4 parent_key" in args[1]
    assert b"S DLAA-5 parent_key" in args[1]
    assert b"S DLAA-6 parent_key" in args[1]

    duplicate_graph_resolver.connect_duplicates_remote(["DLAA-4", "DLAA-5"])
    # Use the same flexible assertion for the second call
    assert magic_mock_jira_dal.update_issue.call_count >= 1
    update_call_args = magic_mock_jira_dal.update_issue.call_args_list[-1]

    # Check the basic parameters are correct
    assert update_call_args[0][0] == "parent_key"
    assert update_call_args[1]["summary"] == expected_summary
    assert update_call_args[1]["feature"] == "shake"
    assert update_call_args[1]["priority"] == "High"

    # Check that the description has the expected basic structure
    actual_description = update_call_args[1]["description"]
    assert actual_description["type"] == "doc"
    assert actual_description["version"] == 1
    assert len(actual_description["content"]) >= len(expected_description["content"])

    # Check that the expected content is present (allowing for additional content)
    expected_paragraphs = expected_description["content"]
    actual_paragraphs = actual_description["content"]

    for i, expected_paragraph in enumerate(expected_paragraphs):
        if i < len(actual_paragraphs):
            actual_paragraph = actual_paragraphs[i]
            assert actual_paragraph["type"] == expected_paragraph["type"]
            if "content" in expected_paragraph:
                assert actual_paragraph["content"] == expected_paragraph["content"]


@patch("jeeves.scripts.index_pipeline_and_spike_detector.sync_jira_tickets.app_registry")
def test_resolve_duplicate_graphs(mock_app_registry):
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
    assert parent_of_dupes.child_issues == [child_2.issue_key, child_3.issue_key]
    assert child_2.parent_issue == parent_of_dupes.issue_key
    assert child_3.parent_issue == parent_of_dupes.issue_key
    # Document DLAA-5 is the parent of DLAA-6 since DLAA-6 is closed as duplicate while DLAA-5 is open
    assert no_parent_5.child_issues == [no_parent_6.issue_key]
    assert no_parent_6.parent_issue == no_parent_5.issue_key

    assert key_to_issue == expected_key_to_issue
    assert list_of_parents == expected_list_of_parents


def test_connect_duplicates_remote_closes_child_tickets():
    """Test that child tickets are closed as duplicates while parent tickets remain open."""
    # Create test documents
    parent_doc = _jira_document(
        issue_number=10, labels=["parent_bug"], status="To Do", resolution=""
    )
    open_child_doc = _jira_document(issue_number=11, status="To Do", resolution="")
    resolved_child_doc = _jira_document(issue_number=12, status="Done", resolution="Fixed")
    another_parent_doc = _jira_document(
        issue_number=13, labels=["parent_bug"], status="To Do", resolution=""
    )

    # Mock duplicate graph
    mock_duplicate_graph = MagicMock()
    mock_duplicate_graph.issue_keys_to_documents = {
        "DLAA-10": parent_doc,
        "DLAA-11": open_child_doc,
        "DLAA-12": resolved_child_doc,
        "DLAA-13": another_parent_doc,
    }
    mock_duplicate_graph.existing_issue_links = set()

    # Mock JiraDAL
    mock_jira_dal = MagicMock()
    mock_jira_dal.get_issue.return_value = parent_doc
    mock_jira_dal.create_bug_issue.return_value = "DLAA-10"

    # Mock async results for marking duplicates
    future = asyncio.Future()
    future.set_result(
        [
            ("DLAA-11", "DLAA-10", True),
            ("DLAA-12", "DLAA-10", True),
            ("DLAA-13", "DLAA-10", True),
        ]
    )
    mock_jira_dal.mark_duplicates_async.return_value = future

    # Mock parent summary manager
    mock_parent_summary_manager = MagicMock()
    mock_parent_summary_manager.generate_summary_and_description.return_value = JiraTicketText(
        description="Test description", title="Test summary"
    )

    # Create resolver
    resolver = DuplicateGraphResolver(
        mock_es_dal, mock_jira_dal, mock_jira_manager, mock_parent_summary_manager, MagicMock()
    )

    # Use patches to simplify the test
    with patch.object(
        resolver, "get_duplicate_graph", return_value=mock_duplicate_graph
    ), patch.object(
        JiraDocument, "is_group_parent", side_effect=lambda doc: "parent_bug" in doc.labels
    ), patch(
        "jeeves.manager.duplicate_graph_resolver.is_jira_issue_resolved",
        side_effect=lambda resolution: resolution not in ["", "Unresolved"],
    ), patch("jeeves.manager.duplicate_graph_resolver.get_asyncio_loop") as mock_loop, patch(
        "jeeves.manager.duplicate_graph_resolver.parse_parent_description",
        return_value={
            "app_version": {},
            "platform": {},
            "course": {},
            "ui_language": {},
            "os_version": {},
            "components": {},
        },
    ):
        mock_loop.return_value.run_until_complete.return_value = [
            ("DLAA-11", "DLAA-10", True),
            ("DLAA-12", "DLAA-10", True),
            ("DLAA-13", "DLAA-10", True),
        ]

        result, parent_key = resolver.connect_duplicates_remote(
            ["DLAA-10", "DLAA-11", "DLAA-12", "DLAA-13"]
        )

        # Verify that child tickets and deprecated parent issues are closed
        # Expected calls: DLAA-13 (deprecated parent), DLAA-11 (open child), DLAA-12 (gets closed despite being resolved)
        assert mock_jira_dal.close_issue_as_duplicate.call_count == 3
        mock_jira_dal.close_issue_as_duplicate.assert_any_call("DLAA-11")  # open child
        mock_jira_dal.close_issue_as_duplicate.assert_any_call(
            "DLAA-12"
        )  # resolved child (still gets closed)
        mock_jira_dal.close_issue_as_duplicate.assert_any_call("DLAA-13")  # deprecated parent
        assert "SUCCESS" in result
        assert parent_key == "DLAA-10"  # Verify the parent key is returned


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


@patch("jeeves.manager.duplicate_graph_resolver.upload_to_jeeves_s3")
def test_connect_duplicates_remote_adds_shared_conditions_link(mock_upload_to_s3):
    """Test that shared experiment conditions link is added to parent issue description."""
    magic_mock_jira_dal = MagicMock()

    # Mock documents with user IDs
    child_doc_1 = MagicMock()
    child_doc_1.issue_key = "DLAA-4"
    child_doc_1.user_id = "450156231"
    child_doc_1.feature = "shake"
    child_doc_1.priority = "High"
    child_doc_1.header_text = "Child Issue 1"

    child_doc_2 = MagicMock()
    child_doc_2.issue_key = "DLAA-5"
    child_doc_2.user_id = "1600500023"
    child_doc_2.feature = "shake"
    child_doc_2.priority = "High"
    child_doc_2.header_text = "Child Issue 2"

    # Mock parent issue
    parent_issue = MagicMock()
    parent_issue.body_text = "Random description someone entered\nAPP VERSIONS:\nNOT PRESENT: 2\n6.117.0.1: 1\n\n\nPLATFORMS:\nNOT PRESENT: 2\niOS: 1\n\n\nCOURSES:\nNOT PRESENT: 2\nDUOLINGO_FR_EN: 1\n\n\nINTERFACE LANGUAGES:\nNOT PRESENT: 2\nen: 1\n\n\nOPERATING SYSTEMS:\nNOT PRESENT: 2\niOS 14.4.1: 1\n\n\nAREAS:\n\n"
    parent_issue.issue_key = "parent_key"
    parent_issue.summary = "Parent Issue"

    docs = {
        "DLAA-4": child_doc_1,
        "DLAA-5": child_doc_2,
        "parent_key": parent_issue,
    }

    def mock_is_group_parent(doc):
        return doc.issue_key == "parent_key"

    magic_mock_jira_dal.get_issue.return_value = parent_issue
    magic_mock_jira_dal.mark_duplicates_async.return_value = asyncio.Future()
    magic_mock_jira_dal.mark_duplicates_async.return_value.set_result(
        [
            ("DLAA-4", "parent_key", True),
            ("DLAA-5", "parent_key", True),
        ]
    )

    mock_parent_summary_generator = MagicMock()
    mock_summary = MagicMock()
    mock_summary.title = "Test Summary"
    mock_summary.description = "Test Description"
    mock_parent_summary_generator.generate_summary_and_description.return_value = mock_summary

    duplicate_graph_resolver = DuplicateGraphResolver(
        mock_es_dal, magic_mock_jira_dal, mock_jira_manager, mock_parent_summary_generator
    )

    with patch.object(duplicate_graph_resolver, "get_duplicate_graph") as mock_get_duplicate_graph:
        mock_get_duplicate_graph.return_value = JiraDuplicateGraph(
            issue_keys_to_documents=docs,
            existing_issue_links=set(),
        )
        with patch.object(JiraDocument, "is_group_parent", side_effect=mock_is_group_parent):
            duplicate_graph_resolver.connect_duplicates_remote(["DLAA-4", "DLAA-5"])

    # Verify that update_issue was called with the shared conditions link
    magic_mock_jira_dal.update_issue.assert_called_once()
    call_args = magic_mock_jira_dal.update_issue.call_args

    # Check that the description contains the shared conditions URL
    description_arg = call_args[1]["description"]
    description_content = description_arg["content"]

    # Find the paragraph with the shared conditions link
    shared_conditions_found = False
    for paragraph in description_content:
        if paragraph["type"] == "paragraph":
            # Check if this paragraph contains the shared conditions link
            content = paragraph.get("content", [])
            has_shared_conditions_text = False
            has_link = False

            for text_element in content:
                if text_element.get("type") == "text":
                    # Check for bold "Shared Experiment Conditions:" text
                    if "Shared Experiment Conditions:" in text_element.get("text", "") and any(
                        mark.get("type") == "strong" for mark in text_element.get("marks", [])
                    ):
                        has_shared_conditions_text = True

                    # Check for the link with correct URL containing user IDs
                    if "View Shared Conditions" in text_element.get("text", "") and any(
                        mark.get("type") == "link"
                        and "1600500023,450156231" in mark.get("attrs", {}).get("href", "")
                        for mark in text_element.get("marks", [])
                    ):
                        has_link = True

            if has_shared_conditions_text and has_link:
                shared_conditions_found = True
                break

    assert (
        shared_conditions_found
    ), "Shared experiment conditions link not found in parent issue description"


def _make_no_parent_resolver(mock_jira_dal: MagicMock) -> DuplicateGraphResolver:
    """Helper that returns a resolver wired with MagicMocks for the no-parent tests."""
    return DuplicateGraphResolver(
        MagicMock(),  # es_dal
        mock_jira_dal,
        MagicMock(),  # jira_manager
        MagicMock(),  # parent_summary_manager
        MagicMock(),  # upload_to_s3
    )


@pytest.mark.parametrize(
    "side_effects, expected_status",
    [
        ([True, True], "SUCCESS"),
        ([True, False], "PARTIAL"),
        ([False, False], "FAILURE"),
    ],
)
def test_connect_duplicates_no_parent_various_outcomes(side_effects, expected_status):
    """Verifies SUCCESS / PARTIAL / FAILURE determination and ticket-closing behavior."""
    mock_jira_dal = MagicMock()
    resolver = _make_no_parent_resolver(mock_jira_dal)

    issue_keys = ["DLAA-1", "DLAA-2", "DLAA-3"]  # one duplicate + two targets
    with patch.object(resolver, "try_mark_duplicate_remote", side_effect=side_effects) as mock_try:
        result_manifest = resolver.connect_duplicates_no_parent(issue_keys)

    # 1. Overall status line should match expectation
    assert result_manifest.split("\n", 1)[0] == expected_status

    # 2. try_mark_duplicate_remote should be invoked for each target ticket
    assert mock_try.call_count == len(issue_keys) - 1
    mock_try.assert_any_call("DLAA-1", "DLAA-2")
    mock_try.assert_any_call("DLAA-1", "DLAA-3")

    # 3. The duplicate ticket must be closed exactly once regardless of outcome
    mock_jira_dal.close_issue_as_duplicate.assert_called_once_with("DLAA-1")

    # 4. Manifest lines must reflect individual successes / failures
    for idx, success in enumerate(side_effects, start=2):
        key = issue_keys[idx - 1]
        prefix = "S" if success else "F"
        assert f"{prefix} DLAA-1 {key}" in result_manifest


def test_connect_duplicates_no_parent_bad_input():
    """Calling with fewer than two issue keys should raise a ValueError."""
    resolver = _make_no_parent_resolver(MagicMock())
    with pytest.raises(ValueError):
        resolver.connect_duplicates_no_parent(["DLAA-1"])  # only one key provided

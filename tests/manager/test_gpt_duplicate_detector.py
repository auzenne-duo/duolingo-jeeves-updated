from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from jeeves.dal.ai_completions_dal import AICompletionsDAL
from jeeves.manager.gpt_duplicate_detector import GPTDuplicateDetector
from jeeves.manager.jira_manager import JiraManager


@pytest.fixture
def mock_ai_completions_dal():
    return MagicMock(spec=AICompletionsDAL)


@pytest.fixture
def mock_jira_manager():
    return MagicMock(spec=JiraManager)


@pytest.fixture
def mock_s3_client():
    return MagicMock()


@pytest.fixture
def mock_s3_bucket():
    return "test-bucket"


@pytest.fixture
def mock_gpt_screenshot_summarizer():
    summarizer = MagicMock()
    summarizer.get_description_s3.return_value = "Test screenshot"
    return summarizer


@pytest.fixture
def detector(
    mock_ai_completions_dal,
    mock_jira_manager,
    mock_gpt_screenshot_summarizer,
    mock_s3_client,
    mock_s3_bucket,
):
    return GPTDuplicateDetector(
        ai_completions_dal=mock_ai_completions_dal,
        jira_manager=mock_jira_manager,
        gpt_screenshot_summarizer=mock_gpt_screenshot_summarizer,
        s3_client=mock_s3_client,
        s3_bucket=mock_s3_bucket,
    )


def test_get_jira_issue_text(detector):
    test_issue = {
        "key": "TEST-123",
        "fields": {
            "summary": "Test Issue",
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {"type": "paragraph", "content": [{"type": "text", "text": "Test Description"}]}
                ],
            },
        },
    }

    text = detector.get_jira_issue_text(test_issue)

    assert "TEST-123" in text
    assert "Test Issue" in text
    assert "Test Description" in text
    assert "Test screenshot" in text


def test_get_jira_issue_text_with_empty_description(detector):
    test_issue = {"key": "TEST-123", "fields": {"summary": "Test Issue", "description": None}}

    text = detector.get_jira_issue_text(test_issue)

    assert "TEST-123" in text
    assert "Test Issue" in text
    assert "(no description)" in text
    assert "Test screenshot" in text


def test_determine_duplicate_from_chat_response():
    assert GPTDuplicateDetector.determine_duplicate_from_chat_response(
        "These are duplicates.\nduplicate: true"
    ) == (True, "These are duplicates.")

    assert GPTDuplicateDetector.determine_duplicate_from_chat_response(
        "These are not duplicates.\nduplicate: false"
    ) == (False, "These are not duplicates.")


def test_find_duplicates(detector, mock_jira_manager, mock_ai_completions_dal):
    test_issue = {
        "key": "TEST-123",
        "fields": {
            "summary": "Test Issue",
            "description": {
                "type": "doc",
                "version": 1,
                "content": [
                    {"type": "paragraph", "content": [{"type": "text", "text": "Test Description"}]}
                ],
            },
        },
    }

    other_issues = [
        {
            "key": "TEST-456",
            "fields": {
                "summary": "Other Issue 1",
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "Other Description 1"}],
                        }
                    ],
                },
            },
        },
        {
            "key": "TEST-789",
            "fields": {
                "summary": "Other Issue 2",
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [{"type": "text", "text": "Other Description 2"}],
                        }
                    ],
                },
            },
        },
    ]

    mock_jira_manager.get_str_tickets_since.return_value = other_issues

    mock_ai_completions_dal.batched_ask.return_value = [
        "These are duplicates.\nduplicate: true",
        "These are not duplicates.\nduplicate: false",
    ]

    duplicates = detector.find_duplicates(test_issue)

    assert len(duplicates) == 1
    assert duplicates[0][0] == "TEST-456"
    assert "These are duplicates." in duplicates[0][1]

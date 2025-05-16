import json
from io import BytesIO
from unittest.mock import MagicMock

import pytest
from werkzeug.datastructures import FileStorage

from jeeves.dal.ai_completions_dal import AICompletionsDAL
from jeeves.manager.gpt_log_summarizer import (
    GPTLogSummarizer,
    JiraLogSummarizationTicket,
    LogSummaryResponse,
)


def make_filestorage(filename, content):
    return FileStorage(stream=BytesIO(content.encode("utf-8")), filename=filename)


IGNORED_LINE = "should be ignored"
ERROR_LINE = "error1"
ERROR_LINE_2 = "error2"
DEBUG_LINE = "debug1"
DEBUG_LINE_2 = "debug2"


@pytest.fixture
def files():
    return {
        "error.log": [ERROR_LINE, ERROR_LINE_2],
        "info.txt": [IGNORED_LINE],
        "debug.LOG": [DEBUG_LINE, DEBUG_LINE_2],
    }


@pytest.fixture
def ticket(files):
    return JiraLogSummarizationTicket(
        description="desc", title="title", files=files, ticket_id="JIRA-1"
    )


@pytest.fixture
def mock_ai_completions_dal():
    return MagicMock(spec=AICompletionsDAL)


@pytest.fixture
def summarizer(mock_ai_completions_dal):
    return GPTLogSummarizer(ai_completions_dal=mock_ai_completions_dal)


def test_logs_filtering(ticket):
    assert len(ticket.logs) == 4
    assert any(ERROR_LINE in log for log in ticket.logs)
    assert any(DEBUG_LINE in log for log in ticket.logs)
    assert not any(IGNORED_LINE in log for log in ticket.logs)


def test_to_yaml(ticket):
    yaml_str = ticket.to_yaml()
    lines = yaml_str.split("\n")
    assert lines[0] == "TITLE: title"
    assert lines[1] == "DESCRIPTION: desc"
    assert lines[2].startswith("LOGS: ")
    logs_json = lines[2][len("LOGS: ") :]
    logs = json.loads(logs_json)
    assert any(ERROR_LINE in log for log in logs)
    assert any(DEBUG_LINE in log for log in logs)
    assert not any(IGNORED_LINE in log for log in logs)
    assert isinstance(logs, list)
    assert len(logs) == 4


def test_summarize_logs_success(summarizer, mock_ai_completions_dal, ticket):
    response_json = '{"log_summary": ["log1", "log2"]}'
    mock_ai_completions_dal.ask.return_value = response_json
    response = summarizer.summarize_logs(ticket)
    assert isinstance(response, LogSummaryResponse)
    assert response.log_summary == ["log1", "log2"]


def test_summarize_logs_error(summarizer, mock_ai_completions_dal, ticket):
    mock_ai_completions_dal.ask.side_effect = Exception("fail")
    response = summarizer.summarize_logs(ticket)
    assert isinstance(response, LogSummaryResponse)
    assert response.log_summary == []


def test_filter_logs_error_warn(summarizer, mock_ai_completions_dal):
    logs = [
        "error: something failed",
        "info: all good",
        "Warn: be careful",
        "DEBUG: not important",
        "warning: heads up",
        "no issues here",
        "error: frameperformance issue detected",
        "warn: keychain access denied",
        "error: unrelated error",
    ]
    ticket = JiraLogSummarizationTicket(
        description="desc", title="title", files={"error.log": logs}, ticket_id="JIRA-1"
    )
    mock_ai_completions_dal.ask.return_value = '{"log_summary": []}'
    summarizer.summarize_logs(ticket)
    args, kwargs = mock_ai_completions_dal.ask.call_args
    user_prompt = kwargs.get("user_prompt") or args[1]
    assert "error: something failed" in user_prompt
    assert "Warn: be careful" in user_prompt
    assert "warning: heads up" in user_prompt
    assert "error: unrelated error" in user_prompt
    assert "info: all good" not in user_prompt
    assert "DEBUG: not important" not in user_prompt
    assert "no issues here" not in user_prompt
    assert "error: frameperformance issue detected" not in user_prompt
    assert "warn: keychain access denied" not in user_prompt


def test_empty_title_and_description_returns_empty_and_no_call(summarizer, mock_ai_completions_dal):
    ticket = JiraLogSummarizationTicket(description="", title="", files={}, ticket_id="JIRA-1")
    ticket.logs = ["error: something failed", "warn: something odd"]
    result = summarizer.summarize_logs(ticket)
    assert result.log_summary == []
    mock_ai_completions_dal.ask.assert_not_called()


def test_empty_after_filtering_returns_empty_and_no_call(summarizer, mock_ai_completions_dal):
    ticket = JiraLogSummarizationTicket(
        description="desc", title="title", files={}, ticket_id="JIRA-1"
    )
    ticket.logs = ["info: all good", "DEBUG: not important", "no issues here"]
    result = summarizer.summarize_logs(ticket)
    assert result.log_summary == []
    mock_ai_completions_dal.ask.assert_not_called()


@pytest.mark.parametrize(
    "title",
    [
        "test",
        "tests",
        "Test",
        " test ",
        "TEST",
        "TeSt",
        "testing",
        "Testing",
        " TESTING ",
        "TeStInG",
    ],
)
def test_testing_ticket_returns_empty_and_no_call(summarizer, mock_ai_completions_dal, title):
    ticket = JiraLogSummarizationTicket(description="", title=title, files={}, ticket_id="JIRA-1")
    ticket.logs = ["error: something failed", "warn: something odd"]
    result = summarizer.summarize_logs(ticket)
    assert result.log_summary == []
    mock_ai_completions_dal.ask.assert_not_called()


class TestLogSummaryResponseFormat:
    def test_format_collapses_duplicates_and_counts(self):
        logs = [
            "error: something failed",
            "warn: something odd",
            "error: something failed",
            "info: all good",
            "warn: something odd",
            "warn: something odd",
        ]
        response = LogSummaryResponse(log_summary=logs)
        formatted = response.format(max_lines=10)
        assert "error: something failed (x2)" in formatted
        assert "warn: something odd (x3)" in formatted
        assert "info: all good" in formatted
        assert "info: all good (x" not in formatted
        assert "error: something failed\nerror: something failed" not in formatted

    def test_format_max_lines(self):
        logs = [f"error {i}" for i in range(10)]
        response = LogSummaryResponse(log_summary=logs)
        formatted = response.format(max_lines=5)
        assert len(formatted.splitlines()) == 6  # 5 lines + 1 omitted line
        assert "...and 5 more unique lines omitted." in formatted

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
    assert len(ticket.logs) == 2
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
    assert len(logs) == 2


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

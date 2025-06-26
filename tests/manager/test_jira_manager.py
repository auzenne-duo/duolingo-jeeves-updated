from datetime import datetime
from unittest.mock import MagicMock

import pytest
import pytz

from jeeves.manager.jira_manager import JiraManager


@pytest.fixture
def base_time():
    return datetime(2024, 1, 1, tzinfo=pytz.utc)


@pytest.fixture
def test_issues():
    return [
        {"key": "TEST-1", "fields": {"updated": "2024-01-01T10:00:00.000+0000"}},
        {"key": "TEST-2", "fields": {"updated": "2024-01-01T11:00:00.000+0000"}},
        {"key": "TEST-3", "fields": {"updated": "2024-01-01T12:00:00.000+0000"}},
    ]


@pytest.fixture
def mock_jira_dal(monkeypatch):
    """Mock the JiraDAL.paginate_search_issues method"""
    mock = MagicMock()
    monkeypatch.setattr("jeeves.manager.jira_manager.JiraDAL.paginate_search_issues", mock)
    return mock


def test_get_str_tickets_since_returns_issues(mock_jira_dal, base_time, test_issues):
    """Test that get_str_tickets_since returns the issues from the DAL"""
    mock_jira_dal.return_value = test_issues[:2]

    results = JiraManager.get_str_tickets_since(base_time)

    assert len(results) == 2
    assert results[0]["key"] == "TEST-1"
    assert results[1]["key"] == "TEST-2"
    assert mock_jira_dal.call_count == 1


def test_get_str_tickets_since_empty_results(mock_jira_dal, base_time):
    """Test that get_str_tickets_since handles empty results"""
    mock_jira_dal.return_value = []

    results = JiraManager.get_str_tickets_since(base_time)

    assert len(results) == 0
    assert mock_jira_dal.call_count == 1

from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytest
import pytz

from jeeves.manager.jira_manager import JiraManager
from jeeves.util.date_util import parse_external_datetime


@pytest.fixture
def base_time():
    return datetime(2024, 1, 1, tzinfo=pytz.utc)


@pytest.fixture
def test_issues():
    return {
        "issue1": {"key": "TEST-1", "fields": {"updated": "2024-01-01T10:00:00.000+0000"}},
        "issue2": {"key": "TEST-2", "fields": {"updated": "2024-01-01T11:00:00.000+0000"}},
        "issue3": {"key": "TEST-3", "fields": {"updated": "2024-01-01T12:00:00.000+0000"}},
    }


@pytest.fixture(autouse=True)
def reset_cache():
    """Reset the cache before and after each test"""
    # Reset before test
    JiraManager.RECENT_ISSUES_CACHE = {}
    JiraManager.RECENT_ISSUES_CACHE_START = datetime.fromtimestamp(0, tz=pytz.utc)
    JiraManager.RECENT_ISSUES_CACHE_END = datetime.fromtimestamp(0, tz=pytz.utc)

    yield

    # Reset after test
    JiraManager.RECENT_ISSUES_CACHE = {}
    JiraManager.RECENT_ISSUES_CACHE_START = datetime.fromtimestamp(0, tz=pytz.utc)
    JiraManager.RECENT_ISSUES_CACHE_END = datetime.fromtimestamp(0, tz=pytz.utc)


@pytest.fixture
def mock_jira_dal(monkeypatch):
    """Mock the JiraDAL.paginate_search_issues method"""
    mock = MagicMock()
    monkeypatch.setattr("jeeves.manager.jira_manager.JiraDAL.paginate_search_issues", mock)
    return mock


def test_initial_cache_population(mock_jira_dal, base_time, test_issues):
    # Setup mock to return test issues
    mock_jira_dal.return_value = [test_issues["issue1"], test_issues["issue2"]]

    # Call the method
    results = JiraManager.get_str_tickets_since(base_time)

    # Verify results
    assert len(results) == 2
    assert results[0]["key"] == "TEST-1"
    assert results[1]["key"] == "TEST-2"

    # Verify cache state
    assert len(JiraManager.RECENT_ISSUES_CACHE) == 2
    assert base_time == JiraManager.RECENT_ISSUES_CACHE_START
    assert base_time < JiraManager.RECENT_ISSUES_CACHE_END


def test_cache_updates_with_new_tickets(mock_jira_dal, base_time, test_issues):
    # First call populates cache
    mock_jira_dal.return_value = [test_issues["issue1"]]
    JiraManager.get_str_tickets_since(base_time)

    # Second call with new ticket
    mock_jira_dal.return_value = [test_issues["issue2"]]
    results = JiraManager.get_str_tickets_since(base_time)

    # Should return both tickets
    assert len(results) == 2
    assert results[0]["key"] == "TEST-1"
    assert results[1]["key"] == "TEST-2"


def test_cache_purges_old_tickets(mock_jira_dal, base_time, test_issues):
    # First populate cache with old and new tickets
    mock_jira_dal.return_value = [test_issues["issue1"], test_issues["issue2"]]
    JiraManager.get_str_tickets_since(base_time)

    # Call with later start time that should exclude issue1
    later_time = parse_external_datetime(test_issues["issue2"]["fields"]["updated"])
    mock_jira_dal.return_value = []
    results = JiraManager.get_str_tickets_since(later_time)

    # Should only return newer ticket
    assert len(results) == 1
    assert results[0]["key"] == "TEST-2"
    assert len(JiraManager.RECENT_ISSUES_CACHE) == 1


def test_handles_tickets_before_cache_start(mock_jira_dal, base_time, test_issues):
    # First populate cache with newer tickets
    mock_jira_dal.return_value = [test_issues["issue2"], test_issues["issue3"]]
    JiraManager.get_str_tickets_since(
        parse_external_datetime(test_issues["issue2"]["fields"]["updated"])
    )

    # Call with earlier start time that should include older tickets
    mock_jira_dal.return_value = [test_issues["issue1"]]
    results = JiraManager.get_str_tickets_since(base_time)

    # Should return all tickets
    assert len(results) == 3
    assert results[0]["key"] == "TEST-1"
    assert results[1]["key"] == "TEST-2"
    assert results[2]["key"] == "TEST-3"


def test_cache_start_end_time_updates(mock_jira_dal, base_time, test_issues):
    # Initial call
    mock_jira_dal.return_value = [test_issues["issue1"]]
    JiraManager.get_str_tickets_since(base_time)

    initial_cache_start = JiraManager.RECENT_ISSUES_CACHE_START
    initial_cache_end = JiraManager.RECENT_ISSUES_CACHE_END

    # Simulate time passing by manually setting cache end time
    new_cache_end = initial_cache_end + timedelta(minutes=1)
    JiraManager.RECENT_ISSUES_CACHE_END = new_cache_end

    # Second call
    mock_jira_dal.return_value = [test_issues["issue2"]]
    JiraManager.get_str_tickets_since(base_time)

    # Cache start should remain the same
    assert initial_cache_start == JiraManager.RECENT_ISSUES_CACHE_START
    # Cache end should be updated
    assert initial_cache_end < JiraManager.RECENT_ISSUES_CACHE_END


def test_single_api_call_with_ascending_times(mock_jira_dal, base_time, test_issues):
    """Test that only one API call is made when updated_since times are ascending"""
    # Setup mock to return test issues
    mock_jira_dal.return_value = [
        test_issues["issue1"],
        test_issues["issue2"],
        test_issues["issue3"],
    ]

    # First call with earliest time
    results1 = JiraManager.get_str_tickets_since(base_time)
    assert len(results1) == 3
    assert mock_jira_dal.call_count == 1

    # Second call with later time (should use cache)
    later_time = parse_external_datetime(test_issues["issue2"]["fields"]["updated"])
    results2 = JiraManager.get_str_tickets_since(later_time)
    assert len(results2) == 2  # Should only return issue2 and issue3
    assert mock_jira_dal.call_count == 2

    # Third call with even later time (should use cache)
    latest_time = parse_external_datetime(test_issues["issue3"]["fields"]["updated"])
    results3 = JiraManager.get_str_tickets_since(latest_time)
    assert len(results3) == 1  # Should only return issue3
    assert mock_jira_dal.call_count == 3


def test_double_api_call_with_earlier_time(mock_jira_dal, base_time, test_issues):
    """Test that two API calls are made when an earlier time is provided after a later time"""
    # First call with later time
    later_time = parse_external_datetime(test_issues["issue2"]["fields"]["updated"])
    mock_jira_dal.return_value = [test_issues["issue2"], test_issues["issue3"]]
    results1 = JiraManager.get_str_tickets_since(later_time)
    assert len(results1) == 2
    assert mock_jira_dal.call_count == 1

    # Second call with earlier time (should make new API call)
    mock_jira_dal.return_value = [test_issues["issue1"]]
    results2 = JiraManager.get_str_tickets_since(base_time)
    assert len(results2) == 3  # Should return all tickets
    assert mock_jira_dal.call_count == 3  # Make 2 API calls to fill tickets before and after cache

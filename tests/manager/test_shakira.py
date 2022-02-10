import unittest
from unittest.mock import MagicMock

from jeeves.manager.shakira import ShakiraManager
from jeeves.manager.shakira_jira import ShakiraJiraClient
from jeeves.manager.shakira_slack import ShakiraSlackClient
from jeeves.model.slack_channel import SlackChannel

_JIRA_ISSUE_URL = "https://jira.com/issues/DLAA-1"


def _get_mocked_managers():
    shakira_jira_mock = ShakiraJiraClient
    shakira_jira_mock.create_issue = MagicMock(return_value="DLAA-1")
    shakira_jira_mock.upload_attachments = MagicMock()
    shakira_jira_mock.issue_url = MagicMock(return_value=_JIRA_ISSUE_URL)

    shakira_slack_mock = ShakiraSlackClient
    shakira_slack_mock.post_issue = MagicMock(return_value="post1")
    shakira_slack_mock.post_info_in_reply = MagicMock()

    return (
        shakira_jira_mock,
        shakira_slack_mock,
        ShakiraManager(shakira_jira_mock, shakira_slack_mock),
    )


def test_get_slack_report_types():
    _, _, shakira_manager = _get_mocked_managers()
    result = shakira_manager.get_slack_report_types()

    case = unittest.TestCase()
    case.assertCountEqual(
        [
            {"name": "Visual polish", "alsoPostsToJira": True},
            {"name": "Lesson content issue", "alsoPostsToJira": False},
            {"name": "TTS is missing/mispronounced", "alsoPostsToJira": False},
            {"name": "Feature request", "alsoPostsToJira": False},
        ],
        result,
    )


def test_report_issue_to_jira_only():
    shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
    shakira_manager.report_issue(
        project="DLAA",
        feature="Callouts",
        slack_report_type=None,
        client_specified_slack_channel_name=None,
        summary="summary",
        description=None,
        generated_description=None,
        reporter_email=None,
        pre_release=False,
        files={},
    )

    shakira_jira_mock.create_issue.assert_called_once_with(
        project="DLAA",
        feature="Callouts",
        label=None,
        summary="summary",
        description=None,
        generated_description=None,
        reporter_email=None,
        pre_release=False,
        will_post_to_slack=False,
    )
    assert not shakira_slack_mock.post_issue.called


def test_report_issue_to_slack_only_v1():
    shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
    shakira_manager.report_issue(
        project="DLAA",
        feature="TTS: mispronunciation",
        slack_report_type=None,
        client_specified_slack_channel_name=None,
        summary="summary",
        description=None,
        generated_description=None,
        reporter_email=None,
        pre_release=False,
        files={},
    )

    shakira_slack_mock.post_issue.assert_called_once_with(
        project="DLAA",
        slack_channel=SlackChannel.FEEDBACK_TTS,
        summary="summary",
        reporter_email=None,
        jira_issue_url=None,
        post_info_in_reply=False,
        screenshot=None,
    )
    assert not shakira_jira_mock.create_issue.called


def test_report_issue_to_slack_only_v2():
    shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
    shakira_manager.report_issue(
        project="DLAA",
        feature=None,
        slack_report_type="TTS is missing/mispronounced",
        client_specified_slack_channel_name=None,
        summary="summary",
        description=None,
        generated_description=None,
        reporter_email=None,
        pre_release=False,
        files={},
    )

    shakira_slack_mock.post_issue.assert_called_once_with(
        project="DLAA",
        slack_channel=SlackChannel.FEEDBACK_TTS,
        summary="summary",
        reporter_email=None,
        jira_issue_url=None,
        post_info_in_reply=False,
        screenshot=None,
    )
    assert not shakira_jira_mock.create_issue.called


def test_report_issue_to_both_v1():
    shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
    shakira_manager.report_issue(
        project="DLAA",
        feature="Visual polish",
        slack_report_type=None,
        client_specified_slack_channel_name=None,
        summary="summary",
        description=None,
        generated_description=None,
        reporter_email=None,
        pre_release=False,
        files={},
    )

    shakira_jira_mock.create_issue.assert_called_once_with(
        project="DLAA",
        feature="Visual polish",
        label="visual-polish",
        summary="summary",
        description=None,
        generated_description=None,
        reporter_email=None,
        pre_release=False,
        will_post_to_slack=True,
    )
    shakira_slack_mock.post_issue.assert_called_once_with(
        project="DLAA",
        slack_channel=SlackChannel.VISUAL_POLISH,
        summary="summary",
        reporter_email=None,
        jira_issue_url=_JIRA_ISSUE_URL,
        post_info_in_reply=False,
        screenshot=None,
    )


def test_report_issue_to_both_v2():
    shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
    shakira_manager.report_issue(
        project="DLAA",
        feature="Callouts",
        slack_report_type="Visual polish",
        client_specified_slack_channel_name=None,
        summary="summary",
        description=None,
        generated_description=None,
        reporter_email=None,
        pre_release=False,
        files={},
    )

    shakira_jira_mock.create_issue.assert_called_once_with(
        project="DLAA",
        feature="Callouts",
        label="visual-polish",
        summary="summary",
        description=None,
        generated_description=None,
        reporter_email=None,
        pre_release=False,
        will_post_to_slack=True,
    )
    shakira_slack_mock.post_issue.assert_called_once_with(
        project="DLAA",
        slack_channel=SlackChannel.VISUAL_POLISH,
        summary="summary",
        reporter_email=None,
        jira_issue_url=_JIRA_ISSUE_URL,
        post_info_in_reply=False,
        screenshot=None,
    )

import unittest
from unittest.mock import MagicMock, patch

from jeeves.manager.shakira import ShakiraManager
from jeeves.manager.shakira_jira import ShakiraJiraApiClient
from jeeves.manager.shakira_slack import ShakiraSlackApiClient
from jeeves.model.slack_channel import SlackChannel

_JIRA_ISSUE_URL = "https://jira.com/issues/DLAA-1"


def _get_mocked_managers():
    shakira_jira_mock = ShakiraJiraApiClient()
    shakira_jira_mock.create_issue = MagicMock(return_value="DLAA-1")
    shakira_jira_mock.get_issue_details = MagicMock(return_value="None")
    shakira_jira_mock.link_issues = MagicMock()
    shakira_jira_mock.upload_attachments = MagicMock()
    shakira_jira_mock.issue_url = MagicMock(return_value=_JIRA_ISSUE_URL)

    shakira_slack_mock = ShakiraSlackApiClient()
    shakira_slack_mock.post_issue = MagicMock(return_value="post1")
    shakira_slack_mock.post_info_in_reply = MagicMock()

    return (
        shakira_jira_mock,
        shakira_slack_mock,
        ShakiraManager(shakira_jira_mock, shakira_slack_mock),
    )


mock_priority_estimator = MagicMock()
mock_priority_estimator.estimate_priority.return_value = "Medium"


@patch("jeeves.manager.shakira.PriorityEstimator", mock_priority_estimator)
class Test(unittest.TestCase):
    def test_get_slack_report_types(self):
        _, _, shakira_manager = _get_mocked_managers()
        result = shakira_manager.get_slack_report_types()

        case = unittest.TestCase()
        case.assertCountEqual(
            [
                {"name": "Visual polish", "alsoPostsToJira": True},
                {"name": "Lesson content issue", "alsoPostsToJira": False},
                {"name": "TTS is missing/mispronounced", "alsoPostsToJira": False},
                {"name": "Localization issue", "alsoPostsToJira": False},
                {"name": "Feature request", "alsoPostsToJira": False},
            ],
            result,
        )

    def test_report_issue_to_jira_only(self):
        shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
        shakira_manager.report_issue(
            project="DLAA",
            feature="Callouts",
            slack_report_type=None,
            client_specified_slack_channel_name=None,
            related_issue_key=None,
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
            labels=[],
            summary="summary",
            description=None,
            generated_description=None,
            reporter_email=None,
            pre_release=False,
            will_post_to_slack=False,
            priority="Medium",
            related_issue_exists=False,
        )
        assert not shakira_slack_mock.post_issue.called

    def test_report_issue_with_valid_related_jira_ticket(self):
        shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
        shakira_jira_mock.get_issue_details = MagicMock(return_value={"id": 1})

        shakira_manager.report_issue(
            project="DLAA",
            feature="Callouts",
            slack_report_type="Visual polish",
            client_specified_slack_channel_name=None,
            related_issue_key="DEL-1733",
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
            labels=["visual-polish"],
            summary="summary",
            description=None,
            generated_description=None,
            reporter_email=None,
            pre_release=False,
            will_post_to_slack=True,
            priority="Medium",
            related_issue_exists=True,
        )

        shakira_jira_mock.get_issue_details.assert_called_once_with(
            project="DLAA", issue_key="DEL-1733"
        )

        shakira_jira_mock.link_issues.assert_called_once_with(
            project="DLAA", outward_issue_key="DEL-1733", inward_issue_key="DLAA-1"
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

    def test_report_issue_with_invalid_related_jira_ticket(self):
        shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
        shakira_jira_mock.get_issue_details = MagicMock(return_value={})

        shakira_manager.report_issue(
            project="DLAA",
            feature="Callouts",
            slack_report_type="Visual polish",
            client_specified_slack_channel_name=None,
            related_issue_key="DEL-1733",
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
            labels=["visual-polish"],
            summary="summary",
            description=None,
            generated_description=None,
            reporter_email=None,
            pre_release=False,
            will_post_to_slack=False,
            priority="Medium",
            related_issue_exists=False,
        )

        shakira_jira_mock.get_issue_details.assert_called_once_with(
            project="DLAA", issue_key="DEL-1733"
        )
        assert not shakira_jira_mock.link_issues.called
        assert not shakira_slack_mock.post_issue.called

    def test_report_issue_to_slack_only_v1(self):
        shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
        shakira_manager.report_issue(
            project="DLAA",
            feature="TTS: mispronunciation",
            slack_report_type=None,
            client_specified_slack_channel_name=None,
            related_issue_key=None,
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

    def test_report_issue_to_slack_only_with_related_ticket_v1(self):
        shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
        shakira_manager.report_issue(
            project="DLAA",
            feature="TTS: mispronunciation",
            slack_report_type=None,
            client_specified_slack_channel_name=None,
            related_issue_key="DLAA-1733",
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

    def test_report_issue_to_slack_only_v2(self):
        shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
        shakira_manager.report_issue(
            project="DLAA",
            feature=None,
            slack_report_type="TTS is missing/mispronounced",
            client_specified_slack_channel_name=None,
            related_issue_key=None,
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

    def test_report_issue_to_both_v1(self):
        shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
        shakira_manager.report_issue(
            project="DLAA",
            feature="Visual polish",
            slack_report_type=None,
            client_specified_slack_channel_name=None,
            related_issue_key=None,
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
            labels=["visual-polish"],
            summary="summary",
            description=None,
            generated_description=None,
            reporter_email=None,
            pre_release=False,
            will_post_to_slack=True,
            priority="Medium",
            related_issue_exists=False,
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

    def test_report_issue_to_both_v2(self):
        shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
        shakira_manager.report_issue(
            project="DLAA",
            feature="Callouts",
            slack_report_type="Visual polish",
            client_specified_slack_channel_name=None,
            related_issue_key=None,
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
            labels=["visual-polish"],
            summary="summary",
            description=None,
            generated_description=None,
            reporter_email=None,
            pre_release=False,
            will_post_to_slack=True,
            priority="Medium",
            related_issue_exists=False,
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

        assert not shakira_jira_mock.link_issues.called

    def test_report_issue_from_jeeves(self):
        shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
        shakira_manager.report_issue(
            project="DLAA",
            feature="Callouts",
            slack_report_type=None,
            client_specified_slack_channel_name=None,
            related_issue_key=None,
            summary="[via Jeeves] summary",
            description=None,
            generated_description=None,
            reporter_email=None,
            pre_release=False,
            files={},
        )

        shakira_jira_mock.create_issue.assert_called_once_with(
            project="DLAA",
            feature="Callouts",
            labels=["via-jeeves"],
            summary="[via Jeeves] summary",
            description=None,
            generated_description=None,
            reporter_email=None,
            pre_release=False,
            will_post_to_slack=False,
            priority="Medium",
            related_issue_exists=False,
        )
        assert not shakira_slack_mock.post_issue.called

    def test_report_issue_called_estimate_priority(self):
        shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
        shakira_manager.report_issue(
            project="DLAA",
            feature="Callouts",
            slack_report_type=None,
            client_specified_slack_channel_name=None,
            related_issue_key=None,
            summary="summary",
            description=None,
            generated_description=None,
            reporter_email="biglou@duolingo.com",
            pre_release=False,
            files={},
        )

        shakira_jira_mock.create_issue.assert_called_once_with(
            project="DLAA",
            feature="Callouts",
            labels=[],
            summary="summary",
            description=None,
            generated_description=None,
            reporter_email="biglou@duolingo.com",
            pre_release=False,
            will_post_to_slack=False,
            priority="Medium",
            related_issue_exists=False,
        )
        assert not shakira_slack_mock.post_issue.called
        mock_priority_estimator.estimate_priority.assert_called_with(
            "summary", "Callouts", "biglou@duolingo.com"
        )

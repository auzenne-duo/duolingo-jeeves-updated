import unittest
from unittest.mock import MagicMock, patch

import requests

from jeeves.dal.employees import EmployeesDAL
from jeeves.manager.shakira import ShakiraManager
from jeeves.manager.shakira_jira import ShakiraJiraApiClient
from jeeves.manager.shakira_slack import ShakiraSlackApiClient
from jeeves.model.slack_channel import SlackChannel
from jeeves.util.shakira import JIRA_RELEASE_BLOCKER_LABEL

_JIRA_ISSUE_URL = "https://jira.com/issues/DLAA-1"


def _get_mocked_managers():
    employees_dal = EmployeesDAL()
    shakira_jira_mock = ShakiraJiraApiClient(employees_dal=employees_dal)
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
                {"name": "Design quality", "alsoPostsToJira": True},
                {"name": "Lesson content issue", "alsoPostsToJira": False},
                {"name": "TTS / Visemes / Mouth animations", "alsoPostsToJira": False},
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
            release_blocker=False,
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
            slack_report_type="Design quality",
            client_specified_slack_channel_name=None,
            related_issue_key="DEL-1733",
            summary="summary",
            description=None,
            generated_description=None,
            reporter_email=None,
            pre_release=False,
            release_blocker=False,
            files={},
        )

        shakira_jira_mock.create_issue.assert_called_once_with(
            project="DLAA",
            feature="Callouts",
            labels=["design-quality"],
            summary="summary",
            description=None,
            generated_description=None,
            reporter_email=None,
            pre_release=False,
            will_post_to_slack=True,
            priority="Medium",
            related_issue_exists=True,
        )

        shakira_jira_mock.get_issue_details.assert_called_once_with(issue_key="DEL-1733")

        shakira_jira_mock.link_issues.assert_called_once_with(
            outward_issue_key="DEL-1733", inward_issue_key="DLAA-1"
        )

        shakira_slack_mock.post_issue.assert_called_once_with(
            project="DLAA",
            slack_channel=SlackChannel.DESIGN_QUALITY,
            summary="summary",
            reporter_email=None,
            jira_issue_url=_JIRA_ISSUE_URL,
            post_info_in_reply=False,
            screenshot=None,
        )

    def test_report_design_quality_issue_forwards_to_area_design_quality_channel(self):
        shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
        shakira_jira_mock.get_issue_details = MagicMock(return_value={"id": 1})

        shakira_manager.report_issue(
            project="DLAA",
            feature="Explain my Answer",
            slack_report_type="Design quality",
            client_specified_slack_channel_name=None,
            related_issue_key="DEL-1733",
            summary="summary",
            description=None,
            generated_description=None,
            reporter_email=None,
            pre_release=False,
            release_blocker=False,
            files={},
        )

        shakira_jira_mock.create_issue.assert_called_once_with(
            project="DLAA",
            feature="Explain my Answer",
            labels=["design-quality"],
            summary="summary",
            description=None,
            generated_description=None,
            reporter_email=None,
            pre_release=False,
            will_post_to_slack=True,
            priority="Medium",
            related_issue_exists=True,
        )

        shakira_jira_mock.get_issue_details.assert_called_once_with(issue_key="DEL-1733")

        shakira_jira_mock.link_issues.assert_called_once_with(
            outward_issue_key="DEL-1733", inward_issue_key="DLAA-1"
        )

        shakira_slack_mock.post_issue.assert_any_call(
            project="DLAA",
            slack_channel=SlackChannel.DESIGN_QUALITY,
            summary="summary",
            reporter_email=None,
            jira_issue_url=_JIRA_ISSUE_URL,
            post_info_in_reply=False,
            screenshot=None,
        )

        shakira_slack_mock.post_issue.assert_any_call(
            project="DLAA",
            slack_channel=SlackChannel.DESIGN_QUALITY_MONETIZATION,
            summary="summary",
            reporter_email=None,
            jira_issue_url=_JIRA_ISSUE_URL,
            post_info_in_reply=False,
            screenshot=None,
        )

        assert shakira_slack_mock.post_issue.call_count == 2

    def test_design_quality_forwarding_with_combined_area_channel(self):
        """Verify that the forwarding works for the combined learning (R&D and Scaling) channel."""
        shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
        shakira_jira_mock.get_issue_details = MagicMock(return_value={"id": 1})

        shakira_manager.report_issue(
            project="DLAA",
            feature="Path",
            slack_report_type="Design quality",
            client_specified_slack_channel_name=None,
            related_issue_key="DEL-1733",
            summary="summary",
            description=None,
            generated_description=None,
            reporter_email=None,
            pre_release=False,
            release_blocker=False,
            files={},
        )

        shakira_jira_mock.create_issue.assert_called_once_with(
            project="DLAA",
            feature="Path",
            labels=["design-quality"],
            summary="summary",
            description=None,
            generated_description=None,
            reporter_email=None,
            pre_release=False,
            will_post_to_slack=True,
            priority="Medium",
            related_issue_exists=True,
        )

        shakira_jira_mock.get_issue_details.assert_called_once_with(issue_key="DEL-1733")

        shakira_jira_mock.link_issues.assert_called_once_with(
            outward_issue_key="DEL-1733", inward_issue_key="DLAA-1"
        )

        shakira_slack_mock.post_issue.assert_any_call(
            project="DLAA",
            slack_channel=SlackChannel.DESIGN_QUALITY,
            summary="summary",
            reporter_email=None,
            jira_issue_url=_JIRA_ISSUE_URL,
            post_info_in_reply=False,
            screenshot=None,
        )

        shakira_slack_mock.post_issue.assert_any_call(
            project="DLAA",
            slack_channel=SlackChannel.DESIGN_QUALITY_LEARNING,
            summary="summary",
            reporter_email=None,
            jira_issue_url=_JIRA_ISSUE_URL,
            post_info_in_reply=False,
            screenshot=None,
        )

        assert shakira_slack_mock.post_issue.call_count == 2

    def test_report_issue_with_invalid_related_jira_ticket(self):
        shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
        shakira_jira_mock.get_issue_details = MagicMock(return_value={})

        shakira_manager.report_issue(
            project="DLAA",
            feature="Callouts",
            slack_report_type="Design quality",
            client_specified_slack_channel_name=None,
            related_issue_key="DEL-1733",
            summary="summary",
            description=None,
            generated_description=None,
            reporter_email=None,
            pre_release=False,
            release_blocker=False,
            files={},
        )

        shakira_jira_mock.create_issue.assert_called_once_with(
            project="DLAA",
            feature="Callouts",
            labels=["design-quality"],
            summary="summary",
            description=None,
            generated_description=None,
            reporter_email=None,
            pre_release=False,
            will_post_to_slack=False,
            priority="Medium",
            related_issue_exists=False,
        )

        shakira_jira_mock.get_issue_details.assert_called_once_with(issue_key="DEL-1733")
        assert not shakira_jira_mock.link_issues.called
        assert not shakira_slack_mock.post_issue.called

    def test_report_issue_to_slack_only_v1(self):
        shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
        shakira_manager.report_issue(
            project="DLAA",
            feature=None,
            slack_report_type="TTS / Visemes / Mouth animations",
            client_specified_slack_channel_name=None,
            related_issue_key=None,
            summary="summary",
            description=None,
            generated_description=None,
            reporter_email=None,
            pre_release=False,
            release_blocker=False,
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
            feature=None,
            slack_report_type="TTS / Visemes / Mouth animations",
            client_specified_slack_channel_name=None,
            related_issue_key="DLAA-1733",
            summary="summary",
            description=None,
            generated_description=None,
            reporter_email=None,
            pre_release=False,
            release_blocker=False,
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
            slack_report_type="TTS / Visemes / Mouth animations",
            client_specified_slack_channel_name=None,
            related_issue_key=None,
            summary="summary",
            description=None,
            generated_description=None,
            reporter_email=None,
            pre_release=False,
            release_blocker=False,
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
            feature="Design quality",
            slack_report_type=None,
            client_specified_slack_channel_name=None,
            related_issue_key=None,
            summary="summary",
            description=None,
            generated_description=None,
            reporter_email=None,
            pre_release=False,
            release_blocker=False,
            files={},
        )

        shakira_jira_mock.create_issue.assert_called_once_with(
            project="DLAA",
            feature="Design quality",
            labels=["design-quality"],
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
            slack_channel=SlackChannel.DESIGN_QUALITY,
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
            slack_report_type="Design quality",
            client_specified_slack_channel_name=None,
            related_issue_key=None,
            summary="summary",
            description=None,
            generated_description=None,
            reporter_email=None,
            pre_release=False,
            release_blocker=False,
            files={},
        )

        shakira_jira_mock.create_issue.assert_called_once_with(
            project="DLAA",
            feature="Callouts",
            labels=["design-quality"],
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
            slack_channel=SlackChannel.DESIGN_QUALITY,
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
            release_blocker=False,
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
            release_blocker=False,
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

    def test_report_issue_release_blocker(self):
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
            release_blocker=True,
            files={},
        )

        shakira_jira_mock.create_issue.assert_called_once_with(
            project="DLAA",
            feature="Callouts",
            labels=[JIRA_RELEASE_BLOCKER_LABEL],
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

    def test_upload_artifacts_success(self):
        shakira_jira_mock, _, shakira_manager = _get_mocked_managers()
        resp = shakira_manager.upload_artifacts(
            jira_issue_key="TEST-1234",
            files={"screenshot": "screenshot.png"},
        )

        shakira_jira_mock.upload_attachments.assert_called_once_with(
            "TEST", "TEST-1234", {"screenshot": "screenshot.png"}
        )
        assert resp["issueKey"] == "TEST-1234"

    def test_upload_artifacts_jira_error(self):
        shakira_jira_mock, _, shakira_manager = _get_mocked_managers()
        mock_jira_response = requests.models.Response()
        mock_jira_response.status_code = 500
        shakira_jira_mock.upload_attachments.side_effect = requests.HTTPError(
            "JIRA internal error", response=mock_jira_response
        )

        resp = shakira_manager.upload_artifacts(
            jira_issue_key="TEST-1234",
            files={"screenshot": "screenshot.png"},
        )

        assert resp["error"] == (
            "Error uploading attachments to JIRA for TEST-1234: JIRA internal error",
            500,
        )

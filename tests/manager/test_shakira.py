import unittest
from typing import Tuple
from unittest.mock import MagicMock

import requests

from jeeves.dal.employees import EmployeesDAL
from jeeves.manager.gpt_priority_estimator import GPTPriorityEstimator, GPTPriorityResponse
from jeeves.manager.shakira import SLACK_CHANNEL_MD, ShakiraManager
from jeeves.manager.shakira_jira import ShakiraJiraApiClient
from jeeves.manager.shakira_slack import ShakiraSlackApiClient
from jeeves.model.jira_priorities import JiraPriority
from jeeves.model.jira_ticket_text import JiraTicketText
from jeeves.model.slack_channel import SlackChannel
from jeeves.util.shakira import JIRA_RELEASE_BLOCKER_LABEL

_JIRA_ISSUE_URL = "https://jira.com/issues/DLAA-1"


def _get_mocked_managers() -> (
    Tuple[GPTPriorityEstimator, ShakiraJiraApiClient, ShakiraSlackApiClient, ShakiraManager]
):
    gpt_priority_estimator_mock = GPTPriorityEstimator(ai_completions_dal=MagicMock())

    employees_dal = EmployeesDAL()
    shakira_jira_mock = ShakiraJiraApiClient(employees_dal=employees_dal)
    shakira_jira_mock.add_comment = MagicMock()
    shakira_jira_mock.create_issue = MagicMock(return_value="DLAA-1")
    shakira_jira_mock.get_issue_details = MagicMock(return_value="None")
    shakira_jira_mock.issue_url = MagicMock(return_value=_JIRA_ISSUE_URL)
    shakira_jira_mock.link_issues = MagicMock()
    shakira_jira_mock.set_priority = MagicMock()
    shakira_jira_mock.upload_attachments = MagicMock()

    shakira_slack_mock = ShakiraSlackApiClient()
    shakira_slack_mock.post_info_in_reply = MagicMock()
    shakira_slack_mock.post_issue = MagicMock(return_value="post1")

    return (
        gpt_priority_estimator_mock,
        shakira_jira_mock,
        shakira_slack_mock,
        ShakiraManager(gpt_priority_estimator_mock, shakira_jira_mock, shakira_slack_mock),
    )


class Test(unittest.TestCase):
    def test_get_slack_report_types(self):
        _, _, _, shakira_manager = _get_mocked_managers()
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
        _, shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
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
            localization_contractor=False,
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
            related_issue_exists=False,
            localization_contractor=False,
        )
        assert not shakira_slack_mock.post_issue.called

    def test_report_issue_with_valid_related_jira_ticket(self):
        _, shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
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
            localization_contractor=False,
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
            related_issue_exists=True,
            localization_contractor=False,
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
        _, shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
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
            localization_contractor=False,
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
            related_issue_exists=True,
            localization_contractor=False,
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
        _, shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
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
            localization_contractor=False,
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
            related_issue_exists=True,
            localization_contractor=False,
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
        _, shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
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
            localization_contractor=False,
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
            related_issue_exists=False,
            localization_contractor=False,
        )

        shakira_jira_mock.get_issue_details.assert_called_once_with(issue_key="DEL-1733")
        assert not shakira_jira_mock.link_issues.called
        assert not shakira_slack_mock.post_issue.called

    def test_report_issue_to_slack_only_v1(self):
        _, shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
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
            localization_contractor=False,
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
        _, shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
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
            localization_contractor=False,
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
        _, shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
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
            localization_contractor=False,
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
        _, shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
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
            localization_contractor=False,
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
            related_issue_exists=False,
            localization_contractor=False,
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
        _, shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
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
            localization_contractor=False,
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
            related_issue_exists=False,
            localization_contractor=False,
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
        _, shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
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
            localization_contractor=False,
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
            related_issue_exists=False,
            localization_contractor=False,
        )
        assert not shakira_slack_mock.post_issue.called

    def test_report_issue_summary_too_long(self):
        _, shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
        shakira_manager.report_issue(
            project="DLAA",
            feature="Callouts",
            slack_report_type=None,
            client_specified_slack_channel_name=None,
            related_issue_key=None,
            summary="a" * 256,
            description=None,
            generated_description=None,
            reporter_email=None,
            pre_release=False,
            release_blocker=False,
            files={},
            localization_contractor=False,
        )

        shakira_jira_mock.create_issue.assert_called_once_with(
            project="DLAA",
            feature="Callouts",
            labels=[],
            summary="a" * 252 + "...",
            description=None,
            generated_description=None,
            reporter_email=None,
            pre_release=False,
            will_post_to_slack=False,
            related_issue_exists=False,
            localization_contractor=False,
        )
        assert not shakira_slack_mock.post_issue.called

    def test_report_issue_release_blocker(self):
        _, shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
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
            localization_contractor=False,
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
            related_issue_exists=False,
            localization_contractor=False,
        )
        assert not shakira_slack_mock.post_issue.called

    def test_set_priority(self) -> None:
        gpt_priority_estimator_mock, shakira_jira_mock, _, shakira_manager = _get_mocked_managers()
        priority_str = "Highest"
        reason = "App crashing blocks all user activity."
        gpt_priority_estimator_mock.estimate_priority = MagicMock(
            return_value=GPTPriorityResponse(JiraPriority.HIGHEST, reason)
        )
        ticket_text = JiraTicketText(
            title="Major bug",
            description="App crashes on startup",
        )
        # pylint: disable=protected-access
        shakira_manager._set_priority(issue_key="DLAI-1", project="DLAI", ticket_text=ticket_text)
        shakira_jira_mock.set_priority.assert_called_once_with("DLAI", "DLAI-1", priority_str)
        shakira_jira_mock.add_comment.assert_called_once_with(
            "DLAI",
            "DLAI-1",
            f"The priority was automatically set to {{{{{priority_str}}}}} by GPT for the reason: {{{{{reason.strip('.')}}}}}."
            f"\n\nPlease change any incorrect priorities and report any major issues to {SLACK_CHANNEL_MD}.",
        )

    def test_set_priority_no_priority(self) -> None:
        gpt_priority_estimator_mock, shakira_jira_mock, _, shakira_manager = _get_mocked_managers()
        priority_str = "Unprioritized"
        reason = "Not enough context"
        gpt_priority_estimator_mock.estimate_priority = MagicMock(
            return_value=GPTPriorityResponse(JiraPriority.UNPRIORITIZED, reason)
        )
        ticket_text = JiraTicketText(
            title="Fix this",
            description="What's going on here?",
        )
        # pylint: disable=protected-access
        shakira_manager._set_priority(issue_key="DLAI-1", project="DLAI", ticket_text=ticket_text)
        assert not shakira_jira_mock.set_priority.called
        shakira_jira_mock.add_comment.assert_called_once_with(
            "DLAI",
            "DLAI-1",
            f"The priority was automatically set to {{{{{priority_str}}}}} by GPT for the reason: {{{{{reason}}}}}."
            f"\n\nPlease change any incorrect priorities and report any major issues to {SLACK_CHANNEL_MD}.",
        )

    def test_set_priority_jira_error(self) -> None:
        gpt_priority_estimator_mock, shakira_jira_mock, _, shakira_manager = _get_mocked_managers()
        shakira_jira_mock.set_priority.side_effect = requests.HTTPError(
            "JIRA internal error", response=MagicMock(status_code=500)
        )
        gpt_priority_estimator_mock.estimate_priority = MagicMock(
            return_value=GPTPriorityResponse(
                JiraPriority.HIGHEST, "App crashing blocks all user activity"
            )
        )
        ticket_text = JiraTicketText(
            title="Major bug",
            description="App crashes on startup",
        )
        # pylint: disable=protected-access
        shakira_manager._set_priority(issue_key="DLAI-1", project="DLAI", ticket_text=ticket_text)
        assert not shakira_jira_mock.add_comment.assert_called_once_with(
            "DLAI",
            "DLAI-1",
            "Could not estimate the priority with GPT. Please set the priority manually.",
        )

    def test_set_priority_gpt_error(self) -> None:
        gpt_priority_estimator_mock, shakira_jira_mock, _, shakira_manager = _get_mocked_managers()
        gpt_priority_estimator_mock.ai_completions_dal.ask.side_effect = (
            requests.exceptions.RequestException("GPT internal error")
        )

        ticket_text = JiraTicketText(
            title="Major bug",
            description="App crashes on startup",
        )
        # pylint: disable=protected-access
        shakira_manager._set_priority(issue_key="DLAI-1", project="DLAI", ticket_text=ticket_text)
        shakira_jira_mock.add_comment.assert_called_once_with(
            "DLAI",
            "DLAI-1",
            "Could not estimate the priority with GPT. Please set the priority manually.",
        )

    def test_upload_artifacts_success(self):
        _, shakira_jira_mock, _, shakira_manager = _get_mocked_managers()
        resp = shakira_manager.upload_artifacts(
            jira_issue_key="TEST-1234",
            files={"screenshot": "screenshot.png"},
        )

        shakira_jira_mock.upload_attachments.assert_called_once_with(
            "TEST", "TEST-1234", {"screenshot": "screenshot.png"}
        )
        assert resp["issueKey"] == "TEST-1234"

    def test_upload_artifacts_jira_error(self):
        _, shakira_jira_mock, _, shakira_manager = _get_mocked_managers()
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

    def test_upload_artifacts_no_artifacts(self):
        _, shakira_jira_mock, _, shakira_manager = _get_mocked_managers()

        resp = shakira_manager.upload_artifacts(
            jira_issue_key="TEST-1234",
            files={},
        )

        assert not shakira_jira_mock.upload_attachments.called
        assert resp["issueKey"] == "TEST-1234"

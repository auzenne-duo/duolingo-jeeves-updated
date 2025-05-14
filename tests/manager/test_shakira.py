import unittest
from typing import Tuple
from unittest.mock import MagicMock, call, patch

import requests
from werkzeug.datastructures import FileStorage

from jeeves.dal.employees import EmployeesDAL
from jeeves.manager.gpt_log_summarizer import GPTLogSummarizer, LogSummaryResponse
from jeeves.manager.gpt_priority_estimator import GPTPriorityEstimator, GPTPriorityResponse
from jeeves.manager.gpt_screenshot_summarizer import GPTScreenshotSummarizer
from jeeves.manager.shakira import SLACK_CHANNEL_MD, ShakiraManager
from jeeves.manager.shakira_jira import ShakiraJiraApiClient
from jeeves.manager.shakira_slack import ShakiraSlackApiClient
from jeeves.model.jira_priorities import JiraPriority
from jeeves.model.jira_ticket_text import JiraTicketText
from jeeves.model.slack_channel import SlackChannel
from jeeves.util.shakira import JIRA_RELEASE_BLOCKER_LABEL

# pylint: disable=protected-access

_JIRA_ISSUE_URL = "https://jira.com/issues/DLAA-1"


def _get_mocked_managers() -> (
    Tuple[
        GPTLogSummarizer,
        GPTPriorityEstimator,
        GPTScreenshotSummarizer,
        ShakiraJiraApiClient,
        ShakiraSlackApiClient,
        ShakiraManager,
    ]
):
    gpt_log_summarizer_mock = GPTLogSummarizer(ai_completions_dal=MagicMock())
    gpt_log_summarizer_mock.summarize_logs = MagicMock(return_value=LogSummaryResponse([]))
    gpt_priority_estimator_mock = GPTPriorityEstimator(ai_completions_dal=MagicMock())
    gpt_screenshot_summarizer_mock = GPTScreenshotSummarizer(ai_completions_dal=MagicMock())
    gpt_screenshot_summarizer_mock.generate_description = MagicMock(
        return_value="screenshot summary"
    )

    employees_dal = EmployeesDAL()
    shakira_jira_mock = ShakiraJiraApiClient(employees_dal=employees_dal)
    shakira_jira_mock.add_comment = MagicMock()
    shakira_jira_mock.create_issue = MagicMock(return_value="DLAA-1")
    shakira_jira_mock.get_issue_details = MagicMock(
        return_value={
            "fields": {
                "summary": "summary",
                "description": {
                    "type": "doc",
                    "version": 1,
                    "content": [
                        {
                            "type": "paragraph",
                            "content": [
                                {"type": "text", "text": "Description Formatting"},
                                {"type": "hardBreak"},
                                {"type": "text", "text": "Generated info"},
                            ],
                        }
                    ],
                },
            }
        }
    )
    shakira_jira_mock.issue_url = MagicMock(return_value=_JIRA_ISSUE_URL)
    shakira_jira_mock.link_issues = MagicMock()
    shakira_jira_mock.set_priority = MagicMock()
    shakira_jira_mock.upload_attachments = MagicMock()
    shakira_jira_mock.insert_rich_text_into_description = MagicMock()

    shakira_slack_mock = ShakiraSlackApiClient()
    shakira_slack_mock.post_info_in_reply = MagicMock()
    shakira_slack_mock.post_issue = MagicMock(return_value="post1")

    return (
        gpt_log_summarizer_mock,
        gpt_priority_estimator_mock,
        gpt_screenshot_summarizer_mock,
        shakira_jira_mock,
        shakira_slack_mock,
        ShakiraManager(
            gpt_log_summarizer_mock,
            gpt_priority_estimator_mock,
            gpt_screenshot_summarizer_mock,
            shakira_jira_mock,
            shakira_slack_mock,
            MagicMock(),
            upload_to_s3=MagicMock(),
        ),
    )


class Test(unittest.TestCase):
    def test_get_slack_report_types(self):
        _, _, _, _, _, shakira_manager = _get_mocked_managers()
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
        _, _, _, shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
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
        _, _, _, shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
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
        _, _, _, shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
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
        _, _, _, shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
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
        _, _, _, shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
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
        _, _, _, shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
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
        _, _, _, shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
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
        _, _, _, shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
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
        _, _, _, shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
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
        _, _, _, shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
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
        _, _, _, shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
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
        _, _, _, shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
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
        _, _, _, shakira_jira_mock, shakira_slack_mock, shakira_manager = _get_mocked_managers()
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

    def test_screenshot_summary(self) -> None:
        _, _, gpt_screenshot_summarizer_mock, _, _, shakira_manager = _get_mocked_managers()
        mock_stream = MagicMock()
        mock_stream.read.return_value = b"fake image data"
        files = {
            "screenshot": FileStorage(
                stream=mock_stream,
                filename="screenshot.png",
                content_type="image/png",
                name="screenshot",
            )
        }
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
            files=files,
            localization_contractor=False,
        )
        gpt_screenshot_summarizer_mock.generate_description.assert_called_once_with(
            b"fake image data",
            "png",
            "summary",
        )

    def test_set_priority(self) -> None:
        _, gpt_priority_estimator_mock, _, shakira_jira_mock, _, shakira_manager = (
            _get_mocked_managers()
        )
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
        _, gpt_priority_estimator_mock, _, shakira_jira_mock, _, shakira_manager = (
            _get_mocked_managers()
        )
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
        _, gpt_priority_estimator_mock, _, shakira_jira_mock, _, shakira_manager = (
            _get_mocked_managers()
        )
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
        _, gpt_priority_estimator_mock, _, shakira_jira_mock, _, shakira_manager = (
            _get_mocked_managers()
        )
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
        _, _, _, shakira_jira_mock, _, shakira_manager = _get_mocked_managers()
        mock_screenshot = MagicMock()
        # Patch app_registry to return a mock executor
        with patch("jeeves.manager.shakira.app_registry") as mock_app_registry:
            mock_executor = MagicMock()
            mock_app_registry.return_value = mock_executor
            # Patch background methods to avoid side effects
            # pylint: disable=protected-access
            shakira_manager._generate_and_upload_screenshot_summary = MagicMock()
            # pylint: disable=protected-access
            shakira_manager._summarize_logs = MagicMock()
            resp = shakira_manager.upload_artifacts(
                jira_issue_key="TEST-1234",
                files={"screenshot": mock_screenshot},
            )

            shakira_jira_mock.upload_attachments.assert_called_once_with(
                "TEST", "TEST-1234", {"screenshot": mock_screenshot}
            )
            assert resp["issueKey"] == "TEST-1234"
            # Check that executor.submit was called for both background tasks
            submit_calls = [call[0][0] for call in mock_executor.submit.call_args_list]
            # pylint: disable=protected-access
            assert shakira_manager._generate_and_upload_screenshot_summary in submit_calls
            # pylint: disable=protected-access
            assert shakira_manager._summarize_logs in submit_calls

    def test_upload_artifacts_jira_error(self):
        _, _, _, shakira_jira_mock, _, shakira_manager = _get_mocked_managers()
        mock_screenshot = MagicMock()
        mock_jira_response = requests.models.Response()
        mock_jira_response.status_code = 500
        shakira_jira_mock.upload_attachments.side_effect = requests.HTTPError(
            "JIRA internal error", response=mock_jira_response
        )

        resp = shakira_manager.upload_artifacts(
            jira_issue_key="TEST-1234",
            files={"screenshot": mock_screenshot},
        )

        assert resp["error"] == (
            "TEST-1234: Error uploading attachments to JIRA: JIRA internal error",
            500,
        )

    def test_upload_artifacts_no_artifacts(self):
        _, _, _, shakira_jira_mock, _, shakira_manager = _get_mocked_managers()

        resp = shakira_manager.upload_artifacts(
            jira_issue_key="TEST-1234",
            files={},
        )

        assert not shakira_jira_mock.upload_attachments.called
        assert resp["issueKey"] == "TEST-1234"

    def test_parse_log_files_with_screenshot(self):
        _, _, _, _, _, shakira_manager = _get_mocked_managers()
        # Create mock file storage objects
        mock_stream1 = MagicMock()
        mock_stream1.read.return_value = b"error: something failed"
        mock_file1 = FileStorage(
            stream=mock_stream1,
            filename="log1.txt",
            content_type="text/plain",
            name="log1.txt",
        )
        files = {
            "log1.txt": mock_file1,
        }
        # pylint: disable=protected-access
        result = shakira_manager._parse_log_files(files)
        expected = {
            "log1.txt": ["error: something failed"],
        }
        self.assertEqual(result, expected)
        # Verify streams were reset
        mock_stream1.seek.assert_has_calls([call(0), call(0)])

    def test_summarize_logs_no_files(self):
        gpt_log_summarizer_mock, _, _, _, _, shakira_manager = _get_mocked_managers()
        # Should return None and not call summarize_logs
        # pylint: disable=protected-access
        result = shakira_manager._summarize_logs(
            issue_key="DLAA-1",
            summary="summary",
            description="description",
            files={},
        )
        assert result is None
        assert not gpt_log_summarizer_mock.summarize_logs.called

    def test_summarize_logs_no_description_or_summary(self):
        gpt_log_summarizer_mock, _, _, _, _, shakira_manager = _get_mocked_managers()
        # Should return None and not call summarize_logs
        # pylint: disable=protected-access
        result = shakira_manager._summarize_logs(
            issue_key="DLAA-1",
            summary=None,
            description=None,
            files={"log.txt": ["log line"]},
        )
        assert result is None
        assert not gpt_log_summarizer_mock.summarize_logs.called

    def test_summarize_logs_success(self):
        gpt_log_summarizer_mock, _, _, _, _, shakira_manager = _get_mocked_managers()
        mock_summary_response = MagicMock()
        mock_summary_response.format.return_value = "summary text"
        gpt_log_summarizer_mock.summarize_logs.return_value = mock_summary_response
        # pylint: disable=protected-access
        shakira_manager._upload_to_s3 = MagicMock()
        files = {"log.txt": ["log line 1", "log line 2"]}
        # pylint: disable=protected-access
        shakira_manager._summarize_logs(
            issue_key="DLAA-1",
            summary="summary",
            description="description",
            files=files,
        )
        gpt_log_summarizer_mock.summarize_logs.assert_called_once()
        shakira_manager._upload_to_s3.assert_called_once_with(
            "log_summaries/DLAA-1.txt", b"summary text"
        )

    def test_summarize_logs_error_in_summarize(self):
        gpt_log_summarizer_mock, _, _, _, _, shakira_manager = _get_mocked_managers()
        gpt_log_summarizer_mock.summarize_logs.side_effect = Exception("fail summarize")
        # pylint: disable=protected-access
        shakira_manager._upload_to_s3 = MagicMock()
        files = {"log.txt": ["log line 1", "log line 2"]}
        # Should not raise, should not call upload_to_s3
        # pylint: disable=protected-access
        shakira_manager._summarize_logs(
            issue_key="DLAA-1",
            summary="summary",
            description="description",
            files=files,
        )
        gpt_log_summarizer_mock.summarize_logs.assert_called_once()
        assert not shakira_manager._upload_to_s3.called

    def test_summarize_logs_error_in_upload(self):
        gpt_log_summarizer_mock, _, _, _, _, shakira_manager = _get_mocked_managers()
        mock_summary_response = MagicMock()
        mock_summary_response.format.return_value = "summary text"
        gpt_log_summarizer_mock.summarize_logs.return_value = mock_summary_response
        # pylint: disable=protected-access
        shakira_manager._upload_to_s3 = MagicMock(side_effect=Exception("fail upload"))
        files = {"log.txt": ["log line 1", "log line 2"]}
        # Should not raise
        # pylint: disable=protected-access
        shakira_manager._summarize_logs(
            issue_key="DLAA-1",
            summary="summary",
            description="description",
            files=files,
        )
        gpt_log_summarizer_mock.summarize_logs.assert_called_once()
        shakira_manager._upload_to_s3.assert_called_once_with(
            "log_summaries/DLAA-1.txt", b"summary text"
        )

    def test_parse_log_files_unicode_decode_error(self):
        _, _, _, _, _, shakira_manager = _get_mocked_managers()
        # Create a mock file storage that raises UnicodeDecodeError
        mock_stream = MagicMock()

        def raise_unicode_decode(*args, **kwargs):
            raise UnicodeDecodeError("utf-8", b"\xff", 0, 1, "invalid start byte")

        mock_stream.read.side_effect = raise_unicode_decode
        mock_file = FileStorage(
            stream=mock_stream,
            filename="badlog.txt",
            content_type="text/plain",
            name="badlog.txt",
        )
        files = {"badlog.txt": mock_file}
        # pylint: disable=protected-access
        result = shakira_manager._parse_log_files(files)
        assert result == {}

    def test_parse_log_files_other_exception(self):
        _, _, _, _, _, shakira_manager = _get_mocked_managers()
        # Create a mock file storage that raises a generic Exception
        mock_stream = MagicMock()
        mock_stream.read.side_effect = Exception("some error")
        mock_file = FileStorage(
            stream=mock_stream,
            filename="errorlog.txt",
            content_type="text/plain",
            name="errorlog.txt",
        )
        files = {"errorlog.txt": mock_file}
        # pylint: disable=protected-access
        result = shakira_manager._parse_log_files(files)
        assert result == {}

    def test_find_duplicates_gpt_issue_details_none(self):
        _, _, _, shakira_jira_mock, _, shakira_manager = _get_mocked_managers()
        shakira_jira_mock.get_issue_details = MagicMock(return_value=None)
        # pylint: disable=protected-access
        result = shakira_manager._find_duplicates_gpt("DUP-KEY")
        assert result == []

    def test_find_duplicates_gpt_find_duplicates_raises(self):
        _, _, _, shakira_jira_mock, _, shakira_manager = _get_mocked_managers()
        shakira_jira_mock.get_issue_details = MagicMock(return_value={"fields": {}})
        shakira_manager._gpt_duplicate_detector.find_duplicates = MagicMock(
            side_effect=Exception("fail")
        )
        # pylint: disable=protected-access
        result = shakira_manager._find_duplicates_gpt("DUP-KEY")
        assert result == []

    def test_find_duplicates_gpt_no_duplicates(self):
        _, _, _, shakira_jira_mock, _, shakira_manager = _get_mocked_managers()
        shakira_jira_mock.get_issue_details = MagicMock(return_value={"fields": {}})
        shakira_manager._gpt_duplicate_detector.find_duplicates = MagicMock(return_value=[])
        # pylint: disable=protected-access
        result = shakira_manager._find_duplicates_gpt("DUP-KEY")
        assert result == []

    def test_find_duplicates_gpt_uploads_to_s3_and_handles_upload_error(self):
        _, _, _, shakira_jira_mock, _, shakira_manager = _get_mocked_managers()
        shakira_jira_mock.get_issue_details = MagicMock(return_value={"fields": {}})
        shakira_manager._gpt_duplicate_detector.find_duplicates = MagicMock(
            return_value=[("DUP-1", "reason")]
        )
        shakira_manager._upload_to_s3 = MagicMock(side_effect=Exception("fail upload"))
        # pylint: disable=protected-access
        result = shakira_manager._find_duplicates_gpt("DUP-KEY")
        assert result == [("DUP-1", "reason")]
        shakira_manager._upload_to_s3.assert_called_once()

    def test_create_ai_summary_no_rich_text(self):
        _, _, _, shakira_jira_mock, _, shakira_manager = _get_mocked_managers()
        shakira_manager._find_duplicates_gpt = MagicMock(return_value=[])
        shakira_manager._gpt_log_summarizer.generate_log_summary_rich_text = MagicMock(
            return_value=[]
        )
        shakira_jira_mock.insert_rich_text_into_description = MagicMock()
        # pylint: disable=protected-access
        shakira_manager._create_ai_summary("DUP-KEY", None)
        shakira_jira_mock.insert_rich_text_into_description.assert_not_called()

    def test_create_ai_summary_handles_exception(self):
        _, _, _, shakira_jira_mock, _, shakira_manager = _get_mocked_managers()
        shakira_manager._find_duplicates_gpt = MagicMock(side_effect=Exception("fail"))
        shakira_jira_mock.insert_rich_text_into_description = MagicMock()
        # pylint: disable=protected-access
        shakira_manager._create_ai_summary("DUP-KEY", None)
        shakira_jira_mock.insert_rich_text_into_description.assert_not_called()

    def test_create_ai_disabled_log_summarization_feature(self):
        _, _, _, shakira_jira_mock, _, shakira_manager = _get_mocked_managers()
        # Simulate finding duplicates and log summary
        dups = [("DUP-1", "reason")]
        rich_text_dups = ["duplicate rich text"]
        rich_text_logs = ["log summary rich text"]
        shakira_manager._find_duplicates_gpt = MagicMock(return_value=dups)
        shakira_manager._gpt_duplicate_detector.generate_duplicates_rich_text = MagicMock(
            return_value=rich_text_dups
        )
        shakira_manager._gpt_log_summarizer.generate_log_summary_rich_text = MagicMock(
            return_value=rich_text_logs
        )
        shakira_jira_mock.insert_rich_text_into_description = MagicMock()

        # pylint: disable=protected-access
        shakira_manager._create_ai_summary("DUP-KEY", "disable feature")

        shakira_jira_mock.insert_rich_text_into_description.assert_called_once()
        args, _ = shakira_jira_mock.insert_rich_text_into_description.call_args
        # The rich text should include both duplicate and log summary
        assert rich_text_dups[0] in str(args[1])
        assert rich_text_logs[0] not in str(args[1])
        assert len(args[1]) == 2

    def test_create_ai_summary_happy_path(self):
        _, _, _, shakira_jira_mock, _, shakira_manager = _get_mocked_managers()
        # Simulate finding duplicates and log summary
        dups = [("DUP-1", "reason")]
        rich_text_dups = ["duplicate rich text"]
        rich_text_logs = ["log summary rich text"]
        shakira_manager._find_duplicates_gpt = MagicMock(return_value=dups)
        shakira_manager._gpt_duplicate_detector.generate_duplicates_rich_text = MagicMock(
            return_value=rich_text_dups
        )
        shakira_manager._gpt_log_summarizer.generate_log_summary_rich_text = MagicMock(
            return_value=rich_text_logs
        )
        shakira_jira_mock.insert_rich_text_into_description = MagicMock()

        # pylint: disable=protected-access
        shakira_manager._create_ai_summary("DUP-KEY", "Video Call")

        # Should call insert_rich_text_into_description with both rich text parts
        shakira_jira_mock.insert_rich_text_into_description.assert_called_once()
        args, _ = shakira_jira_mock.insert_rich_text_into_description.call_args
        # The rich text should include both duplicate and log summary
        assert rich_text_dups[0] in str(args[1])
        assert rich_text_logs[0] in str(args[1])
        assert len(args[1]) == 3
        # Assert order: dups before logs
        rich_text_str = str(args[1])
        assert rich_text_str.index(rich_text_dups[0]) < rich_text_str.index(rich_text_logs[0])

"""
Interface for interacting with the Slack and JIRA managers for shakira routes.
"""

from typing import Dict, List, Optional, Tuple, Union

from duolingo_base.util import registry

from jeeves.lib.profiling import traced_function
from jeeves.manager.shakira_jira import ShakiraJiraApiClient
from jeeves.manager.shakira_slack import ShakiraSlackApiClient
from jeeves.model.slack_channel import SlackChannel
from jeeves.util.priority_estimator import PriorityEstimator
from jeeves.util.shakira import (
    JIRA_PROJ_TO_PLATFORM,
    JIRA_RELEASE_BLOCKER_LABEL,
    JIRA_VIA_JEEVES_LABEL,
)

_VIA_JEEVES_MARKER = "[via Jeeves]"

_SHAKIRA_FEATURES_TO_SLACK_CHANNEL = {
    "Visual polish": SlackChannel.VISUAL_POLISH,
    "Lesson content / accepted translations": SlackChannel.FEEDBACK_LANGUAGE,
    "TTS: mispronunciation": SlackChannel.FEEDBACK_TTS,
    "TTS: missing": SlackChannel.PROJ_MISSING_TTS,
    "Feature request / feedback": SlackChannel.FEEDBACK_PRODUCT,
}

_SLACK_REPORT_TYPE_TO_SLACK_CHANNEL = {
    "Lesson content issue": SlackChannel.FEEDBACK_LANGUAGE,
    "TTS is mispronounced": SlackChannel.FEEDBACK_TTS,
    "TTS is missing": SlackChannel.PROJ_MISSING_TTS,
    "Visual polish": SlackChannel.VISUAL_POLISH,
    "Feature request": SlackChannel.FEEDBACK_PRODUCT,
}

_SLACK_CHANNELS_TO_JIRA_LABELS = {
    SlackChannel.VISUAL_POLISH: "visual-polish",
    SlackChannel.LITERACY_TESTING: "shakira",
}


@registry.bind(
    jira_client=registry.reference(ShakiraJiraApiClient),
    slack_client=registry.reference(ShakiraSlackApiClient),
)
class ShakiraManager:
    def __init__(self, jira_client: ShakiraJiraApiClient, slack_client: ShakiraSlackApiClient):
        self._jira_client = jira_client
        self._slack_client = slack_client

    def get_shake_to_report_tokens(self, project: Optional[str]) -> Dict[str, str]:
        """
        Gets API tokens for Jira and Slack depending on the project.

        Parameters:
             project: Platform (e.g., DLAA, DLAI, DLAW)

        Returns:
            Dictionary of API tokens for Jira and Slack.
        """

        jira_token = self._jira_client.get_jira_api_token(project)
        slack_token = self._slack_client.get_slack_api_token()

        return {"jira": jira_token, "slack": slack_token}

    def get_project_error_message(self, project: str) -> Optional[str]:
        """
        If the project is invalid, return an error message. Otherwise return None.
        """
        return (
            f"Invalid project - must be one of {list(JIRA_PROJ_TO_PLATFORM)}"
            if project not in JIRA_PROJ_TO_PLATFORM
            else None
        )

    def get_features(self, projects: Union[str, List[str]]) -> List[str]:
        """
        Get possible values for the "Feature" issue field in a project.

        parameters
            projects: e.g. DLAA, DLAI, DLAW
        """
        return self._jira_client.get_features(projects)

    def get_slack_report_types(self) -> List[Dict[str, Union[str, bool]]]:
        """
        Returns a list of report types that go to Slack.

        returns: a List[Dict[str, Union[str, bool]]], each dict containing the following fields:
            - "name": the name of the Slack report type.
            - "alsoPostsToJira": whether this Slack report type will also create a Jira issue.
        """
        return [
            {
                "name": channel_name,
                "alsoPostsToJira": channel in _SLACK_CHANNELS_TO_JIRA_LABELS,
            }
            for channel_name, channel in _SLACK_REPORT_TYPE_TO_SLACK_CHANNEL.items()
        ]

    @traced_function()
    def report_issue(
        self,
        project: str,
        feature: Optional[str],
        slack_report_type: Optional[str],
        client_specified_slack_channel_name: Optional[str],
        related_issue_key: Optional[str],
        summary: str,
        description: Optional[str],
        generated_description: Optional[str],
        reporter_email: Optional[str],
        pre_release: bool,
        release_blocker: bool,
        files: Dict[str, "FileStorage"],
    ) -> Dict[str, Union[str, Tuple[str, int]]]:
        """
        Create an issue in JIRA and/or post the issue to Slack, depending on the client_specified_slack_channel_name, feature, and slack_report_type fields.

        parameters:
            project: e.g. DLAA, DLAI, DLAW, LIT, DETBUG
            feature: e.g. Achievements
            slack_report_type: e.g. "Lesson content / accepted translations" or "Visual polish".
            client_specified_slack_channel_name: e.g. #visual-polish. If this is set, override the other parameters and post in this channel.
            related_issue_key: e.g. "DEL-1773". If this is set the related issue will be linked to the new issue.
            summary: Roughly one-sentence summary of issue.
            description: Longer issue description.
            generated_description: Generated information such as app version, fullstory url, session type, etc.
            reporter_email: Email of the duo reporting the issue.
            pre_release: Whether the bug is being reported from pre-release app version.
            release_blocker: Whether the ticket should have a release blocker label
            files: MultiDict of form name to file. The screenshot file should have the form name "screenshot".

        returns: Dict[str, ?] containing one or more of the following fields:
            - "issueKey": str if an issue was created in JIRA.
            - "slackChannel": str if it was posted to Slack.
            - "url": (DEPRECATED) str URL to view the created issue, the Slack channel, or None.
            - "jiraUrl": str if an issue was created in JIRA.
            - "slackUrl": str if it was posted to Slack.
            - "error": Tuple[message: str, code: int] if there was an error creating the issue.

        """
        project_error_message = self.get_project_error_message(project)
        if project_error_message:
            return {
                "error": (
                    project_error_message,
                    400,
                )
            }

        client_specified_slack_channel = (
            SlackChannel.from_name_or_id(client_specified_slack_channel_name)
            if client_specified_slack_channel_name
            else None
        )
        if client_specified_slack_channel_name and not client_specified_slack_channel:
            return {
                "error": (
                    f"Invalid slack channel - must be one of {[c.name for c in list(SlackChannel)]}",
                    400,
                )
            }
        slack_channel_from_slack_report_type = (
            SlackChannel.LITERACY_TESTING
            if slack_report_type == "literacy"
            else _SLACK_REPORT_TYPE_TO_SLACK_CHANNEL.get(slack_report_type)
        )
        slack_channel_from_feature = _SHAKIRA_FEATURES_TO_SLACK_CHANNEL.get(feature)
        channel = (
            client_specified_slack_channel
            or slack_channel_from_slack_report_type
            or slack_channel_from_feature
        )

        jira_label_from_channel = _SLACK_CHANNELS_TO_JIRA_LABELS.get(channel)
        jeeves_label = JIRA_VIA_JEEVES_LABEL if summary.startswith(_VIA_JEEVES_MARKER) else None
        rc_blocker_label = JIRA_RELEASE_BLOCKER_LABEL if release_blocker else None

        screenshot = files.get("screenshot")

        post_to_slack_only = channel is not None and jira_label_from_channel is None
        if related_issue_key and not post_to_slack_only:
            related_issue_details = self._jira_client.get_issue_details(issue_key=related_issue_key)
            related_issue_exists = (
                related_issue_details is not None and related_issue_details.get("id") is not None
            )
        else:
            related_issue_exists = False

        related_issue_invalid = related_issue_key is not None and not related_issue_exists

        priority = PriorityEstimator.estimate_priority(summary, feature, reporter_email)

        should_post_to_slack = (
            channel is not None and not related_issue_invalid
        ) or post_to_slack_only
        should_post_to_jira = jira_label_from_channel is not None or not should_post_to_slack
        issue_key = None
        issue_url = None
        if should_post_to_jira:
            issue_key = self._jira_client.create_issue(
                project=project,
                feature=feature,
                labels=[
                    label
                    for label in [jira_label_from_channel, jeeves_label, rc_blocker_label]
                    if label is not None
                ],
                summary=summary,
                description=description,
                generated_description=generated_description,
                reporter_email=reporter_email,
                pre_release=pre_release,
                will_post_to_slack=should_post_to_slack,
                priority=priority,
                related_issue_exists=related_issue_exists,
            )
            if issue_key:
                self._jira_client.upload_attachments(project, issue_key, files)
                issue_url = self._jira_client.issue_url(issue_key)

                if related_issue_exists:
                    self._jira_client.link_issues(
                        outward_issue_key=related_issue_key,
                        inward_issue_key=issue_key,
                    )

                # add comment that priority is automatically generated
                comment = f"Priority was automatically assigned {priority}. Please change any incorrect priorities so we can incorporate your feedback!"
                self._jira_client.add_comment(project, issue_key, comment)

            if not should_post_to_slack:
                return (
                    {"issueKey": issue_key, "url": issue_url, "jiraUrl": issue_url}
                    if issue_key
                    else {"error": ("There was an issue posting to Jira.", 500)}
                )

        if should_post_to_slack:
            post_info_in_reply = (
                issue_url is None and (description or generated_description) is not None
            )
            post_id = self._slack_client.post_issue(
                project=project,
                slack_channel=channel,
                summary=summary,
                reporter_email=reporter_email,
                jira_issue_url=issue_url,
                post_info_in_reply=post_info_in_reply,
                screenshot=screenshot,
            )

            if post_info_in_reply and post_id:
                self._slack_client.post_info_in_reply(
                    slack_channel=channel,
                    original_post_id=post_id,
                    summary=summary,
                    description=description,
                    generated_description=generated_description,
                )

            optional_channel_url = channel.url() if post_id else None
            return (
                {
                    "slackChannel": channel.name if post_id else None,
                    "url": issue_url or optional_channel_url,
                    "issueKey": issue_key,
                    "slackUrl": optional_channel_url,
                    "jiraUrl": issue_url,
                }
                if post_id or issue_key
                else {"error": ("There was a problem reporting the issue.", 500)}
            )

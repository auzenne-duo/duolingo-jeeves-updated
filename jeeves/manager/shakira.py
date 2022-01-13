"""
Interface for interacting with the Slack and JIRA managers for shakira routes.
"""

from typing import Dict, List, Optional, Tuple, Union

from jeeves.manager.shakira_jira import ShakiraJiraClient
from jeeves.manager.shakira_slack import ShakiraSlackClient
from jeeves.model.slack_channel import SlackChannel
from jeeves.util.shakira import JIRA_PROJ_TO_PLATFORM

_SHAKIRA_FEATURES_TO_SLACK_CHANNEL = {
    "Visual polish": SlackChannel.VISUAL_POLISH,
    "Lesson content / accepted translations": SlackChannel.FEEDBACK_LANGUAGE,
    "TTS: mispronunciation": SlackChannel.FEEDBACK_TTS,
    "Feature request / feedback": SlackChannel.FEEDBACK_PRODUCT,
}

_SLACK_CHANNELS_THAT_RECEIVE_REPORTS = {
    channel.name: channel
    for channel in [
        SlackChannel.VISUAL_POLISH,
        SlackChannel.FEEDBACK_LANGUAGE,
        SlackChannel.FEEDBACK_TTS,
        SlackChannel.FEEDBACK_PRODUCT,
    ]
}

_SLACK_CHANNELS_TO_JIRA_LABELS = {SlackChannel.VISUAL_POLISH: "visual-polish"}


class ShakiraManager:
    def __init__(self, jira_client, slack_client):
        self._jira_client = jira_client
        self._slack_client = slack_client

    def get_project_error_message(self, project: str) -> Optional[str]:
        """
        If the project is invalid, return an error message. Otherwise return None.
        """
        return (
            f"Invalid project - must be one of {list(JIRA_PROJ_TO_PLATFORM.keys())}"
            if project not in JIRA_PROJ_TO_PLATFORM.keys()
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
            for channel_name, channel in _SLACK_CHANNELS_THAT_RECEIVE_REPORTS.items()
        ]

    def report_issue(
        self,
        project: str,
        feature: Optional[str],
        slack_report_type: Optional[str],
        client_specified_slack_channel_name: Optional[str],
        summary: str,
        description: Optional[str],
        generated_description: Optional[str],
        reporter_email: Optional[str],
        pre_release: bool,
        files: Dict[str, "FileStorage"],
    ) -> Dict[str, Union[str, Tuple[str, int]]]:
        """
        Create an issue in JIRA and/or post the issue to Slack, depending on the client_specified_slack_channel_name, feature, and slack_report_type fields.

        parameters:
            project: e.g. DLAA, DLAI, DLAW
            feature: e.g. Achievements
            slack_report_type: e.g. "Lesson content / accepted translations" or "Visual polish".
            client_specified_slack_channel_name: e.g. #visual-polish. If this is set, override the other parameters and post in this channel.
            summary: Roughly one-sentence summary of issue.
            description: Longer issue description.
            generated_description: Generated information such as app version, fullstory url, session type, etc.
            reporter_email: Email of the duo reporting the issue.
            pre_release: Whether the bug is being reported from pre-release app version.
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
        slack_channel_from_slack_report_type = _SLACK_CHANNELS_THAT_RECEIVE_REPORTS.get(
            slack_report_type
        )
        slack_channel_from_feature = _SHAKIRA_FEATURES_TO_SLACK_CHANNEL.get(feature)
        channel = (
            client_specified_slack_channel
            or slack_channel_from_slack_report_type
            or slack_channel_from_feature
        )
        jira_label_from_channel = _SLACK_CHANNELS_TO_JIRA_LABELS.get(channel)
        screenshot = files.get("screenshot")

        if client_specified_slack_channel_name and not client_specified_slack_channel:
            return {
                "error": (
                    f"Invalid slack channel - must be one of {[c.name for c in list(SlackChannel)]}",
                    400,
                )
            }

        should_post_to_slack = channel is not None
        should_post_to_jira = jira_label_from_channel is not None or not should_post_to_slack

        issue_key = None
        issue_url = None
        if should_post_to_jira:
            issue_key = self._jira_client.create_issue(
                project=project,
                feature=feature,
                label=jira_label_from_channel,
                summary=summary,
                description=description,
                generated_description=generated_description,
                reporter_email=reporter_email,
                pre_release=pre_release,
                will_post_to_slack=should_post_to_slack,
            )
            if issue_key:
                self._jira_client.upload_attachments(project, issue_key, files)
                issue_url = self._jira_client.issue_url(issue_key)

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


Shakira = ShakiraManager(ShakiraJiraClient, ShakiraSlackClient)

"""
Interface for interacting with the Slack and JIRA managers for shakira routes.
"""

from typing import Dict, List, Optional, Tuple, Union

from jeeves.manager.shakira_jira import ShakiraJiraClient
from jeeves.manager.shakira_slack import ShakiraSlackClient, SlackChannel
from jeeves.util.shakira import JIRA_PROJ_TO_PLATFORM

_SHAKIRA_FEATURES_TO_SLACK_CHANNEL = {
    "Visual polish": SlackChannel.VISUAL_POLISH,
    "Lesson content / accepted translations": SlackChannel.FEEDBACK_LANGUAGE,
    "TTS: mispronunciation": SlackChannel.FEEDBACK_TTS,
    "Feature request / feedback": SlackChannel.FEEDBACK_PRODUCT,
}

_SLACK_CHANNELS_THAT_ALSO_POST_TO_JIRA = {SlackChannel.VISUAL_POLISH}


class ShakiraManager:
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
        return ShakiraJiraClient.get_features(projects)

    def report_issue(
        self,
        project: str,
        feature: Optional[str],
        client_specified_slack_channel_name: Optional[str],
        summary: str,
        description: Optional[str],
        generated_description: Optional[str],
        reporter_email: Optional[str],
        pre_release: bool,
        files: Dict[str, "FileStorage"],
    ) -> Dict[str, Union[str, Tuple[str, int]]]:
        """
        Either create an issue in Jira or post the screenshot to slack, depending on the feature.

        parameters:
            project: e.g. DLAA, DLAI, DLAW
            feature: e.g. Achievements
            client_specified_slack_channel_name: e.g. #visual-polish. If this is set, override the feature and post in this channel.
            summary: Rougly one-sentence summary of issue.
            description: Longer issue description.
            generated_description: Generated information such as app version, fullstory url, session type, etc.
            reporter_emai: Email of the duo reporting the issue.
            pre_release: Whether the bug is being reported from pre-release app version.
            files: MultiDict of form name to file. The screenshot file should have the form name "screenshot".

        returns: Dict[str, ?] containing one or more of the following fields:
            - "issueKey": str if an issue was created in JIRA
            - "slackChannel": str if it was posted to Slack
            - "url": URL to view the created issue
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
        slack_channel_from_feature = _SHAKIRA_FEATURES_TO_SLACK_CHANNEL.get(feature)
        channel = client_specified_slack_channel or slack_channel_from_feature
        should_also_post_to_jira = channel in _SLACK_CHANNELS_THAT_ALSO_POST_TO_JIRA
        screenshot = files.get("screenshot")

        if client_specified_slack_channel_name and not client_specified_slack_channel:
            return {
                "error": (
                    f"Invalid slack channel - must be one of {[c.name for c in list(SlackChannel)]}",
                    400,
                )
            }

        should_post_to_slack = channel is not None
        should_post_to_jira = should_also_post_to_jira or not should_post_to_slack

        issue_key = None
        issue_url = None
        if should_post_to_jira:
            issue_key = ShakiraJiraClient.create_issue(
                project=project,
                feature=feature,
                summary=summary,
                description=description,
                generated_description=generated_description,
                reporter_email=reporter_email,
                pre_release=pre_release,
                will_post_to_slack=should_post_to_slack,
            )
            if issue_key:
                ShakiraJiraClient.upload_attachments(project, issue_key, files)
                issue_url = ShakiraJiraClient.issue_url(issue_key)

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
            post_id = ShakiraSlackClient.post_issue(
                project=project,
                slack_channel=channel,
                summary=summary,
                reporter_email=reporter_email,
                jira_issue_url=issue_url,
                post_info_in_reply=post_info_in_reply,
                screenshot=screenshot,
            )

            if post_info_in_reply and post_id:
                ShakiraSlackClient.post_info_in_reply(
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


Shakira = ShakiraManager()

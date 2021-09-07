"""
Interface for interacting with the Slack and JIRA managers for shakira routes.
"""

from typing import Dict, List, Optional, Tuple, Union

from jeeves.manager.shakira_jira import ShakiraJiraClient
from jeeves.manager.shakira_slack import ShakiraSlackClient, SlackChannel
from jeeves.util.shakira import JIRA_PROJ_TO_PLATFORM

SHAKIRA_FEATURES_TO_SLACK_CHANNEL = {
    "Visual polish": SlackChannel.VISUAL_POLISH,
    "Lesson content / accepted translations": SlackChannel.FEEDBACK_LANGUAGE,
    "TTS: mispronunciation": SlackChannel.FEEDBACK_TTS,
    "Feature request / feedback": SlackChannel.FEEDBACK_PRODUCT,
}


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
            projects: e.g. DLAA, DLAI
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
            project: e.g. DLAI, DLAA
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
        slack_channel_from_feature = SHAKIRA_FEATURES_TO_SLACK_CHANNEL.get(feature)
        channel = client_specified_slack_channel or slack_channel_from_feature
        screenshot = files.get("screenshot")

        if client_specified_slack_channel_name and not client_specified_slack_channel:
            return {
                "error": (
                    f"Invalid slack channel - must be one of {[c.name for c in list(SlackChannel)]}",
                    400,
                )
            }
        if client_specified_slack_channel_name and not screenshot:
            return {
                "error": (f"Must provide a screenshot file in order to post issue in Slack.", 400)
            }

        if channel and screenshot:
            post_info_in_reply = (description or generated_description) is not None
            post_id = ShakiraSlackClient.post_screenshot(
                project=project,
                slack_channel=channel,
                summary=summary,
                reporter_email=reporter_email,
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
            return (
                {"slackChannel": channel.name, "url": channel.url()}
                if post_id
                else {"error": ("There was an issue posting to Slack.", 500)}
            )
        else:
            issue_key = ShakiraJiraClient.create_issue(
                project=project,
                feature=feature,
                summary=summary,
                description=description,
                generated_description=generated_description,
                reporter_email=reporter_email,
                pre_release=pre_release,
            )
            if issue_key:
                ShakiraJiraClient.upload_attachments(project, issue_key, files)
            return (
                {"issueKey": issue_key, "url": ShakiraJiraClient.issue_url(issue_key)}
                if issue_key
                else {"error": ("There was an issue posting to Jira.", 500)}
            )


Shakira = ShakiraManager()

"""
Interface for interacting with the Slack and JIRA managers for shakira routes.
"""

from typing import Union, List, Optional, Dict

from jeeves.manager.shakira_jira import ShakiraJiraClient
from jeeves.manager.shakira_slack import ShakiraSlackClient, SlackChannel

SHAKIRA_FEATURES_TO_SLACK_CHANNEL = {
    "Visual polish": SlackChannel.VISUAL_POLISH,
    "Lesson content / accepted translations": SlackChannel.FEEDBACK_LANGUAGE,
    "TTS: mispronunciation": SlackChannel.FEEDBACK_TTS,
    "Feature request / feedback": SlackChannel.FEEDBACK_PRODUCT,
}


class ShakiraManager:
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
        slack_channel: Optional[str],
        summary: str,
        description: str,
        generated_description: Optional[str],
        reporter_email: Optional[str],
        pre_release: bool,
        files: Dict[str, "FileStorage"],
    ) -> Dict[str, str]:
        """
        Either create an issue in JIRA or post the screenshot to slack, depending on the feature.

        parameters:
            project: e.g. DLAI, DLAA
            feature: e.g. Achievements
            slack_channel: e.g. #visual-polish. If this is set, override the feature and post in this channel.
            summary: Rougly one-sentence summary of issue.
            description: Longer issue description.
            generated_description: Generated information such as app version, fullstory url, session type, etc.
            reporter_emai: Email of the duo reporting the issue.
            pre_release: Whether the bug is being reported from pre-release app version.
            files: MultiDict of form name to file. The screenshot file should have the form name "screenshot".

        returns: Dict[str, str] containing one of the following fields:
            - "issueKey" if an issue was created in JIRA
            - "slackChannel" if it was posted to Slack

        """
        slack_channel_from_feature = SHAKIRA_FEATURES_TO_SLACK_CHANNEL.get(feature)
        client_specified_slack_channel = (
            SlackChannel.from_name_or_id(slack_channel) if slack_channel else None
        )
        channel = client_specified_slack_channel or slack_channel_from_feature
        screenshot = files.get("screenshot")
        if channel and screenshot:
            post_id = ShakiraSlackClient.post_screenshot(
                project=project,
                slack_channel=channel,
                summary=summary,
                reporter_email=reporter_email,
                screenshot=screenshot,
            )
            if post_id:
                ShakiraSlackClient.post_info_in_reply(
                    slack_channel=channel,
                    original_post_id=post_id,
                    description=description,
                    generated_description=generated_description,
                )
            return {"slackChannel": channel.name if post_id else None}
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
            return {"issueKey": issue_key}


Shakira = ShakiraManager()

"""
Manager for interacting with the Slack API for shakira.
"""

import json
import os
from typing import Optional

import duo_logging.legacy as rollbar  # type: ignore[import]
from requests import post
from requests.exceptions import RequestException

from jeeves.model.slack_channel import SlackChannel
from jeeves.util.error_util import print_request_exception
from jeeves.util.shakira import JIRA_PROJ_TO_PLATFORM

_API = "https://slack.com/api/"
_API_TOKEN = os.environ.get("SHAKIRA_SLACK_API_TOKEN")


class ShakiraSlackApiClient:
    def get_slack_api_token(self):
        """
        Returns Slack API token.
        """
        return _API_TOKEN

    def _post_chat_message(
        self,
        slack_channel: SlackChannel,
        summary: str,
        caption: str,
    ) -> Optional[str]:
        """
        Post a chat message in the appropriate slack channel along with a brief summary.
        For reference: https://api.slack.com/methods/chat.postMessage

        parameters:
            slack_channel: Channel to post the screenshot to.
            summary: Roughly one-sentence summary of issue.
            caption: Additional information about the issue.
        returns:
            post id: str API ID of the created slack post.
        """
        url = f"{_API}/chat.postMessage"
        headers = {"Authorization": f"Bearer {_API_TOKEN}", "Content-Type": "application/json"}

        blocks = [{"type": "header", "text": {"type": "plain_text", "text": summary}}]
        data = {
            "channel": slack_channel.channel_id,
            "blocks": blocks,
        }
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": caption}})

        try:
            r = post(
                url,
                headers=headers,
                data=json.dumps(data),
            )
            r.raise_for_status()
            response_json = json.loads(r.text)
            if response_json["ok"]:
                return response_json["ts"]
            else:
                rollbar.report_message(
                    f"Could not post message to Slack: {response_json['error']}", "error"
                )
                return None
        except RequestException as e:
            print_request_exception(e, rollbar_level="error")

    def _post_screenshot(
        self,
        slack_channel: SlackChannel,
        summary: str,
        caption: str,
        screenshot: "FileStorage",
    ) -> Optional[str]:
        """
        Posts the screenshot in the appropriate slack channel along with a brief summary.
        For reference: https://api.slack.com/methods/files.upload

        parameters:
            project: e.g. DLAA, DLAI, DLAW
            slack_channel: Channel to post the screenshot to.
            summary: Roughly one-sentence summary of issue.
            caption: Additional information about the issue.
            screenshot: Screenshot taken when the phone was shook.

        returns:
            post id: str API ID of the created slack post.
        """
        url = f"{_API}/files.upload"
        headers = {"Authorization": f"Bearer {_API_TOKEN}"}
        initial_comment = f"*{summary}*\n{caption}"

        screenshot.seek(0)
        try:
            r = post(
                url,
                headers=headers,
                files=[("file", screenshot)],
                data={
                    "initial_comment": initial_comment,
                    "link_names": True,
                    "channels": slack_channel.channel_id,
                },
            )
            r.raise_for_status()
            response_json = json.loads(r.text)
            if response_json["ok"]:
                # The API allows you to post multiple messages to multiple channels at once. We only post
                # to one public channel at a time but we still have to dig through a bunch of lists and dicts.
                public_shares = [
                    share
                    for shares in response_json["file"]["shares"]["public"].values()
                    for share in shares
                ]
                if len(public_shares) > 0:
                    return public_shares[0]["ts"]
            else:
                rollbar.report_message(
                    f"Could not post screenshot to Slack: {response_json['error']}", "error"
                )
                return None
        except RequestException as e:
            print_request_exception(e, rollbar_level="error")
            return None

    def post_issue(
        self,
        project: str,
        slack_channel: SlackChannel,
        summary: str,
        reporter_email: Optional[str],
        jira_issue_url: Optional[str],
        post_info_in_reply: bool,
        screenshot: Optional["FileStorage"],
    ) -> Optional[str]:
        """
        Post a message (including screenshots, if applicable) in the appropriate slack channel along with a brief summary.

        parameters:
            project: e.g. DLAA, DLAI, DLAW
            slack_channel: Channel to post the screenshot to.
            summary: Rougly one-sentence summary of issue.
            reporter_email: Email of the user reporting the issue.
            jira_issue_url: URL to the related Jira issue, if applicable.
            post_info_in_reply: Whether details will be posted in a reply.
            screenshot: Screenshot taken when the phone was shook, if available.

        returns:
            post id: str API ID of the created slack post.
        """
        reporter_username = (
            f'<@{reporter_email.split("@")[0]}>' if reporter_email else "unknown user"
        )
        platform = JIRA_PROJ_TO_PLATFORM.get(project, "unknown platform")
        additional_details = ""
        if jira_issue_url:
            additional_details += f"\n<{jira_issue_url}>"
        elif post_info_in_reply:
            additional_details += "\n_See thread for details._"
        caption = f"Reported by {reporter_username} on {platform}{additional_details}"

        if screenshot:
            return self._post_screenshot(slack_channel, summary, caption, screenshot)
        else:
            return self._post_chat_message(slack_channel, summary, caption)

    def post_info_in_reply(
        self,
        slack_channel: SlackChannel,
        original_post_id: str,
        summary: str,
        description: Optional[str],
        generated_description: Optional[str],
    ):
        """
        Posts a longer description in a follow-up reply to the initial post.
        https://api.slack.com/methods/chat.postMessage

        parameters:
            original_post_id: ID returned by post_screenshot
            slack_channel: Channel to post the screenshot to.
            summary: Roughly one-sentence summary of the issue.
            description: Longer issue description.
            generated_description: Generated information such as app version, fullstory url, session type, etc.
        """
        url = f"{_API}/chat.postMessage"
        headers = {"Authorization": f"Bearer {_API_TOKEN}", "Content-Type": "application/json"}
        blocks = [{"type": "header", "text": {"type": "plain_text", "text": summary}}]
        if description:
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": description}})
        data = {
            "channel": slack_channel.channel_id,
            "thread_ts": original_post_id,
            "blocks": blocks,
        }
        if generated_description:
            data["attachments"] = [
                {
                    "blocks": [
                        {
                            "type": "section",
                            "text": {"type": "mrkdwn", "text": generated_description},
                        }
                    ]
                }
            ]
        try:
            r = post(
                url,
                headers=headers,
                data=json.dumps(data),
            )
            r.raise_for_status()
        except RequestException as e:
            print_request_exception(e, rollbar_level="error")

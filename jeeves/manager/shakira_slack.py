"""
Manager for interacting with the Slack API for shakira.
"""

import json
import os
from collections import namedtuple
from enum import Enum
from typing import Optional

from requests import post
from requests.exceptions import RequestException

from jeeves.util.error_util import print_request_exception
from jeeves.util.shakira import JIRA_PROJ_TO_PLATFORM


class SlackChannel(namedtuple("SlackChannel", "name channel_id"), Enum):
    VISUAL_POLISH = "#visual-polish", "C01867ZCY7J"
    FEEDBACK_LANGUAGE = "#feedback-language", "C0KHQRPDZ"
    FEEDBACK_PRODUCT = "#feedback-product", "C013VGDCU5R"
    FEEDBACK_TTS = "#feedback-tts", "C01FWHDCLP4"
    POST_TEST_RESULTS = "#post-test-results", "CJNN7RJBD"

    @classmethod
    def from_name_or_id(cls, name_or_id: str) -> Optional["SlackChannel"]:
        for channel in list(cls):
            if channel.name == name_or_id or channel.channel_id == name_or_id:
                return channel
        return None

    def url(self):
        return f"https://duolingo.slack.com/archives/{self.channel_id}"


_API = "https://slack.com/api/"
_API_TOKEN = os.environ.get("SHAKIRA_SLACK_API_TOKEN")


class ShakiraSlackApiClient:
    def post_screenshot(
        self,
        project: str,
        slack_channel: SlackChannel,
        summary: str,
        reporter_email: Optional[str],
        post_info_in_reply: bool,
        screenshot: "FileStorage",
    ) -> Optional[str]:
        """
        Posts the screenshot in the appropriate slack channel along with a brief summary.
        For reference: https://api.slack.com/methods/files.upload

        parameters:
            project: e.g. DLAA, DLAI, DLAW
            slack_channel: Channel to post the screenshot to.
            summary: Rougly one-sentence summary of issue.
            reporter_emai: Email of the user reporting the issue.
            screenshot: Screenshot taken when the phone was shook.

        returns:
            post id: str API ID of the created slack post.
        """
        url = f"{_API}/files.upload"
        headers = {"Authorization": f"Bearer {_API_TOKEN}"}
        reporter_username = (
            f'<@{reporter_email.split("@")[0]}>' if reporter_email else "unknown user"
        )
        platform = JIRA_PROJ_TO_PLATFORM.get(project, "unknown platform")
        see_thread_for_details = "\n_See thread for details._" if post_info_in_reply else ""
        initial_comment = (
            f"*{summary}*\nReported by {reporter_username} on {platform}{see_thread_for_details}"
        )
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
                return None
        except RequestException as e:
            print_request_exception(e)
            return None

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
            print_request_exception(e)


ShakiraSlackClient = ShakiraSlackApiClient()

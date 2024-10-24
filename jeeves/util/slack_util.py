import json

from requests import post
from requests.exceptions import RequestException

from jeeves.util.error_util import print_request_exception


class SlackUtil:
    """
    Utility class for sending messages to Slack.
    """

    def __init__(self, slack_channel_id: str, slack_api_token: str = None):
        self.slack_channel_id = slack_channel_id
        self.slack_api_token = slack_api_token

    def send_slack_message(self, slack_message: str) -> None:
        """
        Given a message, send the message to the channel.
        """
        url = "https://slack.com/api/chat.postMessage"
        headers = {
            "Authorization": f"Bearer {self.slack_api_token}",
            "Content-Type": "application/json; charset=utf-8",
        }

        block = {"text": {"text": slack_message, "type": "mrkdwn"}, "type": "section"}
        data = {
            "channel": self.slack_channel_id,
            "blocks": [block],
        }

        print(f"Sending slack message to {self.slack_channel_id}: {slack_message}")

        try:
            r = post(url, headers=headers, data=json.dumps(data))
            r.raise_for_status()
            print(f"Slack POST response code: {r.status_code}. Response body: {r.json()}")

            # It's lame that slack API returns status code 200 for errors like invalid auth token. See https://api.slack.com/methods/chat.postMessage#errors
            if not r.json().get("ok", False):
                raise RequestException(f"Slack POST failed with error: {r.json()['error']}")
        except RequestException as e:
            print_request_exception(e, log_level="error")

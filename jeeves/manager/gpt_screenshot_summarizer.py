from __future__ import annotations

import logging
import time
from base64 import b64encode
from typing import Optional

from duolingo_base.dal.s3 import S3DownloadException
from duolingo_base.util import registry

from jeeves.dal.ai_completions_dal import AICompletionsDAL
from jeeves.util.s3_client_and_bucket import get_s3_client_and_bucket

LOG = logging.getLogger(__name__)

DESCRIPTION_PROMPT = "Describe this screenshot of the Duolingo app. It is a screenshot attached to a bug report. The bug report summary is: {summary}"


@registry.bind(
    ai_completions_dal=registry.reference(AICompletionsDAL),
)
class GPTScreenshotSummarizer:
    def __init__(self, ai_completions_dal: AICompletionsDAL) -> None:
        self.ai_completions_dal = ai_completions_dal
        self.s3_client, self.s3_bucket = get_s3_client_and_bucket()

    def get_description_s3(self, jira_key: str) -> Optional[str]:
        try:
            data = self.s3_client.download(self.s3_bucket, f"screenshot_summaries/{jira_key}.txt")
            return data.decode("utf-8")
        except S3DownloadException:
            return None

    def poll_for_description_s3(self, jira_key: str, timeout: int = 60) -> Optional[str]:
        start_time = time.time()
        while time.time() - start_time < timeout:
            description = self.get_description_s3(jira_key)
            if description is not None:
                return description
            time.sleep(1)
        return None

    def generate_description(self, screenshot: bytes, extension: str, issue_summary: str) -> str:
        """
        Generates a description of a screenshot from an STR ticket using AIC backend.

        Parameters:
            `screenshot`: The screenshot to summarize as a bytes
            `extension`: The file extension of the screenshot (e.g. "png")
            `issue_summary`: The summary (title) of the JIRA issue the screenshot is from

        Raises:
            ValueError: If the file extension cannot be determined from the screenshot
            requests.exceptions.RequestException: If the AIC backend returns an error
        """
        b64_screenshot = b64encode(screenshot).decode("utf-8")

        url = f"data:image/{extension};base64,{b64_screenshot}"
        message = DESCRIPTION_PROMPT.format(summary=issue_summary)
        messages = [
            {"role": "system", "content": "You are a helpful assistant"},
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": message,
                    },
                    {"type": "image_url", "image_url": {"url": url, "detail": "low"}},
                ],
            },
        ]
        summary = self.ai_completions_dal.ask_messages(messages)
        return summary

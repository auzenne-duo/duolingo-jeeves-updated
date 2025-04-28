from __future__ import annotations

import logging
from base64 import b64encode

from duolingo_base.util import registry
from werkzeug.datastructures import FileStorage

from jeeves.dal.ai_completions_dal import AICompletionsDAL

LOG = logging.getLogger(__name__)

DESCRIPTION_PROMPT = "Describe this screenshot of the Duolingo app. It is a screenshot attached to a bug report. The bug report summary is: {summary}"


@registry.bind(
    ai_completions_dal=registry.reference(AICompletionsDAL),
)
class GPTScreenshotSummarizer:
    def __init__(self, ai_completions_dal: AICompletionsDAL) -> None:
        self.ai_completions_dal = ai_completions_dal

    def get_screenshot_summary(self, screenshot: FileStorage, issue_summary: str) -> str:
        """
        Generates a description of a screenshot from an STR ticket using AIC backend.

        Parameters:
            `screenshot`: The screenshot to summarize as a FileStorage object
                (e.g. from a Flask `request.files`). Expects filename or mimetype
                to determine image format.
            `issue_summary`: The summary (title) of the JIRA issue the screenshot is from

        Raises:
            ValueError: If the file extension cannot be determined from the screenshot
            requests.exceptions.RequestException: If the AIC backend returns an error
        """
        if screenshot.filename:
            extension = screenshot.filename.split(".")[-1]
        elif screenshot.mimetype:
            extension = screenshot.mimetype.split("/")[-1]
        else:
            raise ValueError("Could not determine extension for screenshot")

        # Some other process (probably the file upload) seems to consume this
        # stream previously, so seek back to 0 to read again
        screenshot.stream.seek(0)

        b64_screenshot = b64encode(screenshot.stream.read()).decode("utf-8")

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

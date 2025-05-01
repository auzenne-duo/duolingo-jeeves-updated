import unittest
from unittest.mock import MagicMock

from requests.exceptions import RequestException

from jeeves.manager.gpt_screenshot_summarizer import GPTScreenshotSummarizer


class TestGPTScreenshotSummarizer(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_ai_completions_dal = MagicMock()
        self.summarizer = GPTScreenshotSummarizer(ai_completions_dal=self.mock_ai_completions_dal)

    def test_get_screenshot_summary_success(self) -> None:
        screenshot_bytes = b"fake image data"
        extension = "png"
        issue_summary = "App crashes on startup"
        expected_summary = "The screenshot shows the app crashing screen"

        self.mock_ai_completions_dal.ask_messages.return_value = expected_summary

        result = self.summarizer.get_screenshot_summary(screenshot_bytes, extension, issue_summary)

        self.assertEqual(result, expected_summary)
        self.mock_ai_completions_dal.ask_messages.assert_called_once()

    def test_get_screenshot_summary_ai_error(self) -> None:
        screenshot_bytes = b"fake image data"
        extension = "png"
        issue_summary = "App crashes on startup"

        self.mock_ai_completions_dal.ask_messages.side_effect = RequestException(
            "AI service unavailable"
        )

        with self.assertRaises(RequestException):
            self.summarizer.get_screenshot_summary(screenshot_bytes, extension, issue_summary)

        self.mock_ai_completions_dal.ask_messages.assert_called_once()

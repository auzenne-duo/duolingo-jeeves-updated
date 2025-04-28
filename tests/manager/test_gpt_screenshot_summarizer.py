import unittest
from unittest.mock import MagicMock

from werkzeug.datastructures import FileStorage

from jeeves.manager.gpt_screenshot_summarizer import GPTScreenshotSummarizer


class TestGPTScreenshotSummarizer(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_ai_completions_dal = MagicMock()
        self.summarizer = GPTScreenshotSummarizer(ai_completions_dal=self.mock_ai_completions_dal)

    def test_get_screenshot_summary_with_filename(self) -> None:
        # Create a mock FileStorage object with filename
        mock_screenshot = MagicMock(spec=FileStorage)
        mock_screenshot.filename = "test.png"
        mock_screenshot.stream = MagicMock()
        mock_screenshot.stream.read.return_value = b"fake image data"
        mock_screenshot.stream.seek = MagicMock()

        issue_summary = "App crashes on startup"
        expected_summary = "The screenshot shows the app crashing screen"
        self.mock_ai_completions_dal.ask_messages.return_value = expected_summary

        result = self.summarizer.get_screenshot_summary(mock_screenshot, issue_summary)

        self.assertEqual(result, expected_summary)
        mock_screenshot.stream.seek.assert_called_once_with(0)
        self.mock_ai_completions_dal.ask_messages.assert_called_once()

    def test_get_screenshot_summary_with_mimetype(self) -> None:
        # Create a mock FileStorage object with mimetype
        mock_screenshot = MagicMock(spec=FileStorage)
        mock_screenshot.filename = None
        mock_screenshot.mimetype = "image/jpeg"
        mock_screenshot.stream = MagicMock()
        mock_screenshot.stream.read.return_value = b"fake image data"
        mock_screenshot.stream.seek = MagicMock()

        issue_summary = "UI layout issue"
        expected_summary = "The screenshot shows misaligned UI elements"
        self.mock_ai_completions_dal.ask_messages.return_value = expected_summary

        result = self.summarizer.get_screenshot_summary(mock_screenshot, issue_summary)

        self.assertEqual(result, expected_summary)
        mock_screenshot.stream.seek.assert_called_once_with(0)
        self.mock_ai_completions_dal.ask_messages.assert_called_once()

    def test_get_screenshot_summary_no_extension(self) -> None:
        # Create a mock FileStorage object with no filename or mimetype
        mock_screenshot = MagicMock(spec=FileStorage)
        mock_screenshot.filename = None
        mock_screenshot.mimetype = None

        with self.assertRaises(ValueError):
            self.summarizer.get_screenshot_summary(mock_screenshot, "Test issue")

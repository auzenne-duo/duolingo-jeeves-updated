import unittest
from unittest.mock import MagicMock

import responses

from jeeves.manager.parent_summary_manager import ParentSummaryManager
from jeeves.model.jira_ticket_text import JiraTicketText

mock_ai_completions_dal = MagicMock()


class TestParentSummaryManager(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestParentSummaryManager, self).__init__(*args, **kwargs)
        self.summary_generator = ParentSummaryManager(mock_ai_completions_dal)

    @responses.activate
    def test_generate_summary_and_description(self):
        mock_header = "World character not loading or displaying"
        mock_description = (
            "Multiple users have reported that the world character is not loading or displaying in "
            "various lessons and challenges. Reports indicate that this issue may be transient, "
            "but is reproducible for some users. Some users have reported that the space for the "
            "character still appears, while others say the UI looks different than they remember."
        )

        mock_ai_completions_dal.ask.return_value = f"""
{{
  "title": "{mock_header}",
  "description": "{mock_description}"
}}"""

        tickets = [
            JiraTicketText(
                description="See screenshot", id="DLAI-100", title="World character missing"
            ),
            JiraTicketText(
                description="No world character was shown",
                id="DLAI-101",
                title="missing world character",
            ),
            JiraTicketText(
                description="No characters in any of the lessons in this pebble",
                id="DLAI-102",
                title="missing world character",
            ),
            JiraTicketText(
                description="The animated character didn't load for this challenge; not sure if this is a transient \
                             bug or reproducible.",
                id="DLAI-103",
                title="no characters in any of the lessons in this pebble",
            ),
            JiraTicketText(
                description="UI here looks very different than I remember",
                id="DLAI-104",
                title="Animated character did not load",
            ),
            JiraTicketText(
                description="None shown in this lesson so far",
                id="DLAI-105",
                title="world character missing for speak challenges",
            ),
            JiraTicketText(
                description="I haven't been getting world characters",
                id="DLAI-106",
                title="world characters missing",
            ),
            JiraTicketText(
                description="No world characters in any lessons for this pebble",
                id="DLAI-107",
                title="i haven't been getting world characters",
            ),
            JiraTicketText(
                description="There's still the space for them and it's using the correct tts",
                id="DLAI-108",
                title="no world characters in any lessons for this pebble",
            ),
            JiraTicketText(
                description="It's an empty space in this challenge. I've waited and it hasn't loaded",
                id="DLAI-109",
                title="Missing world character",
            ),
            JiraTicketText(
                description="The character is entirely missing.",
                id="DLAI-110",
                title="The world character isn't loaded",
            ),
            JiraTicketText(
                description="There's space for the character but they aren't showing",
                id="DLAI-111",
                title="character didn't show up",
            ),
            JiraTicketText(
                description="This has been happening 3 nights in a row now",
                id="DLAI-112",
                title="Missing character",
            ),
            JiraTicketText(
                description="The world character didn't show up in this lesson as seen in the screenshot.",
                id="DLAI-113",
                title="Blank Character",
            ),
            JiraTicketText(
                description="Character is missing in this lesson",
                id="DLAI-114",
                title="missing world character",
            ),
            JiraTicketText(
                description="No world character was shown",
                id="DLAI-115",
                title="Missing world character",
            ),
        ]

        response = self.summary_generator.generate_summary_and_description(tickets)
        assert response.title == "World character not loading or displaying"
        assert response.description == (
            "Multiple users have reported that the world character is not loading or "
            "displaying in various lessons and challenges. Reports indicate that this "
            "issue may be transient, but is reproducible for some users. Some users have "
            "reported that the space for the character still appears, while others say the "
            "UI looks different than they remember."
        )

        # Test an error
        mock_ai_completions_dal.ask.return_value = None

        response = self.summary_generator.generate_summary_and_description(tickets)
        assert response.title == "World character missing"
        assert response.description == "See screenshot"


if __name__ == "__main__":
    unittest.main()

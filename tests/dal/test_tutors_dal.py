import unittest
from unittest.mock import MagicMock

import requests
import responses

from jeeves.dal.tutors_dal import TutorsApiDAL


class TestTutorsDAL(unittest.TestCase):
    @responses.activate
    def test_generate_summary(self):
        responses.add(
            responses.POST,
            "https://duolingo-tutors-prod.duolingo.com/2017-06-30/tutors/ai/completion_request",
            body="Title: World character not loading or displaying\nDescription: Multiple users have reported that the world character is not loading or displaying in various lessons and challenges. Reports indicate that this issue may be transient, but is reproducible for some users. Some users have reported that the space for the character still appears, while others say the UI looks different than they remember.",
            status=200,
        )

        headers = [
            "World character missing",
            "missing world character",
            "missing world character",
            "no characters in any of the lessons in this pebble",
            "Animated character did not load",
            "world character missing for speak challenges",
            "world characters missing",
            "i haven't been getting world characters",
            "no world characters in any lessons for this pebble",
            "Missing world character",
            "The world character isn't loaded",
            "character didn't show up",
            "Missing character",
            "Blank Character",
            "missing world character",
            "Missing world character",
        ]

        descriptions = [
            "See screenshot",
            "No world character was shown",
            "No characters in any of the lessons in this pebble",
            "The animated character didn't load for this challenge; not sure if this is a transient bug or reproducible.",
            "UI here looks very different than I remember",
            "None shown in this lesson so far",
            "I haven't been getting world characters",
            "No world characters in any lessons for this pebble",
            "There's still the space for them and it's using the correct tts",
            "It's an empty space in this challenge. I've waited and it hasn't loaded",
            "The character is entirely missing.",
            "There's space for the character but they aren't showing",
            "This has been happening 3 nights in a row now",
            "The world character didn't show up in this lesson as seen in the screenshot.",
            "Character is missing in this lesson",
            "No world character was shown",
        ]
        mock_client = MagicMock()
        mock_client.post.return_value = requests.post(
            "https://duolingo-tutors-prod.duolingo.com/2017-06-30/tutors/ai/completion_request"
        )
        tutors_dal = TutorsApiDAL(mock_client)
        header, description = tutors_dal.generate_summary(headers, descriptions)
        assert header == "World character not loading or displaying"
        assert (
            description
            == "Multiple users have reported that the world character is not loading or displaying in various lessons and challenges. Reports indicate that this issue may be transient, but is reproducible for some users. Some users have reported that the space for the character still appears, while others say the UI looks different than they remember."
        )

        # Test a network error
        responses.add(
            responses.POST,
            "https://duolingo-tutors-prod.duolingo.com/2017-06-30/tutors/ai/completion_request",
            body="",
            status=500,
        )
        mock_client.post.return_value = requests.post(
            "https://duolingo-tutors-prod.duolingo.com/2017-06-30/tutors/ai/completion_request"
        )
        header, description = tutors_dal.generate_summary(headers, descriptions)
        assert header == "World character missing"
        assert description == "See screenshot"

    def test_generate_summary_user_prompt(self):
        """
        Tests that the generate_summary_user_prompt function generates the correct
        prompt for the Tutors service.
        """
        headers = ["Header 1", "Header 2"]
        descriptions = ["Description 1", "Description 2"]
        expected_prompt = "<|im_start|>user<|im_sep|>Title: Header 1\nDescription: Description 1\n\nTitle: Header 2\nDescription: Description 2\n\n<|im_end|>"
        actual_prompt = TutorsApiDAL.generate_summary_user_prompt(headers, descriptions)
        assert actual_prompt == expected_prompt


if __name__ == "__main__":
    unittest.main()

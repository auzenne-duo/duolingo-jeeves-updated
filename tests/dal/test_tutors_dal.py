import unittest
from unittest.mock import MagicMock

import requests
import responses

from jeeves.dal.tutors_dal import TutorsDAL

mock_duolingo_api_client = MagicMock()


class TestTutorsDAL(unittest.TestCase):
    @responses.activate
    def test_ask(self):
        body_text = "Body text here"

        responses.add(
            responses.POST,
            "https://duolingo-tutors-prod.duolingo.com/2017-06-30/tutors/ai/completion_request",
            body=body_text,
            status=200,
        )
        mock_duolingo_api_client.post.return_value = requests.post(
            "https://duolingo-tutors-prod.duolingo.com/2017-06-30/tutors/ai/completion_request"
        )

        tutors_dal = TutorsDAL(mock_duolingo_api_client)
        response = tutors_dal.ask("prompt", "text")
        assert response == body_text

        # Test a network error
        responses.add(
            responses.POST,
            "https://duolingo-tutors-prod.duolingo.com/2017-06-30/tutors/ai/completion_request",
            body="",
            status=500,
        )
        mock_duolingo_api_client.post.return_value = requests.post(
            "https://duolingo-tutors-prod.duolingo.com/2017-06-30/tutors/ai/completion_request"
        )

        response = tutors_dal.ask("prompt", "text")
        assert response is None

    def test_get_prompt(self):
        """
        Tests that the get_prompt function generates the correct
        prompt for the Tutors service.
        """
        system_prompt = "system prompt"
        text = "text"
        expected_prompt = f"<|im_start|>system<|im_sep|>{system_prompt}<|im_end|><|im_start|>user<|im_sep|>{text}<|im_start|>assistant<|im_sep|>"
        actual_prompt = TutorsDAL.get_prompt(system_prompt, text)
        assert actual_prompt == expected_prompt


if __name__ == "__main__":
    unittest.main()

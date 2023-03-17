import logging
import os
from typing import List, Tuple

import requests
from duolingo_base.dal import auth_api
from duolingo_base.dal.duoapi import DuolingoApiClient
from duolingo_base.util import registry

from jeeves.util.error_util import print_request_exception

if os.environ.get("DUOLINGO_JWT"):
    credentials = {"jwt": os.environ.get("DUOLINGO_JWT")}
else:
    credentials = {
        "username": os.environ.get("DUOLINGO_USERNAME"),
        "password": os.environ.get("DUOLINGO_PASSWORD"),
    }
AuthCredentials = registry.define(auth_api.AuthCredentials, **credentials)
AuthAPI = registry.define(auth_api.AuthAPI, credentials=registry.reference(AuthCredentials))
TutorsClient = registry.define(
    DuolingoApiClient,
    url="https://duolingo-tutors-prod.duolingo.com",
    auth_api=registry.reference(AuthAPI),
)

_COMPLETION_REQUEST_ROUTE = "/2017-06-30/tutors/ai/completion_request"

LOG = logging.getLogger(__name__)


@registry.bind(api_client=registry.reference(TutorsClient))
class TutorsApiDAL:
    def __init__(self, api_client: DuolingoApiClient):
        self.client = api_client

    def generate_summary(self, headers: List[str], descriptions: List[str]) -> Tuple[str, str]:
        """
        Given a list of headers and a list of descriptions, generates a summary
        of the descriptions from the Tutors service via AI.

        Parameters:
            headers: A list of headers for the descriptions.
            descriptions: A list of descriptions to summarize.

        Returns:
            A tuple of the header and the full text of the description.
        """
        if not headers or not descriptions:
            raise ValueError("Cannot generate a summary for an empty list of issues.")

        if len(headers) != len(descriptions):
            raise ValueError("The number of headers and descriptions must be the same.")

        if len(headers) == 1:
            return headers[0], descriptions[0]

        # Generate a summary using GPT-3.
        SYSTEM_PROMPT = """
        <|im_start|>system<|im_sep|>Duolingo's users can report bugs, feedback, and feature requests into Jira. Each Jira issue has a title that summarizes the issue and a description with more detail. When given a list of issues that were reported as duplicates, this bot can generate a single title in less than 255 characters and a longer description that summarizes all the duplicate reports. The bot does not give an opinion on the urgency of fixing an issue or whether an issue should be fixed as the goal is to strictly to summarize.<|im_end|>
        """
        user_prompt: str = TutorsApiDAL.generate_summary_user_prompt(headers, descriptions)
        prompt: str = SYSTEM_PROMPT + user_prompt + "<|im_start|>assistant<|im_sep|>"
        try:
            LOG.info(f"Generating summary for {len(headers)} issues")
            LOG.debug(f"Prompt: {prompt.encode('utf-8')}")
            response = self.client.post(
                _COMPLETION_REQUEST_ROUTE,
                json={
                    "allow_caching": False,
                    "max_tokens": 1024,
                    "prompt": prompt,
                    "stop": ["<|im_end|>", "<|diff_marker|>"],
                    "temperature": 1,
                    "top_p": 0.8,
                },
            )
        except requests.exceptions.RequestException as e:
            LOG.warning("Failed to generate summary for %d issues", len(headers))
            LOG.debug(e)
            print_request_exception(e, rollbar_level="warning")
            return headers[0], descriptions[0]
        response_text: str = response.text
        # Log response status code, content, and the username being used
        LOG.debug(f"Username: {os.environ.get('DUOLINGO_USERNAME')}")
        LOG.debug(f"Status Code: {response.status_code}")
        LOG.debug(f"Response: {response_text.encode('utf-8')}")
        # The header is everything between "Title: " and the next new line.
        if "Title: " not in response_text:
            summary_header: str = headers[0]
        else:
            summary_header = response_text.split("Title: ")[1].split("\n")[0]

        # The summary description is after "Description"
        if "Description: " not in response_text:
            summary_description: str = descriptions[0]
        else:
            summary_description = response_text.split("Description: ")[1]

        return summary_header, summary_description

    @classmethod
    def generate_summary_user_prompt(cls, headers: List[str], descriptions: List[str]) -> str:
        """
        Given a list of headers and a list of descriptions, generates a prompt
        for the Tutors service to generate a summary of the descriptions.

        Parameters:
            headers: A list of headers for the descriptions.
            descriptions: A list of descriptions to summarize.

        Returns:
            A string that can be passed as a prompt to the Tutors service.
        """
        prompt = "<|im_start|>user<|im_sep|>"
        for header, description in zip(headers, descriptions):
            prompt += f"""Title: {header}
Description: {description}

"""
        prompt += "<|im_end|>"
        return prompt

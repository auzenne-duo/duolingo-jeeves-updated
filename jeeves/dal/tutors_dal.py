"""
DAL for accessing GPT-4 using the duolingo-tutors api.
"""

import os
from typing import Optional

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


@registry.bind(api_client=registry.reference(TutorsClient))
class TutorsDAL:
    def __init__(self, api_client: DuolingoApiClient):
        self.client = api_client

    @classmethod
    def get_prompt(cls, system_prompt: str, text: str) -> str:
        return f"<|im_start|>system<|im_sep|>{system_prompt}<|im_end|><|im_start|>user<|im_sep|>{text}<|im_start|>assistant<|im_sep|>"

    def ask(self, system_prompt: str, text: str) -> Optional[str]:
        try:
            response = self.client.post(
                _COMPLETION_REQUEST_ROUTE,
                json={
                    "allow_caching": False,
                    "max_tokens": 1024,
                    "prompt": TutorsDAL.get_prompt(system_prompt, text),
                    "stop": ["<|im_end|>", "<|diff_marker|>"],
                    "temperature": 1,
                    "top_p": 0.8,
                },
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print_request_exception(e, rollbar_level="warning")
            return None
        return response.text

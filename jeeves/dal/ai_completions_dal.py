"""
DAL for accessing GPT-4 using the duolingo-ai-completions api.
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
AICompletionsClient = registry.define(
    DuolingoApiClient,
    url="https://duolingo-ai-completions-prod.duolingo.com",
    auth_api=registry.reference(AuthAPI),
)

_EMBEDDING_REQUEST_ROUTE = "/1/ai-completions/embeddings"
_EMBEDDING_MODEL = "text-embedding-ada-002"

_CHAT_COMPLETIONS_ROUTE = "/1/ai-completions/chat-completions"


@registry.bind(api_client=registry.reference(AICompletionsClient))
class AICompletionsDAL:
    def __init__(self, api_client: DuolingoApiClient):
        self.client = api_client

    def ask(self, system_prompt, user_prompt):
        body = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "modelParameters": {"model": "gpt-dv-duo", "maxTokens": 512, "topP": 1.0},
            "taskName": "general",
        }

        try:
            response = self.client.put(
                _CHAT_COMPLETIONS_ROUTE,
                json=body,
                timeout=30,
            )
            response.raise_for_status()
            return response.json()["message"]["content"]
        except requests.exceptions.RequestException as e:
            print_request_exception(e, rollbar_level="warning")
            return None

    def request_embedding(self, text: str) -> Optional[str]:
        try:
            response = self.client.put(
                _EMBEDDING_REQUEST_ROUTE,
                json={"model": _EMBEDDING_MODEL, "input": text},
                timeout=30,
            )
            response.raise_for_status()
            return response.json()["embeddingVector"]
        except requests.exceptions.RequestException as e:
            print_request_exception(e, rollbar_level="warning")
            return None

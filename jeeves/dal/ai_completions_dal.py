"""
DAL for accessing GPT-4 using the duolingo-ai-completions api.
"""

import logging
import os
import time
from typing import Iterable, List, Optional

import requests
from duolingo_base.dal import auth_api
from duolingo_base.dal.duoapi import DuolingoApiClient
from duolingo_base.util import registry

from jeeves.util.error_util import print_request_exception

LOG = logging.getLogger(__name__)

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
_CHAT_COMPLETIONS_MODEL = "gpt-dv-duo"
_CHAT_COMPLETIONS_JSON_MODEL_PREVIEW = "gpt-4-1106-preview"
_BATCH_CHAT_COMPLETIONS_ROUTE = "/1/ai-completions/chat-completions-batch"
_BATCH_CHAT_COMPLETIONS_STATUS_ROUTE = "/1/ai-completions/chat-completion-statuses"


@registry.bind(api_client=registry.reference(AICompletionsClient))
class AICompletionsDAL:
    def __init__(self, api_client: DuolingoApiClient):
        self.client = api_client

    def ask(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 512,
        raise_exceptions: bool = False,
        timeout_seconds: float = 90.0,
        top_p: float = 1.0,
        use_json_mode: bool = False,
    ):
        model = _CHAT_COMPLETIONS_JSON_MODEL_PREVIEW if use_json_mode else _CHAT_COMPLETIONS_MODEL
        body = {
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "modelParameters": {
                "model": model,
                "maxTokens": max_tokens,
                "topP": top_p,
            },
            "taskName": "general",
        }
        if use_json_mode:
            body["modelParameters"]["useJsonMode"] = True

        try:
            response = self.client.put(
                _CHAT_COMPLETIONS_ROUTE,
                json=body,
                timeout=timeout_seconds,
            )
            response.raise_for_status()
            return response.json()["message"]["content"]
        except requests.exceptions.RequestException as e:
            print_request_exception(e, rollbar_level="warning")
            if raise_exceptions:
                raise e
            return None

    def request_embedding(self, text: str, raise_exceptions: bool = False) -> Optional[List[float]]:
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
            if raise_exceptions:
                raise e
            return None

    def batched_ask(
        self,
        system_prompt: str,
        user_prompts: Iterable[str],
        max_tokens: int = 512,
        timeout_seconds: float = 900.0,
        top_p: float = 1.0,
    ) -> List[str]:
        """
        Takes in a system prompt and a batch of user prompts
        and sends them to ai-completions-backend. Returns a list of
        strings where each string is gpt's response to an inputted user_prompt.
        """
        requests_array = []
        for user_prompt in user_prompts:
            request_object = {
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "modelParameters": {
                    "model": _CHAT_COMPLETIONS_MODEL,
                    "maxTokens": max_tokens,
                    "topP": top_p,
                },
                "taskName": "general",
            }
            requests_array.append(request_object)
        try:
            batch_response = self.client.put(
                _BATCH_CHAT_COMPLETIONS_ROUTE,
                json={"requests": requests_array},
                timeout=90,
            )
            batch_response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print_request_exception(e, rollbar_level="warning")
            return None
        LOG.debug(f"AI completions responded with status code {batch_response.status_code}")
        request_hashes = [request["requestHash"] for request in batch_response.json()["responses"]]
        done = False
        results = []
        # use 3 since requests typically take 20-30 seconds so we don't add on more than ~10% to waiting time
        REQUEST_INTERVAL = 3
        # retry every REQUEST_INTERVAL seconds until all responses are done or we time out
        start_time = time.time()
        while not done:
            if time.time() - start_time > timeout_seconds:
                raise TimeoutError(
                    """
                    Timed out waiting for AI completion backend requests to finish.
                    Note that the service may still finish some requests in the background.
                    """
                )
            time.sleep(REQUEST_INTERVAL)
            batch_response = self.client.post(
                _BATCH_CHAT_COMPLETIONS_STATUS_ROUTE,
                json={"requestHashes": request_hashes},
                timeout=90,
            )
            LOG.debug(f"AI completions responded with status code {batch_response.status_code}")
            results = []
            done = True
            LOG.debug(f"Statuses \n{batch_response.json()}")
            for request_response in batch_response.json()["statuses"]:
                if "message" not in request_response:
                    done = False
                    break
                else:
                    results.append(request_response["message"]["content"])
        return results

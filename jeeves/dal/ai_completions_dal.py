"""
DAL for accessing GPT-4 using the duolingo-ai-completions api.
"""

import logging
import time
from typing import Dict, Iterable, List, Optional

import requests
from duolingo_base.dal.duoapi import DuolingoApiClient
from duolingo_base.util import registry

from jeeves.dal.auth_dal import AuthDAL
from jeeves.util.error_util import print_request_exception

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)

_EMBEDDING_REQUEST_ROUTE = "/1/ai-completions/embeddings"
_EMBEDDING_MODEL = "text-embedding-ada-002"

_CHAT_COMPLETIONS_ROUTE = "/1/ai-completions/chat-completions"
_CHAT_COMPLETIONS_MODEL = "gpt-dv-duo"
_CHAT_COMPLETIONS_MODEL_MULTIMODAL = "gpt-4o-mini"
_BATCH_CHAT_COMPLETIONS_ROUTE = "/1/ai-completions/chat-completions-batch"
_BATCH_CHAT_COMPLETIONS_STATUS_ROUTE = "/1/ai-completions/chat-completion-statuses"
BATCH_SIZE = 200


@registry.bind(auth_dal=registry.reference(AuthDAL))
class AICompletionsDAL:
    def __init__(self, auth_dal: AuthDAL, api_client: Optional[DuolingoApiClient] = None):
        if api_client is None:
            self.client = DuolingoApiClient(
                url="https://duolingo-ai-completions-prod.duolingo.com",
                auth_api=auth_dal.auth_api,
            )
        else:
            self.client = api_client

    def ask_messages(
        self,
        messages: List[Dict],
        timeout_seconds: float = 90.0,
        model: str = _CHAT_COMPLETIONS_MODEL_MULTIMODAL,
    ) -> str:
        body = {
            "messages": messages,
            "modelParameters": {
                "model": model,
            },
            "allowCachedCompletions": False,
            "allowRecordingCompletions": False,
            "taskName": "general",
        }

        try:
            response = self.client.put(
                _CHAT_COMPLETIONS_ROUTE,
                json=body,
                timeout=timeout_seconds,
            )
            response.raise_for_status()
            return response.json()["message"]["content"]
        except requests.exceptions.RequestException as e:
            print_request_exception(e, log_level="error")
            raise e

    def ask(
        self,
        system_prompt: str,
        user_prompt: str,
        max_tokens: int = 512,
        raise_exceptions: bool = False,
        timeout_seconds: float = 90.0,
        top_p: float = 1.0,
        use_json_mode: bool = False,
    ) -> Optional[str]:
        model = _CHAT_COMPLETIONS_MODEL
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
            print_request_exception(e, log_level="warning")
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
            print_request_exception(e, log_level="warning")
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
        # use 3 since requests typically take 20-30 seconds so we don't add on more than ~10% to waiting time
        request_interval: float = 3.0,
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
        LOG.debug(f"submitting {len(requests_array)} requests to ai-completions-backend")
        hashes = []
        for start in range(0, len(requests_array), BATCH_SIZE):
            body = {"requests": requests_array[start : start + BATCH_SIZE]}
            LOG.debug(f"submitting batch {start}:{start + BATCH_SIZE}")
            resp = self.client.put(
                _BATCH_CHAT_COMPLETIONS_ROUTE,
                json=body,
            )
            assert resp is not None, "ai-completions-backend request failed and returned None"
            resp.raise_for_status()
            resps = resp.json()["responses"]
            iteration_hashes = [resp["requestHash"] for resp in resps]
            hashes += iteration_hashes

        i = 0
        completions: Dict[str, Optional[str]] = {hash: None for hash in hashes}
        start_time = time.time()
        while True:
            if time.time() - start_time > timeout_seconds:
                raise TimeoutError(
                    """
                    Timed out waiting for AI completion backend requests to finish.
                    Note that the service may still finish some requests in the background.
                    """
                )
            i += 1
            time.sleep(request_interval)
            waiting_hashes = [h for h in hashes if completions[h] is None]
            if not waiting_hashes:
                break
            resp = self.client.post(
                _BATCH_CHAT_COMPLETIONS_STATUS_ROUTE,
                # Limit to BATCH_SIZE to prevent HTTP read timeouts
                json={"requestHashes": waiting_hashes[:BATCH_SIZE]},
            )
            assert resp is not None, "ai-completions-backend request failed and returned None"
            resp.raise_for_status()
            statuses = resp.json()["statuses"]
            for status in statuses:
                if status["status"]["status"] == "SUCCESS":
                    completions[status["requestHash"]] = status["message"]["content"]

            n_succeeded = len([v for v in completions.values() if v is not None])
            LOG.debug(
                f"polling for batch completion ({i * request_interval} sec) ({n_succeeded}/{len(completions)})..."
            )

        out: List[str] = [completions[h] for h in hashes]  # type: ignore
        return out

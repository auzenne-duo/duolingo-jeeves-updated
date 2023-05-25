"""
DAL for accessing GPT-4 using the duolingo-tutors api.
"""

import os
import time
import warnings
from typing import Any, Dict, Iterable, List, Optional

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
_BATCH_COMPLETION_REQUEST_ROUTE = "/2017-06-30/tutors/ai/completion_request_offline_batch"
_BATCH_COMPLETION_END_ROUTE = (
    "/2017-06-30/tutors/ai/completion_request_offline?requestHash={request_hash}"
)
_BATCH_COMPLETION_POLL_MIN_MILLIS = 1000.0
_BATCH_COMPLETION_POLL_MAX_MILLIS = 10000.0

# Maximum number of prompts to send in a single request to initiate a
# completions batch request
_MAX_COMPLETION_BATCH_INITIATE_SIZE = 10

# Maximum number of prompts to send at once across initiated batches
# to the asynchronous route.  At any given moment, we will be waiting for
# at most this many completions to finish asyncronously.  This rate limit
# can be removed after better rate limiting has been added in the backend
_MAX_COMPLETION_BATCH_SERIAL_RATE_LIMIT_SIZE = 20


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
                json=TutorsDAL._make_completion_request_data(system_prompt, text),
            )
            response.raise_for_status()
            return response.text
        except requests.exceptions.RequestException as e:
            print_request_exception(e, rollbar_level="warning")
            return None

    def request_openai_completion_batch(
        self, system_prompt: str, prompts: Iterable[str], timeout_seconds: float = 900.0
    ) -> List[str]:
        """
        This currently send batches of a hundred from prompts serially.  This limitation can be
        removed once we have rate limiting in the backend.
        Parameters:
            system_prompt: System prompt to use for all prompts in the batch
            prompts: Raw text prompts for which to request completions
            timeout_seconds: Maximum number of seconds to wait for batch completions to
                finish before giving up and timing out
        Returns:
            Batch of completions sampled from OpenAI for the given prompt text
        Raises:
            TimeoutError if timeout reached before all completions finish
            Exceptions for HTTP errors when making requests
        """
        completions = []
        for prompt_batch_index in range(
            0, len(prompts), _MAX_COMPLETION_BATCH_SERIAL_RATE_LIMIT_SIZE
        ):
            request_hashes = self._start_request_openai_completion_batch(
                system_prompt,
                prompts[
                    prompt_batch_index : prompt_batch_index
                    + _MAX_COMPLETION_BATCH_SERIAL_RATE_LIMIT_SIZE
                ],
            )
            request_hash_completions = self._poll_openai_completion_batch_statuses(
                request_hashes, timeout_seconds
            )
            completions.extend(
                request_hash_completions.get(request_hash) for request_hash in request_hashes
            )
        return completions

    def _start_request_openai_completion_batch(
        self,
        system_prompt: str,
        prompts: Iterable[str],
    ) -> List[str]:
        """
        Initiates asynchronous completion requests for a collection of prompts, and
        returns hashes of the requests.
        Parameters:
            system_prompt: System prompt to use for all prompts in the batch
            prompts: Raw text prompts for which to start a request for a
                batch of completions
        Returns:
            List of requests hashes for requests for the given prompts
        Raises:
            Exceptions for HTTP errors when making requests
        """
        with warnings.catch_warnings():
            max_batch_size = _MAX_COMPLETION_BATCH_INITIATE_SIZE
            batches = [
                prompts[(k * max_batch_size) : ((k + 1) * max_batch_size)]
                for k in range(1 + len(prompts) // max_batch_size)
            ]

        request_hashes = []
        for batch in batches:
            batch_requests_data = {
                "requests": [
                    TutorsDAL._make_completion_request_data(system_prompt, prompt)
                    for prompt in batch
                ]
            }
            batch_response = self.client.post(
                _BATCH_COMPLETION_REQUEST_ROUTE,
                json=batch_requests_data,
                headers={
                    "Content-Type": "application/json",
                },
            )
            batch_response.raise_for_status()

            request_hashes.extend(r["requestHash"] for r in batch_response.json()["responses"])
        return request_hashes

    def _poll_openai_completion_batch_statuses(
        self, request_hashes: Iterable[str], timeout_seconds: float
    ) -> Dict[str, str]:
        """
        Repeatedly checks for completions from a batch request to finish until
        they are all finished or the timeout is reached.
        Parameters:
            request_hashes: Hashes for a batch of completion requests
            timeout_seconds: Maximum number of seconds to wait for batch completions to
                finish before giving up and timing out
        Returns:
            Mapping from given request hashes to finished completions
        Raises:
            TimeoutError if timeout reached before all completions finish
            Other HTTP errors if requests fail with HTTP error codes
        """
        sleep_time_ms = self._get_openai_completion_batch_poll_sleep_time(len(request_hashes))

        results = {}
        incomplete_request_hashes = set(request_hashes)
        start_time = time.time()
        print(incomplete_request_hashes)
        while incomplete_request_hashes:
            if time.time() - start_time > timeout_seconds:
                raise TimeoutError(
                    """
                    Timed out waitin for AI completion backend requests to finish.
                    Note that the service may still finish some requests in the background.
                    """
                )
            newly_completed = set()
            for request_hash in incomplete_request_hashes:
                request_hash_url = _BATCH_COMPLETION_END_ROUTE.format(
                    request_hash=request_hash.zfill(56)
                )
                response = self.client.get(request_hash_url)
                response.raise_for_status()

                maybe_completion = response.json()["completion"]
                if maybe_completion is not None:
                    newly_completed.add(request_hash)
                    results[request_hash] = maybe_completion

            for request_hash in newly_completed:
                incomplete_request_hashes.remove(request_hash)

            time.sleep(sleep_time_ms / 1000.0)
        print("time elapsed", time.time() - start_time)
        return results

    @staticmethod
    def _get_openai_completion_batch_poll_sleep_time(completion_batch_size: int) -> float:
        """
        Parameters:
            completion_batch_size: Number of prompts in the completion batch
                that is being polled
        Returns:
            The time to sleep between between polling requests.  This
                is some number of milliseconds between some fixed minimum and maximum given
                by configuration.  The precise number of milliseconds will be proportional to the
                number of completions that we're waiting for
        """
        max_sleep_time_proportion = min(
            completion_batch_size, _MAX_COMPLETION_BATCH_INITIATE_SIZE
        ) / float(_MAX_COMPLETION_BATCH_INITIATE_SIZE)
        return (
            _BATCH_COMPLETION_POLL_MIN_MILLIS
            + (_BATCH_COMPLETION_POLL_MAX_MILLIS - _BATCH_COMPLETION_POLL_MIN_MILLIS)
            * max_sleep_time_proportion
        )

    @staticmethod
    def _make_completion_request_data(system_prompt: str, prompt: str) -> Dict[str, Any]:
        """
        Parameters:
            system_prompt: System prompt to use for all prompts in the batch
            prompt: Raw text prompt for which to request a single completion
        Returns:
            POST request data to AI completions backend for the given model
                parameters and prompt
        """

        request_data = {
            "max_tokens": 1024,
            "prompt": TutorsDAL.get_prompt(system_prompt, prompt),
            "stop": ["<|im_end|>", "<|diff_marker|>"],
            "temperature": 1,
            "top_p": 0.8,
        }
        return request_data

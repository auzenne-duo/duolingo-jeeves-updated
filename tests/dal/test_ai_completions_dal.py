import time
import unittest
from unittest.mock import MagicMock

from jeeves.dal.ai_completions_dal import BATCH_SIZE, AICompletionsDAL
from jeeves.dal.auth_dal import AuthDAL


class TestAICompletionsDAL(unittest.TestCase):
    def setUp(self):
        self.mock_auth_dal = MagicMock(spec=AuthDAL)
        self.mock_auth_dal.auth_api = MagicMock()
        self.dal = AICompletionsDAL(auth_dal=self.mock_auth_dal, api_client=MagicMock())

    def test_batched_ask(self):
        system_prompt = "You are a helpful assistant"
        user_prompts = ["What is 1+1?", "What is 2+2?", "What is 3+3?"]
        expected_responses = ["2", "4", "6"]

        self.dal.client.put.return_value.json.return_value = {
            "responses": [{"requestHash": f"hash_{i}"} for i in range(len(user_prompts))]
        }
        self.dal.client.put.return_value.raise_for_status = MagicMock()

        def mock_status_response(*args, **kwargs):
            if args[0] == "/1/ai-completions/chat-completions-batch":
                return self.dal.client.put.return_value

            if not hasattr(mock_status_response, "call_count"):
                mock_status_response.call_count = 0
            mock_status_response.call_count += 1

            response = MagicMock()
            response.raise_for_status = MagicMock()

            requested_hashes = kwargs["json"]["requestHashes"]
            statuses = []
            for hash_val in requested_hashes:
                hash_num = int(hash_val.split("_")[1])
                if mock_status_response.call_count > hash_num:
                    statuses.append(
                        {
                            "requestHash": hash_val,
                            "status": {"status": "SUCCESS"},
                            "message": {"content": expected_responses[hash_num]},
                        }
                    )
                else:
                    statuses.append(
                        {"requestHash": hash_val, "status": {"status": "PENDING"}, "message": None}
                    )

            response.json.return_value = {"statuses": statuses}
            return response

        self.dal.client.post.side_effect = mock_status_response

        start_time = time.time()
        responses = self.dal.batched_ask(
            system_prompt=system_prompt,
            user_prompts=user_prompts,
            timeout_seconds=1.0,
            request_interval=0.02,
        )
        end_time = time.time()

        self.assertEqual(responses, expected_responses)

        status_calls = self.dal.client.post.call_args_list
        self.assertEqual(len(status_calls), 3)

        self.assertEqual(
            status_calls[0][1]["json"]["requestHashes"], ["hash_0", "hash_1", "hash_2"]
        )

        self.assertEqual(status_calls[1][1]["json"]["requestHashes"], ["hash_1", "hash_2"])

        self.assertEqual(status_calls[2][1]["json"]["requestHashes"], ["hash_2"])

        self.assertLess(end_time - start_time, 2.0)

    def test_batched_ask_timeout(self):
        system_prompt = "You are a helpful assistant"
        user_prompts = ["What is 1+1?"]

        self.dal.client.put.return_value.json.return_value = {
            "responses": [{"requestHash": "hash_0"}]
        }
        self.dal.client.put.return_value.raise_for_status = MagicMock()

        def mock_status_response(*args, **kwargs):
            response = MagicMock()
            response.raise_for_status = MagicMock()
            requested_hashes = kwargs["json"]["requestHashes"]
            response.json.return_value = {
                "statuses": [
                    {"requestHash": hash_val, "status": {"status": "PENDING"}, "message": None}
                    for hash_val in requested_hashes
                ]
            }
            return response

        self.dal.client.post.side_effect = mock_status_response

        with self.assertRaises(TimeoutError):
            self.dal.batched_ask(
                system_prompt=system_prompt,
                user_prompts=user_prompts,
                timeout_seconds=0.05,
                request_interval=0.02,
            )

    def test_batched_ask_large_batch(self):
        system_prompt = "You are a helpful assistant"
        num_requests = BATCH_SIZE + 100
        user_prompts = [f"What is {i}+{i}?" for i in range(num_requests)]
        expected_responses = [str(2 * i) for i in range(num_requests)]

        batch_requests = []

        def mock_batch_request(*args, **kwargs):
            if args[0] == "/1/ai-completions/chat-completions-batch":
                response = MagicMock()
                response.raise_for_status = MagicMock()
                response.json.return_value = {
                    "responses": [
                        {"requestHash": f"hash_{i + len(batch_requests) * BATCH_SIZE}"}
                        for i in range(len(kwargs["json"]["requests"]))
                    ]
                }
                batch_requests.append(kwargs["json"]["requests"])
                return response
            return None

        self.dal.client.put.side_effect = mock_batch_request

        def mock_status_response(*args, **kwargs):
            if args[0] == "/1/ai-completions/chat-completions-batch":
                return mock_batch_request(*args, **kwargs)

            response = MagicMock()
            response.raise_for_status = MagicMock()
            requested_hashes = kwargs["json"]["requestHashes"]

            statuses = []
            for hash_val in requested_hashes:
                hash_num = int(hash_val.split("_")[1])
                statuses.append(
                    {
                        "requestHash": hash_val,
                        "status": {"status": "SUCCESS"},
                        "message": {"content": str(2 * hash_num)},
                    }
                )

            response.json.return_value = {"statuses": statuses}
            return response

        self.dal.client.post.side_effect = mock_status_response

        responses = self.dal.batched_ask(
            system_prompt=system_prompt,
            user_prompts=user_prompts,
            timeout_seconds=0.2,
            request_interval=0.02,
        )

        self.assertEqual(responses, expected_responses)

        self.assertEqual(len(batch_requests), 2)
        self.assertEqual(len(batch_requests[0]), BATCH_SIZE)
        self.assertEqual(len(batch_requests[1]), 100)

        for i, request in enumerate(batch_requests[0]):
            self.assertEqual(request["messages"][1]["content"], f"What is {i}+{i}?")
        for i, request in enumerate(batch_requests[1]):
            self.assertEqual(
                request["messages"][1]["content"], f"What is {i + BATCH_SIZE}+{i + BATCH_SIZE}?"
            )

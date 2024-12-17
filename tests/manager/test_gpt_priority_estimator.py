import unittest
from unittest.mock import MagicMock

from jeeves.manager.gpt_priority_estimator import GPTPriorityEstimator, GPTPriorityResponse
from jeeves.model.jira_priorities import JiraPriority
from jeeves.model.jira_ticket_text import JiraTicketText


class TestGPTPriorityResponse(unittest.TestCase):
    def test_from_json_valid(self) -> None:
        json_str = '{"priority": "High", "reason": "Blocker bug needs fixing"}'
        response = GPTPriorityResponse.from_json(json_str)
        self.assertEqual(response.priority, JiraPriority.HIGH)
        self.assertEqual(response.reason, "Blocker bug needs fixing")

    def test_from_json_invalid_priority(self) -> None:
        json_str = '{"priority": "Unknown", "reason": "Invalid priority"}'
        response = GPTPriorityResponse.from_json(json_str)
        self.assertEqual(response.priority, JiraPriority.UNPRIORITIZED)
        self.assertEqual(response.reason, "Invalid priority")

    def test_from_json_missing_fields(self) -> None:
        json_str = "{}"
        response = GPTPriorityResponse.from_json(json_str)
        self.assertEqual(response.priority, JiraPriority.UNPRIORITIZED)
        self.assertEqual(response.reason, "")


class TestGPTPriorityEstimator(unittest.TestCase):
    def setUp(self) -> None:
        self.mock_ai_completions_dal = MagicMock()
        self.estimator = GPTPriorityEstimator(ai_completions_dal=self.mock_ai_completions_dal)

    def test_estimate_priority_valid_ticket(self) -> None:
        ticket = JiraTicketText(title="Bug report", description="App crashes on startup")
        self.mock_ai_completions_dal.ask.return_value = (
            '{"priority": "Highest", "reason": "Crashing on startup"}'
        )

        response = self.estimator.estimate_priority(ticket)

        self.assertEqual(response.priority, JiraPriority.HIGHEST)
        self.assertEqual(response.reason, "Crashing on startup")

    def test_estimate_priority_handles_ai_response_error(self) -> None:
        ticket = JiraTicketText(title="Bug report", description="App crashes on startup")
        self.mock_ai_completions_dal.ask.return_value = (
            '{"priority": "Invalid", "reason": "Unexpected format"}'
        )

        response = self.estimator.estimate_priority(ticket)

        self.assertEqual(response.priority, JiraPriority.UNPRIORITIZED)
        self.assertEqual(response.reason, "Unexpected format")

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from duolingo_base.util import registry

from jeeves.dal.ai_completions_dal import AICompletionsDAL
from jeeves.model.jira_priorities import JiraPriority
from jeeves.model.jira_ticket_text import (
    REQ_DESCRIPTION,
    REQ_TITLE,
    JiraTicketText,
)

# The expected field names of the JSON response object
RESP_PRIORITY = "priority"
RESP_REASON = "reason"

# TODO (david.sawicki): Add specific examples to the system prompt and ask Core Bug Triage Task Force to review.
SYSTEM_PROMPT = f"""
You are part of a quality analytics pipeline at Duolingo that helps employees to automatically triage Jira tickets.
When employees "shake" their device to report a bug, feature request, design issue, or some other feedback, they
fill out a form providing a "{REQ_TITLE}" (a brief summary) and "{REQ_DESCRIPTION}", which are converted into a Jira
ticket. Your job is to assign a priority to the ticket based on the textual content of the report and explain your
reasoning in 10 words or fewer. Sometimes, tickets will have only "{REQ_TITLE}" and no "{REQ_DESCRIPTION}", and that's
acceptable. You can just give your best judgment based on the information provided.

Respond with a JSON object containing only:
- "{RESP_PRIORITY}": The priority of the ticket. The priority can only be one of the following:
  {{"Highest", "High", "Medium", "Low", "Lowest", "Unprioritized"}}. Use the following rubric to assign priorities:
  - High/Highest: Feature rollout blocked until the bug is fixed. For example: Learner blocking experiences, crashing,
    really gnarly visual bug, bad experiences
  - Medium: Should be resolved before rollout, but can be resolved in further iterations if shipping a feature MVP.
    This could also block a feature if need be.
  - Low/Lowest: The feature can be shipped with low/lowest bugs, but a plan should be in place to address via further
    iterations or a grease week. For example: Small visual bugs
  - Unprioritized: Not enough context to determine the priority. For example: if the description refers to an image
    or a video but provides no context about the issue, or vague descriptions like "Fix this" or "Is this a bug?"
- "{RESP_REASON}": A brief justification for the priority assigned in "{RESP_PRIORITY}" in 10 words or fewer.
"""


@dataclass
class GPTPriorityResponse:
    """
    The response from GPT containing the priority and reason for a Jira ticket.
    """

    priority: JiraPriority
    reason: str

    @classmethod
    def from_json(cls, json_str: str) -> GPTPriorityResponse:
        # Sanitize all control characters from JSON string before parsing
        json_str = re.sub(r"[\x00-\x1F\x7F-\x9F]", " ", json_str)
        data = json.loads(json_str)

        priority_resp = (
            JiraPriority.get_enum_from_string(data[RESP_PRIORITY])
            if data.get(RESP_PRIORITY)
            else JiraPriority.UNPRIORITIZED
        )

        return cls(
            priority=priority_resp if priority_resp else JiraPriority.UNPRIORITIZED,
            reason=data[RESP_REASON] if data.get(RESP_REASON) else "",
        )


@registry.bind(
    ai_completions_dal=registry.reference(AICompletionsDAL),
)
class GPTPriorityEstimator:
    def __init__(self, ai_completions_dal: AICompletionsDAL) -> None:
        self.ai_completions_dal = ai_completions_dal

    def estimate_priority(self, ticket: JiraTicketText) -> GPTPriorityResponse:
        """
        Given a title and description of an admin user's Shake-to-Report Jira ticket,
        ask GPT to estimate the priority of the ticket.

        Parameters:
            ticket: A `JiraTicketText` object representing a Jira ticket written by a Duo.

        Returns a `GPTPriorityResponse` instance containing GPT's assessment of the priority for this ticket
            as well as the reason it chose this priority.
        """
        if not ticket:
            raise ValueError("Cannot generate a priority for an undefined ticket.")

        # Ask ai-completions-backend to give a priority.
        response_text = self.ai_completions_dal.ask(
            system_prompt=SYSTEM_PROMPT,
            use_json_mode=True,
            user_prompt=ticket.to_yaml(),
        )
        return GPTPriorityResponse.from_json(response_text)

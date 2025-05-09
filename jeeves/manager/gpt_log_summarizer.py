from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass
from typing import Dict, List, Optional

from duolingo_base.util import registry

from jeeves.dal.ai_completions_dal import AICompletionsDAL

LOG = logging.getLogger(__name__)

RESP_LOG_SUMMARY = "log_summary"

# Components of the request format (in YAML)
REQ_DESCRIPTION = "DESCRIPTION"
REQ_ID = "ID"  # The Jira ticket ID
REQ_TITLE = "TITLE"
REQ_LOGS = "LOGS"  # List of log contents

SYSTEM_PROMPT = """You are an expert log analyzer that finds patterns in logs that are STRICTLY relevant to what appears after either:
1. "Ticket Title:" field
2. "Description:" field

Instructions:
1. First, identify the key issue from ONLY what appears after "Ticket Title:" or the first line after "Description:"
2. Then, find ONLY log entries that directly prove or relate to that specific issue
3. If the title or description indicates this ticket was created for testing, return an empty array
4. If the title or description indicates this is a feature request, return an empty array
5. If no logs directly relate to the title or first line, return an empty array

Respond with a JSON object as an array of strings:
- "{RESP_LOG_SUMMARY}": Grouping of log entries that are relevant to the ticket title or description
"""


@dataclass
class JiraLogSummarizationTicket:
    """
    A simplified container for the textual content of a Jira ticket (title and description).
    This makes it much easier to test and serialize and deserialize!
    """

    description: str
    title: str
    logs: List[str]
    ticket_id: Optional[str] = None

    def __init__(
        self,
        description: str,
        title: str,
        files: Dict[str, List[str]],
        ticket_id: Optional[str] = None,
    ) -> None:
        self.description = description
        self.title = title
        self.ticket_id = ticket_id
        self.logs = []

        for file_title, file_contents in files.items():
            if "log" not in file_title.lower():
                continue  # Only use log files
            if file_contents:
                self.logs.append(file_contents)

    def to_yaml(self) -> str:
        yaml_parts = [
            f"{REQ_TITLE}: {self.title}",
            f"{REQ_DESCRIPTION}: {self.description}",
            f"{REQ_LOGS}: {json.dumps(self.logs)}",  # Use JSON for the list format
        ]
        return "\n".join(yaml_parts)


@dataclass
class LogSummaryResponse:
    """
    The response from GPT containing the log analysis results.
    """

    log_summary: List[str]

    @classmethod
    def from_text(cls, text: str, ticket_id: Optional[str] = None) -> LogSummaryResponse:
        try:
            json_str = re.sub(r"[\x00-\x1F\x7F-\x9F]", " ", text)
            data = json.loads(json_str)
            return cls(log_summary=data[RESP_LOG_SUMMARY] if data.get(RESP_LOG_SUMMARY) else [])
        except Exception:
            LOG.error(f"{ticket_id}: Error parsing log summary response: {text}")
            return cls(log_summary=[])


@registry.bind(
    ai_completions_dal=registry.reference(AICompletionsDAL),
)
class GPTLogSummarizer:
    def __init__(self, ai_completions_dal: AICompletionsDAL) -> None:
        self.ai_completions_dal = ai_completions_dal

    def summarize_logs(self, ticket_data: JiraLogSummarizationTicket) -> LogSummaryResponse:
        """
        Analyzes logs using GPT to find patterns relevant to the ticket title and description.

        Parameters:
            ticket_data: A LogSummarizationTicket containing ticket metadata including title and description

        Returns:
            A LogSummaryResponse containing the analysis results
        """
        user_prompt = f"""
        Ticket Title: {ticket_data.title}
        Description: {ticket_data.description}
        Logs: {ticket_data.logs}
        """

        try:
            response = self.ai_completions_dal.ask(
                system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt, use_json_mode=True
            )
            return LogSummaryResponse.from_text(response, ticket_data.ticket_id)
        except Exception:
            LOG.error(f"{ticket_data.ticket_id}: Error analyzing logs")
            return LogSummaryResponse.from_text([], ticket_data.ticket_id)

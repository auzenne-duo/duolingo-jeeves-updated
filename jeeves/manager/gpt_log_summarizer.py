from __future__ import annotations

import json
import logging
import re
import time
from collections import Counter
from dataclasses import dataclass
from typing import Dict, List, Optional

from duolingo_base.dal.s3 import S3DownloadException
from duolingo_base.util import registry

from jeeves.dal.ai_completions_dal import AICompletionsDAL
from jeeves.util.s3_client_and_bucket import get_s3_client_and_bucket

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.DEBUG)

FEEDBACK_BASE_URL = "https://jeeves.duolingo.com/en/feedback"
FEEDBACK_FEATURE = "AI_LOG_SUMMARY"

# These are titles that are known to be irrelevant to log summarization
SKIP_TITLES = {"test", "tests", "testing"}

# These are lines that are known to be spammy and not relevant to log summarization
SKIP_LINES = ["frameperformance", "keychain"]

RESP_LOG_SUMMARY = "log_summary"

# Components of the request format (in YAML)
REQ_DESCRIPTION = "DESCRIPTION"
REQ_ID = "ID"  # The Jira ticket ID
REQ_TITLE = "TITLE"
REQ_LOGS = "LOGS"  # List of log contents

SYSTEM_PROMPT = f"""You are an expert log analyzer that finds patterns in logs that are STRICTLY relevant to what appears in the:
1. "Ticket Title:" field
2. "Description:" field

The user prompt will be formatted as:
Ticket Title: <title string>
Description: <description string>
Logs: <list of log lines>

Instructions:
1. First, identify the key issue from ONLY what appears after "Ticket Title:" or the first line after "Description:"
2. Then, find ONLY log entries that directly prove or relate to that specific issue
3. If no logs directly relate to the title or first line, return an empty array
4. Respond with a JSON object containing only one string field:
   "{RESP_LOG_SUMMARY}": The list of log lines that directly prove or relate to the key issue

IMPORTANT: Respond ONLY with a valid JSON object, and do NOT include any Markdown or code block formatting.

Examples:
Title: "Crashing"
Description: "App crashes when I try to sign in"
Logs: ['Running on port 8080', 'App failed to start', 'Network request failed']

Response: {{{RESP_LOG_SUMMARY}: ["App failed to start", "Network request failed"]}}

Title: "Slow"
Description: "App is slow when I try to sign in"
Logs: ['App running on port 8080', 'Failed to connect to server', 'Network request failed']

Response: {{{RESP_LOG_SUMMARY}: ["Failed to connect to server", "Network request failed"]}}

Title: "lily not responding / device not capturing inputs"
Description: "Lily is not responding to inputs from the device"
Logs: ['[ERROR | ASAP] Keychain delete error: -34018 A required entitlement isn\'t present.', '2025/02/06 20:29:18:595  [ERROR | EXAI] [VCST] Task finished with error: Error Domain=kAFAssistantErrorDomain Code=1110 "No speech detected" UserInfo={{NSLocalizedDescription=No speech detected}}']

Response: {{{RESP_LOG_SUMMARY}: ["Task finished with error: Error Domain=kAFAssistantErrorDomain Code=1110 \"No speech detected\" UserInfo={{NSLocalizedDescription=No speech detected}}"]}}
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
                self.logs.extend(file_contents)

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
    def from_text(cls, text: str) -> LogSummaryResponse:
        # Sanitize all control characters from JSON string before parsing
        json_str = re.sub(r"[\x00-\x1F\x7F-\x9F]", " ", text)
        data = json.loads(json_str)

        return cls(log_summary=data[RESP_LOG_SUMMARY])

    def format(self, max_lines: int = 5) -> str:
        """
        Returns a formatted string of the logs, collapsing duplicate lines and appending a repeat count.
        Only up to max_lines unique lines are shown; if more, a summary line is appended.
        """
        counts = Counter(self.log_summary)
        unique_lines = list(counts.keys())
        output_lines = []
        for line in unique_lines[:max_lines]:
            count = counts[line]
            if count > 1:
                output_lines.append(f"{line} (x{count})")
            else:
                output_lines.append(line)
        omitted = len(unique_lines) - max_lines
        if omitted > 0:
            output_lines.append(f"...and {omitted} more unique lines omitted.")
        return "\n".join(output_lines)


@registry.bind(
    ai_completions_dal=registry.reference(AICompletionsDAL),
)
class GPTLogSummarizer:
    def __init__(self, ai_completions_dal: AICompletionsDAL) -> None:
        self.ai_completions_dal = ai_completions_dal
        self.s3_client, self.s3_bucket = get_s3_client_and_bucket()

    def should_skip_ticket(self, ticket_data: JiraLogSummarizationTicket) -> bool:
        normalized_title = (ticket_data.title or "").replace(" ", "").lower()
        if normalized_title in SKIP_TITLES:
            return True
        if not (ticket_data.title and ticket_data.title.strip()) and not (
            ticket_data.description and ticket_data.description.strip()
        ):
            return True
        return False

    def _filter_logs_error_warn(self, logs: list[str]) -> list[str]:
        return [
            line
            for line in logs
            if ("error" in line.lower() or "warn" in line.lower())
            and not any(skip_line in line.lower() for skip_line in SKIP_LINES)
        ]

    def summarize_logs(self, ticket_data: JiraLogSummarizationTicket) -> LogSummaryResponse:
        """
        Analyzes logs using GPT to find patterns relevant to the ticket title and description.

        Parameters:
            ticket_data: A LogSummarizationTicket containing ticket metadata including title and description

        Returns:
            A LogSummaryResponse containing the analysis results
        """
        if self.should_skip_ticket(ticket_data):
            LOG.info(
                f"{ticket_data.ticket_id}: Returning empty LogSummaryResponse due to should_skip_ticket"
            )
            return LogSummaryResponse(log_summary=[])

        filtered_logs = self._filter_logs_error_warn(ticket_data.logs)
        if not filtered_logs:
            LOG.info(
                f"{ticket_data.ticket_id}: Returning empty LogSummaryResponse because filtered_logs is empty"
            )
            return LogSummaryResponse(log_summary=[])

        user_prompt = f"""
        Ticket Title: {ticket_data.title}
        Description: {ticket_data.description}
        Logs: {filtered_logs}
        """

        try:
            response = self.ai_completions_dal.ask(
                system_prompt=SYSTEM_PROMPT, user_prompt=user_prompt, use_json_mode=True
            )
            LOG.debug(
                f"{ticket_data.ticket_id}: LogSummaryResponse AI completions response: {response}"
            )
            log_summary_response = LogSummaryResponse.from_text(response)
            formatted_lines = log_summary_response.format(max_lines=1).splitlines()
            first_formatted_log = formatted_lines[0] if formatted_lines else "<no logs>"
            LOG.debug(
                f"{ticket_data.ticket_id}: Returning LogSummaryResponse from AI completions response. First formatted log: {first_formatted_log}"
            )
            return log_summary_response
        except Exception as e:
            LOG.error(f"{ticket_data.ticket_id}: Error analyzing logs: {e}")
            return LogSummaryResponse(log_summary=[])

    def _get_log_summary_s3(self, jira_key: str) -> Optional[str]:
        try:
            data = self.s3_client.download(self.s3_bucket, f"log_summaries/{jira_key}.txt")
            return data.decode("utf-8")
        except S3DownloadException:
            return None

    def _poll_for_log_summary_s3(self, jira_key: str, timeout: int = 60) -> Optional[str]:
        end_time = time.time() + timeout
        while time.time() < end_time:
            if summary := self._get_log_summary_s3(jira_key):
                return summary
            time.sleep(1)
        return None

    def generate_log_summary_rich_text(self, issue_key: str) -> List[Dict]:
        """
        Generate rich text for log summary.

        Args:
            issue_key: The Jira issue key

        Returns:
            List of dictionaries in jira rich text format (to be inserted in
            issue["fields"]["description"]["content"])
        """
        if not issue_key:
            return []

        summary = self._poll_for_log_summary_s3(issue_key, timeout=60)

        if not summary:
            return []

        yes_feedback_url = (
            f"{FEEDBACK_BASE_URL}?feature={FEEDBACK_FEATURE}&id={issue_key}&quick_feedback=POSITIVE"
        )
        no_feedback_url = (
            f"{FEEDBACK_BASE_URL}?feature={FEEDBACK_FEATURE}&id={issue_key}&quick_feedback=NEGATIVE"
        )

        return [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": "Relevant Logs",
                        "marks": [{"type": "strong"}],
                    }
                ],
            },
            {
                "type": "expand",
                "attrs": {"title": "Expand to view"},
                "content": [
                    {"type": "paragraph", "content": [{"type": "text", "text": summary}]},
                    {
                        "type": "paragraph",
                        "content": [
                            {"type": "text", "text": "Helpful? (", "marks": [{"type": "em"}]},
                            {
                                "type": "text",
                                "text": "Yes",
                                "marks": [
                                    {"type": "em"},
                                    {"type": "link", "attrs": {"href": yes_feedback_url}},
                                ],
                            },
                            {"type": "text", "text": " / ", "marks": [{"type": "em"}]},
                            {
                                "type": "text",
                                "text": "No",
                                "marks": [
                                    {"type": "em"},
                                    {"type": "link", "attrs": {"href": no_feedback_url}},
                                ],
                            },
                            {"type": "text", "text": ")", "marks": [{"type": "em"}]},
                        ],
                    },
                ],
            },
        ]

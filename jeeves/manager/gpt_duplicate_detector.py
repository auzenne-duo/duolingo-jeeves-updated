from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import pytz
from duolingo_base.dal.s3 import S3Client
from duolingo_base.util import registry

from jeeves.dal.ai_completions_dal import AICompletionsDAL
from jeeves.dal.jira_dal import JiraDAL
from jeeves.manager.gpt_screenshot_summarizer import GPTScreenshotSummarizer
from jeeves.manager.jira_manager import JiraManager
from jeeves.model.jira_document import JiraDocument
from jeeves.util.s3_client_and_bucket import get_s3_client_and_bucket

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)

DEDUP_SYSTEM_PROMPT = """
You are a helpful assistant trying to determine if two bug reports are duplicates, i.e. are likely describing the same problem with the application. After a short justification, produce a single line of output saying either "duplicate: true" or "duplicate: false".

Example:

# User
Please determine if the following two bug reports are duplicates:
**Ticket DLAA-34292**
**Summary:** unable to finish lesson
**Description:** can't click submit
**end of ticket**

**Ticket DLAA-34254**
**Summary:** cant finish my lesson
**Description:** (blank)
**Screenshot Description:** A screenshot of a duolingo lesson with a language learning exercise. The "Submit" button appears greyed out.
**end of ticket**

# Assistant
These two tickets both describe a user who is unable to complete a lesson, and in the descriptions of both, we see a user presented with a greyed out "submit" button, so they are most likely duplicates.
duplicate: true

Note: being on the same screen (or same activity/view controller) is *not* sufficient evidence that two bugs are duplicates. Two tickets may be describing visual layout bugs on the same screen, but if the exact layout discrepancy is not similar, do not report the bugs as duplicates. For example, even if both tickets are on a lesson screen, if one ticket is referencing inability to complete the lesson while another is about blank buttons for selecting an answer, the two tickets are likely not duplicates. Just because the issues are about the same aspect of user experience, does NOT mean they are duplicates.

Some further examples:
Visual issues with the same UI element incorrect in the same or very similar way (e.g. both tickets discuss the same button appearing in the wrong place) => duplicates
Visual layout issues with different elements => unlikely to be duplicates
Visual layout issues on different platforms (ios/DLAI and android/DLAA) => not duplicates
Visual issues with the same UI element with different symptoms, i.e. incorrect in different ways => not duplicates
Issues about the same screen but with different symptoms (e.g. layout problems referencing different UI elements) => not duplicates
Issues about the same product feature or class of features (e.g. Streak, Friends Quest), but with different symptoms or manifesting in different parts of the app => not duplicates
Issues with the same product feature that manifest in the same or very similar way (e.g. unable to complete a lesson because the final exercise never loaded) => duplicates
Similar symptoms on two different screens => very unlikely, but possibly duplicates, only if the symptom is very specific. A blank screen, for example, is quite a common symptom so is not evidence for duplicates.
Layout bugs on two different screens => almost never duplicates as layout is controlled independently for each screen
""".strip()

DEDUP_USER_PROMPT = """
Please determine if the following two bug reports are duplicates:
{}
{}
""".strip()

DEDUP_TICKET_TEMPLATE = """
**Ticket {key}**
**Summary:** {summary}
**Description:** {description}
**Screenshot Description:** {screenshot_description}
**end of ticket**
""".strip()

RECENT_ISSUES_THRESHOLD = timedelta(days=4)


@registry.bind(
    ai_completions_dal=registry.reference(AICompletionsDAL),
    jira_manager=registry.reference(JiraManager),
    gpt_screenshot_summarizer=registry.reference(GPTScreenshotSummarizer),
)
class GPTDuplicateDetector:
    def __init__(
        self,
        ai_completions_dal: AICompletionsDAL,
        jira_manager: JiraManager,
        gpt_screenshot_summarizer: GPTScreenshotSummarizer,
        s3_client: Optional[S3Client] = None,
        s3_bucket: Optional[str] = None,
    ):
        self.ai_completions_dal = ai_completions_dal
        self.jira_manager = jira_manager
        self.gpt_screenshot_summarizer = gpt_screenshot_summarizer
        default_client, default_bucket = get_s3_client_and_bucket()
        self.s3_client = s3_client or default_client
        self.s3_bucket = s3_bucket or default_bucket

    def get_jira_issue_text(self, data: dict) -> str:
        desc = data["fields"]["description"]
        if desc:
            desc = JiraDocument.compress_rich_text(desc)
        screenshot_description = (
            self.gpt_screenshot_summarizer.get_description_s3(
                data["key"],
            )
            or "(no screenshot description available)"
        )
        return DEDUP_TICKET_TEMPLATE.strip().format(
            key=data["key"],
            summary=data["fields"]["summary"],
            description=desc or "(no description)",
            screenshot_description=screenshot_description,
        )

    @staticmethod
    def determine_duplicate_from_chat_response(chat_response: str):
        if not chat_response:
            return False, "No response from AIC backend"
        lines = chat_response.splitlines()
        dup = "true" in lines[-1]
        return dup, "\n".join(lines[:-1]).strip()

    def _add_label_to_issue(self, issue_key: str, label: str) -> None:
        """Helper to add a JIRA label to an issue, best-effort."""
        try:
            JiraDAL.update_issue(issue_key, labels_to_add=[label])
        except Exception as e:
            LOG.error("%s: Failed to add label %s – %s", issue_key, label, e)

    def find_duplicates(
        self,
        issue: Dict,
    ) -> Tuple[List[Tuple[str, str]], List[Tuple[str, str]]]:
        """
        Given a JIRA issue (JSON dictionary as returned by the JIRA API),
        returns a tuple of (duplicates, non_duplicates) where each is a list of
        (key, reasoning) pairs.

        Duplicate candidates are all tickets from the last
        `RECENT_ISSUES_THRESHOLD`. AI Completions backend is used to determine
        if each of these candidates is likely a duplicate of the new ticket.
        Expects screenshot descriptions to be available in S3 (but will not
        fail if one is not found).
        """
        issue_key = issue["key"]

        # Wait for screenshot description to be available for 60 seconds. If
        # it's not available by then, continue without a screenshot description
        screenshot_description = self.gpt_screenshot_summarizer.poll_for_description_s3(
            issue_key, timeout=60
        )
        if screenshot_description:
            LOG.info(f"{issue_key}: Found screenshot description; starting deduplication")
        else:
            LOG.warning(
                f"{issue_key}: Could not find screenshot description; performing deduplication without it"
            )

        text1 = self.get_jira_issue_text(issue)

        updated_since = datetime.now(tz=pytz.utc) - RECENT_ISSUES_THRESHOLD
        other_issues = self.jira_manager.get_str_tickets_since(updated_since)

        LOG.info(
            f"{issue_key}: Analyzing {len(other_issues)} other issues for potential duplicates"
        )
        dedup_user_messages = []
        issues_to_test = []
        for other in other_issues:
            if other["key"] == issue_key:
                continue
            try:
                text2 = self.get_jira_issue_text(other)
            except (KeyError, ValueError) as e:
                LOG.warning(
                    f"{issue_key}: Skipping issue {other['key']} because it does not have expected structure: {e}"
                )
                continue
            message = DEDUP_USER_PROMPT.format(text1, text2)
            dedup_user_messages.append(message)
            issues_to_test.append(other)

        completions = self.ai_completions_dal.batched_ask(DEDUP_SYSTEM_PROMPT, dedup_user_messages)

        potential_duplicates = []
        non_duplicates = []
        for completion, other in zip(completions, issues_to_test):
            other_key: str = other["key"]
            LOG.debug(f"{issue_key}: Comparing with {other_key}: {completion}")
            is_duplicate, justification = self.determine_duplicate_from_chat_response(completion)
            if is_duplicate:
                potential_duplicates.append((other_key, justification))
            else:
                non_duplicates.append((other_key, justification))

        # Add a label if we detected duplicates
        if potential_duplicates:
            self._add_label_to_issue(issue_key, "duplicate_detected")

        return potential_duplicates, non_duplicates

    @staticmethod
    def generate_duplicates_rich_text(
        issue_key: str, duplicates: List[Tuple[str, str]]
    ) -> List[Dict]:
        """
        Generate rich text for flagging potential duplicate issues.

        Args:
            duplicates: List of tuples containing (issue_key, justification) pairs

        Returns:
            List of dictionaries in jira rich text format (to be inserted in
            issue["fields"]["description"]["content"])
        """
        if not duplicates:
            return []

        connect_duplicates_url = (
            "https://jeeves.duolingo.com/mark-duplicates?jira_issues="
            + f"{issue_key},"
            + ",".join(k for k, _ in duplicates)
        )

        rich_text = [
            {
                "type": "paragraph",
                "content": [
                    {
                        "type": "text",
                        "text": "Potential duplicates (",
                        "marks": [{"type": "strong"}],
                    },
                    {
                        "type": "text",
                        "text": "Choose duplicates and create parent ticket...",
                        "marks": [
                            {"type": "link", "attrs": {"href": connect_duplicates_url}},
                            {"type": "strong"},
                        ],
                    },
                    {"type": "text", "text": ")", "marks": [{"type": "strong"}]},
                ],
            },
        ]

        # Add all issue links first
        for issue_key, _ in duplicates:
            issue_url = f"https://duolingo.atlassian.net/browse/{issue_key}"
            rich_text.append(
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "inlineCard", "attrs": {"url": issue_url}},
                    ],
                }
            )

        # Add all justifications in a single expandable section
        justification_paragraphs = []
        for issue_key, justification in duplicates:
            justification_paragraphs.append(
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": f"{issue_key}", "marks": [{"type": "strong"}]},
                        {"type": "text", "text": f": {justification}"},
                    ],
                }
            )

        rich_text.append(
            {
                "type": "expand",
                "content": justification_paragraphs,
                "attrs": {"title": "Reasoning for duplicate detection"},
            }
        )

        return rich_text

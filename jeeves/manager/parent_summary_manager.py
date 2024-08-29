from __future__ import annotations

from duolingo_base.util import registry

from jeeves.dal.ai_completions_dal import AICompletionsDAL
from jeeves.model.jira_ticket_text import (
    REQ_DESCRIPTION,
    REQ_TITLE,
    RESP_DESCRIPTION,
    RESP_TITLE,
    JiraTicketText,
)

RESP_DESCRIPTION_MAX_SENTENCES = 3
RESP_TITLE_LENGTH = 255

# Hoping that this system prompt can double as documentation for this feature!
SYSTEM_PROMPT = f"""
You are part of a quality analytics pipeline at Duolingo that helps employees to automatically group together
Jira tickets that are describing the same issue in order to help the company identify the most widely reported issues.
When employees "shake" their device to report a bug, feature request, design issue, or some other feedback, they
fill out a form providing a "{REQ_TITLE}" (a brief summary) and "{REQ_DESCRIPTION}", which are converted into a Jira
ticket. This feature is called "Shake-to-Report".

Based on the embedding vector of the text of the new ticket, we run a k-NN search to retrieve a list of Jira tickets
that are the most similar to the new one, which are then presented to the person reporting. The reporter can then
select one or more tickets as a duplicate of their issue, which then causes those to be linked to the new one in Jira.

Given a list of Jira issues that were tagged as duplicates of one another, your task is to create a title and
description for a parent Jira ticket representing the root issue that is underlying the duplicate reports. If the
child tickets seem to be reporting multiple root issues, or if there appear to be some tickets that should not be
linked together with the rest, please indicate this in the description and calling out the ID.

Return a JSON response with the following structure:
- {RESP_TITLE}: A concise summary of the issue, which must be less than {RESP_TITLE_LENGTH} characters.
- {RESP_DESCRIPTION}: A concise description of the issue in at most {RESP_DESCRIPTION_MAX_SENTENCES} sentences. Describe
  the scope, the impact, and any other relevant details that would help a developer understand the issue.
"""


@registry.bind(
    ai_completions_dal=registry.reference(AICompletionsDAL),
)
class ParentSummaryManager:
    def __init__(self, ai_completions_dal: AICompletionsDAL):
        self.ai_completions_dal = ai_completions_dal

    def generate_summary_and_description(self, docs: list[JiraTicketText]) -> JiraTicketText:
        """
        Given a list of headers and a list of descriptions, generates a summary
        of the descriptions from the AI Completions service via OpenAI/GPT.

        Parameters:
            docs: A list of `JiraTicketText` objects to summarize.

        Returns:
            A `JiraTicketText` instance containing a title and description for the parent issue.
        """
        if not docs:
            raise ValueError("Cannot generate a summary for an empty list of issues.")

        # Skip summarizing with GPT if there is only one issue.
        if len(docs) == 1:
            return docs[0]

        # Concatenate the text from the child tickets into a single string.
        user_prompt: str = f"\n{'-'*30}\n".join([doc.to_yaml() for doc in docs])
        # Generate a summary using OpenAI GPT.
        response_text = self.ai_completions_dal.ask(
            system_prompt=SYSTEM_PROMPT,
            use_json_mode=True,
            user_prompt=user_prompt,
        )

        if response_text is None:
            # If there is no response, return the first issue as a fallback.
            return docs[0]

        return JiraTicketText.from_json(response_text)

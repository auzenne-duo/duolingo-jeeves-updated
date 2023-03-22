from typing import List, Tuple

from duolingo_base.util import registry

from jeeves.dal.tutors_dal import TutorsDAL

SYSTEM_PROMPT = """
Duolingo's users can report bugs, feedback, and feature requests into Jira. Each Jira issue has a title that summarizes the issue and a description with more detail. When given a list of issues that were reported as duplicates, this bot can generate a single title in less than 255 characters and a longer description that summarizes all the duplicate reports.
"""


@registry.bind(
    tutors_dal=registry.reference(TutorsDAL),
)
class ParentSummaryManager:
    def __init__(self, tutors_dal: TutorsDAL):
        self.tutors_dal = tutors_dal

    def _generate_summary_user_prompt(self, headers: List[str], descriptions: List[str]) -> str:
        """
        Given a list of headers and a list of descriptions, generates a prompt
        for the Tutors service to generate a summary of the descriptions.

        Parameters:
            headers: A list of headers for the descriptions.
            descriptions: A list of descriptions to summarize.

        Returns:
            A string of titles and descriptions that can be passed as a prompt to the Tutors service.
        """
        prompt = ""
        for header, description in zip(headers, descriptions):
            prompt += f"""Title: {header}
Description: {description}

"""
        return prompt

    def generate_summary_and_description(
        self, headers: List[str], descriptions: List[str]
    ) -> Tuple[str, str]:
        """
        Given a list of headers and a list of descriptions, generates a summary
        of the descriptions from the Tutors service via AI.

        Parameters:
            headers: A list of headers for the descriptions.
            descriptions: A list of descriptions to summarize.

        Returns:
            A tuple of the header and the full text of the description.
        """
        if not headers or not descriptions:
            raise ValueError("Cannot generate a summary for an empty list of issues.")

        if len(headers) != len(descriptions):
            raise ValueError("The number of headers and descriptions must be the same.")

        if len(headers) == 1:
            return headers[0], descriptions[0]

        # Generate a summary using GPT-3.

        user_prompt: str = self._generate_summary_user_prompt(headers, descriptions)
        response_text = self.tutors_dal.ask(SYSTEM_PROMPT, user_prompt)
        print("response_text", response_text)
        if response_text is None:
            return headers[0], descriptions[0]
        # The header is everything between "Title: " and the next new line.
        if "Title: " not in response_text:
            summary_header: str = headers[0]
        else:
            summary_header = response_text.split("Title: ")[1].split("\n")[0]

        # The summary description is after "Description"
        if "Description: " not in response_text:
            summary_description: str = descriptions[0]
        else:
            summary_description = response_text.split("Description: ")[1]

        return summary_header, summary_description

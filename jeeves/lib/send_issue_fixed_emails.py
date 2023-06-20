import json
from datetime import datetime
from typing import Set

from duolingo_base.util import registry

from jeeves.dal.ai_completions_dal import AICompletionsDAL
from jeeves.dal.opensearch_interface import OpenSearchDAL
from jeeves.dal.sns import PublishManager
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.shake_to_report_category import ShakeToReportCategory
from jeeves.model.spike_word import SpikeWord
from jeeves.util.date_util import date_to_str, time_series_str_to_datetime as str_to_datetime
from jeeves.util.s3_client_and_bucket import get_s3_client_and_bucket, upload_to_jeeves_s3

_S3_USERS_EMAIL_SENT_TO_PATH = "beta_feedback_emails"

USER_TEXT_SIMILAR_TO_DESCRIPTION = """You will determine if two pieces of text are talking about the same issue.
You will receive a description of an issue and a piece of text that may or may not be talking about that issue.
You will then respond with "true" or "false" to indicate if the text is talking about the issue described.
Example:
Description: "We fixed an issue with users not being able to sign on to the app."
Text: "I can't log in"
True

Description: "We fixed problems with users not being able to start lessons."
Text: "I can't tap on the right answer."
False

Description: "We fixed problems with users not being able to start lessons."
Text: "Why can't I start my lesson?! This has been happening for a week now!"
True
"""


@registry.bind(
    es_dal=registry.reference(OpenSearchDAL),
    ai_completions_dal=registry.reference(AICompletionsDAL),
    publish_manager=registry.reference(PublishManager),
)
class IssueFixedEmailSender:
    def __init__(
        self,
        es_dal: OpenSearchDAL,
        ai_completions_dal: AICompletionsDAL,
        publish_manager: PublishManager,
    ):
        self._es_dal = es_dal
        self._ai_completions_dal = ai_completions_dal
        self._publish_manager = publish_manager

    def send_issue_fixed_emails(self, spike: SpikeWord, description: str) -> int:
        """
        Send emails to the beta testers who reported the issue that was fixed.

        Parameters:
            spike: The spike that was fixed.
            description: A description of the issue that was fixed.

        Returns:
            The number of emails sent to beta users.
        """
        spike_datetime = str_to_datetime(spike.date)
        hits = self._es_dal.get_recent_paginated_tickets(
            "en", spike.word, spike_datetime, spike_datetime, limit=1000, use_lemmas=True
        )

        beta_user_ids = set()
        datetime_now_str = date_to_str(datetime.now())
        sent_user_ids = self.get_user_ids_sent_to(datetime_now_str)
        doc: JeevesDocument
        for doc in hits["data"]:
            if (
                doc.shake_to_report_category == ShakeToReportCategory.EXTERNAL
                and doc.user_id not in beta_user_ids
                and doc.user_id not in sent_user_ids
            ):
                response = self._ai_completions_dal.ask(
                    USER_TEXT_SIMILAR_TO_DESCRIPTION,
                    f"Description: {description}\nText: {doc.body_text}",
                )
                if response.lower().strip() == "true":
                    beta_user_ids.add(doc.user_id)

        self.update_user_ids_sent_to(datetime_now_str, beta_user_ids)
        for beta_user_id in beta_user_ids:
            self._publish_manager.send_beta_reported_issue_fixed_email(beta_user_id, description)

        # Send to Caleb for testing
        self._publish_manager.send_beta_reported_issue_fixed_email(23133309, description)
        return len(beta_user_ids)

    def get_user_ids_sent_to(self, target_datestring: str) -> Set[int]:
        """
        Get the set of user ids that were sent an email on the given date.

        returns:
            set of user ids
        """
        s3_client, s3_bucket_name = get_s3_client_and_bucket()
        filename = f"{_S3_USERS_EMAIL_SENT_TO_PATH}/{target_datestring}"
        try:
            return set(json.loads(s3_client.download(s3_bucket_name, filename)))
        except:
            print(
                f"Could not find {filename} in S3. Returning empty set.",
            )
            return set()

    def update_user_ids_sent_to(self, target_datestring: str, user_ids: Set[int]) -> None:
        """
        Update the set of user ids that were sent an email on the given date.
        """
        s3_client, s3_bucket_name = get_s3_client_and_bucket()
        filename = f"{_S3_USERS_EMAIL_SENT_TO_PATH}/{target_datestring}"

        # If the file exists, get the current user ids and add the new ones.
        if list(s3_client.yield_filenames(s3_bucket_name, path_prefix=filename)):
            current_user_ids: Set[int] = set(
                json.loads(s3_client.download(s3_bucket_name, filename))
            )
        else:
            current_user_ids = set()
        current_user_ids.update(user_ids)
        upload_to_jeeves_s3(filename, json.dumps(list(current_user_ids)))

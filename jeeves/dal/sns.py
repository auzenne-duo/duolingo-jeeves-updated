"""Managers for publishing events."""
import json

import boto3
import duo_logging
from duolingo_base.config import Config

_config = Config.load_config()


class PublishManager:
    """Manager for basic publishing of events to SNS topics."""

    def __init__(self):
        self._initialized = False
        sns_config = _config.get("sns")
        if not sns_config:
            return

        self._client = boto3.client(
            "sns",
            region_name=sns_config.get("region"),
        )
        self._jeeves_beta_feedback_arn = sns_config["jeeves_beta_feedback_arn"]
        self._initialized = True

    def send_beta_reported_issue_fixed_email(self, user_id: int, qa_summary: str) -> None:
        """
        Publish an event to the jeeves-beta-feedback topic to trigger an email to beta users
        letting them know that an issue they reported has been fixed.

        Parameters:
            user_id: The user ID of the user who reported the issue.
            spike: The spike that was fixed.
            qa_summary: A summary from QA about what was fixed.
        """
        if not self._initialized:
            duo_logging.capture_message(
                "SNS topic is not configured for this environment",
                "warning",
            )
            return

        message = {
            "type": "JeevesBetaFeedback",
            "user_id": user_id,
            "qa_summary": qa_summary,
        }
        self._client.publish(TopicArn=self._jeeves_beta_feedback_arn, Message=json.dumps(message))

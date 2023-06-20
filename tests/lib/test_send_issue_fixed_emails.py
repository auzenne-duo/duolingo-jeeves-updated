import unittest
from datetime import datetime
from unittest.mock import MagicMock, call, patch

from jeeves.lib.send_issue_fixed_emails import _S3_USERS_EMAIL_SENT_TO_PATH, IssueFixedEmailSender
from jeeves.model.shake_to_report_category import ShakeToReportCategory
from jeeves.model.spike_categories import SpikeCategory
from jeeves.model.spike_word import SpikeWord

mock_description = "description"
mock_true_body_text = "body text"

mock_jeeves_document_1 = MagicMock(
    shake_to_report_category=ShakeToReportCategory.EXTERNAL, user_id=111, body_text="body text"
)
mock_jeeves_document_2 = MagicMock(
    shake_to_report_category=ShakeToReportCategory.EXTERNAL, user_id=111, body_text="body text"
)
mock_jeeves_document_3 = MagicMock(
    shake_to_report_category=ShakeToReportCategory.EXTERNAL, user_id=333, body_text="body text"
)
mock_jeeves_document_4 = MagicMock(
    shake_to_report_category=ShakeToReportCategory.EXTERNAL,
    user_id=444,
    body_text="other body text",
)
mock_jeeves_document_5 = MagicMock(
    shake_to_report_category=ShakeToReportCategory.INTERNAL, user_id=555, body_text="body text"
)
mock_jeeves_document_6 = MagicMock(
    shake_to_report_category=ShakeToReportCategory.EXTERNAL, user_id=666, body_text="body text"
)
mock_datestring = "2000-01-01"
mock_spike = SpikeWord(
    word="spike",
    score=5.0,
    date=mock_datestring,
    lang="en",
    spike_group=SpikeCategory.ALL_SPIKES,
)
mock_bucket_name = "bucket_name"
mock_filename = f"{_S3_USERS_EMAIL_SENT_TO_PATH}/2000-01-01"


class TestIssueFixedEmailSender(unittest.TestCase):
    def setUp(self):
        self.mock_os_dal = MagicMock()
        self.mock_os_dal.get_recent_paginated_tickets.return_value = {
            "data": [
                mock_jeeves_document_1,
                mock_jeeves_document_2,
                mock_jeeves_document_3,
                mock_jeeves_document_4,
                mock_jeeves_document_5,
                mock_jeeves_document_6,
            ]
        }

        self.mock_ai_completions_dal = MagicMock()
        expected_true_call = f"Description: {mock_description}\nText: {mock_true_body_text}"
        self.mock_ai_completions_dal.ask.side_effect = (
            lambda _, x: "True" if x == expected_true_call else "False"
        )

        self.mock_publish_manager = MagicMock()
        self.issue_fixed_email_sender = IssueFixedEmailSender(
            self.mock_os_dal, self.mock_ai_completions_dal, self.mock_publish_manager
        )

    def tearDown(self):
        self.mock_os_dal.reset_mock()
        self.mock_ai_completions_dal.reset_mock()
        self.mock_publish_manager.reset_mock()

    @patch("jeeves.lib.send_issue_fixed_emails.IssueFixedEmailSender.get_user_ids_sent_to")
    @patch("jeeves.lib.send_issue_fixed_emails.IssueFixedEmailSender.update_user_ids_sent_to")
    @patch("jeeves.lib.send_issue_fixed_emails.datetime")
    def test_send_issue_fixed_emails(self, mock_datetime, mock_update_user_ids, mock_get_user_ids):
        """
        Only document 1 and 3 should be eligible for emails
        Document 2 has the same id as document 1, so it should be ignored
        Document 4 has a body text which will result in a false response from the AI completions dal
        Document 5 has an internal shake to report category
        Document 6 has a user id that has already been sent to that day
        """
        mock_now_datetime = datetime(2023, 2, 3)
        mock_datetime.now.return_value = mock_now_datetime
        mock_get_user_ids.return_value = {666}

        result = self.issue_fixed_email_sender.send_issue_fixed_emails(mock_spike, mock_description)
        self.assertEqual(result, 2)

        # publish manager should have been called twice with user ids 111 and 333
        self.mock_publish_manager.send_beta_reported_issue_fixed_email.assert_has_calls(
            [
                call(111, mock_description),
                call(333, mock_description),
                call(23133309, mock_description),
            ],
            any_order=True,
        )

        mock_update_user_ids.assert_called_once_with("2023-02-03", {111, 333})

    @patch("jeeves.lib.send_issue_fixed_emails.get_s3_client_and_bucket")
    def test_get_user_ids_sent_to(self, mock_get_s3_client_and_bucket):
        """
        Test that the user ids sent to are returned from the s3 file
        and that if no file is in s3, an empty set is returned
        """
        mock_client = MagicMock()
        mock_client.download.return_value = "[123, 456]"
        mock_get_s3_client_and_bucket.return_value = (mock_client, mock_bucket_name)

        result = self.issue_fixed_email_sender.get_user_ids_sent_to("2000-01-01")
        self.assertEqual(result, {123, 456})
        mock_client.download.assert_called_once_with(mock_bucket_name, mock_filename)

        mock_client.download.side_effect = Exception("test")
        result = self.issue_fixed_email_sender.get_user_ids_sent_to("2000-01-01")
        self.assertEqual(result, set())

    @patch("jeeves.lib.send_issue_fixed_emails.get_s3_client_and_bucket")
    @patch("jeeves.lib.send_issue_fixed_emails.upload_to_jeeves_s3")
    def test_update_user_ids_sent_to(self, mock_upload, mock_get_s3_client_and_bucket):
        """
        Tests that the user ids are updated and uploaded to s3 in the correct format
        """
        mock_client = MagicMock()
        mock_client.download.return_value = "[123, 456]"
        mock_client.yield_filenames.return_value = (file for file in ["2000-01-01"])
        mock_get_s3_client_and_bucket.return_value = (mock_client, MagicMock())

        self.issue_fixed_email_sender.update_user_ids_sent_to(
            "2000-01-01",
            {123, 789},
        )
        mock_upload.assert_called_once_with(mock_filename, "[456, 123, 789]")

    @patch("jeeves.lib.send_issue_fixed_emails.get_s3_client_and_bucket")
    @patch("jeeves.lib.send_issue_fixed_emails.upload_to_jeeves_s3")
    def test_update_user_ids_sent_to_set_default(self, mock_upload, mock_get_s3_client_and_bucket):
        """
        Tests that even if there aren't existing user ids, the new user ids are uploaded to s3 in the correct format
        """
        mock_client = MagicMock()
        mock_client.yield_filenames.return_value = (file for file in [])
        mock_get_s3_client_and_bucket.return_value = (mock_client, MagicMock())

        self.issue_fixed_email_sender.update_user_ids_sent_to(
            "2000-01-01",
            {123, 789},
        )
        mock_upload.assert_called_once_with(mock_filename, "[123, 789]")

"""
Manager for Reddit documents.
"""


import json
from datetime import datetime, timedelta
from typing import Optional

import requests
import rollbar
from duolingo_base.dal.s3 import S3Client
from requests.exceptions import RequestException

from jeeves.manager.jeeves_manager import JeevesManager
from jeeves.model.custom_types import JSON
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.reddit_document import RedditDocument
from jeeves.util.date_util import date_to_str, datetime_to_str, parse_external_datetime
from jeeves.util.error_util import print_request_exception

# The duolingo page receives <100 submissions per hour, so this is reasonable to prevent rate limiting
_MAX_SUBMISSIONS_PER_UPDATE = 200


class RedditManager(JeevesManager):
    @staticmethod
    def get_managed_document_type():
        """
        Please see parent class for documentation
        """
        return RedditDocument

    @staticmethod
    def get_checkpoint_file_name() -> str:
        """
        Returns the name of the S3 file used for storing checkpoint data.
        """
        return f"{RedditManager.get_managed_document_type().get_data_source_identifier()}/checkpoint_data.txt"

    @staticmethod
    def _store_document_to_s3(
        s3_client: S3Client, bucket_name: str, checkpoint_datetime: datetime, doc: JSON
    ) -> str:
        """
        Stores a given document to a given S3 bucket.
        File path in bucket is 'Reddit/<date>/<document ID>'

        Parameters:
            s3_client: Duolingo base library S3 object. Expected to have write
                       access to the bucket specified by bucket_name.
            bucket_name: Name of the bucket we want to store the document to.
            checkpoint_datetime: String representation of a date used for
                             checkpointing, format YYYY-MM-DD hh:mm:ss.
            doc: JSON representation of a document we wish to store.

        Returns:
            String representing date to be used for checkpointing. Will be the
            more recent of checkpoint_date and the date specified in doc.
            Format YYYY-MM-DD hh:mm:ss.
        """

        # Upload document to S3
        document_datetime = parse_external_datetime(doc["utc_datetime_str"])
        date_str = date_to_str(document_datetime)
        document_path = f"{RedditManager.get_managed_document_type().get_data_source_identifier()}/{date_str}/{doc['id']}"
        s3_client.upload(bucket_name, document_path, json.dumps(doc))

        # Update checkpointing information if necessary
        if document_datetime > checkpoint_datetime:
            _CHECKPOINT_FILE = RedditManager.get_checkpoint_file_name()
            checkpoint_datetime = document_datetime
            s3_client.upload(bucket_name, _CHECKPOINT_FILE, datetime_to_str(checkpoint_datetime))

        return checkpoint_datetime

    @staticmethod
    def update_s3_if_necessary(
        s3_client: S3Client, bucket_name: str, default_start_timestamp: float
    ) -> None:
        """
        Please see parent class for documentation.
        """

        _CHECKPOINT_FILE = RedditManager.get_checkpoint_file_name()
        if not list(s3_client.yield_filenames(bucket_name, path_prefix=_CHECKPOINT_FILE)):
            # Create checkpoint file using default timestamp
            new_checkpoint_string = datetime_to_str(
                datetime.utcfromtimestamp(default_start_timestamp)
            )
            s3_client.upload(bucket_name, _CHECKPOINT_FILE, new_checkpoint_string)

        # Get up to _MAX_SUBMISSIONS_PER_UPDATE reddit submissions since checkpoint datetime
        checkpoint_datetime = parse_external_datetime(
            s3_client.download(bucket_name, _CHECKPOINT_FILE).decode("utf-8")
        )
        stored_document_count = 0
        while stored_document_count < _MAX_SUBMISSIONS_PER_UPDATE:
            start_epoch = int(checkpoint_datetime.timestamp())
            route = f"https://api.pushshift.io/reddit/submission/search/?subreddit=duolingo&after={start_epoch}&size=25&sort_type=created_utc&order=asc"

            try:
                response = requests.get(route)
                response.raise_for_status()
            except RequestException as e:
                print_request_exception(e, rollbar_level="warning")
                return
            response_json = response.json()
            if not "data" in response_json:
                rollbar.report_message(
                    f"Reddit response missing data key {response_json}", "warning"
                )
                break
            submissions = response.json()["data"]
            if not submissions:
                break
            for submission in submissions:
                stored_document_count += 1
                checkpoint_datetime = RedditManager._store_document_to_s3(
                    s3_client, bucket_name, checkpoint_datetime, submission
                ) + timedelta(seconds=1)

    @staticmethod
    def get_most_recent_s3_populated_date(s3_client: S3Client, bucket_name: str) -> datetime:
        """
        Please see parent class for documentation.
        """
        checkpoint_timestamp = s3_client.download(
            bucket_name, RedditManager.get_checkpoint_file_name()
        ).decode("utf-8")
        return parse_external_datetime(checkpoint_timestamp)

    @staticmethod
    def process_document(doc_json: JSON) -> Optional[JeevesDocument]:
        """
        Please see parent class for documentation.
        """
        test_doc = RedditDocument.deserialize_from_external_json(doc_json)
        if RedditDocument.check_should_index_document(test_doc):
            return test_doc
        return None

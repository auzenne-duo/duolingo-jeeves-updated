"""
Manager for Reddit documents.
"""


import json
import os
from datetime import datetime
from typing import Dict, Optional, Tuple, Type

import pytz
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
# note that _CLIENT_ID refers to 'personal use script' and _SECRET_TOKEN to 'token'
_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID")
_SECRET_TOKEN = os.environ.get("REDDIT_SECRET_TOKEN")
_USERNAME = os.environ.get("REDDIT_USERNAME")
_PASSWORD = os.environ.get("REDDIT_PASSWORD")

_CREDENTIALS = {"grant_type": "password", "username": _USERNAME, "password": _PASSWORD}
_AUTH = requests.auth.HTTPBasicAuth(_CLIENT_ID, _SECRET_TOKEN)
_HEADERS = {"User-Agent": "MyBot/0.0.1"}


class RedditManager(JeevesManager):
    @staticmethod
    def get_managed_document_type() -> Type[JeevesDocument]:
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
        s3_client: S3Client,
        bucket_name: str,
        doc: dict,
        checkpoint_datetime: datetime,
        checkpoint_id: str,
    ) -> Dict[str, str]:
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
            String representing the last stored message to be used for checkpointing.
        """
        # Upload document to S3
        document_datetime = datetime.fromtimestamp(doc["created_utc"], tz=pytz.utc)
        date_str = date_to_str(document_datetime)
        doc_id = doc["name"]
        document_path = f"{RedditManager.get_managed_document_type().get_data_source_identifier()}/{date_str}/{doc_id}"
        s3_client.upload(bucket_name, document_path, json.dumps(doc))

        # Update checkpointing information if necessary
        if document_datetime > checkpoint_datetime:
            checkpoint_datetime = document_datetime
            s3_client.upload(
                bucket_name,
                RedditManager.get_checkpoint_file_name(),
                json.dumps(
                    {
                        "checkpoint_id": doc_id,
                        "checkpoint_datetime": datetime_to_str(checkpoint_datetime),
                    }
                ),
            )
            return doc_id, document_datetime
        return checkpoint_id, checkpoint_datetime

    @staticmethod
    def _check_checkpoint_id(checkpoint_id: str):
        """
        Returns checkpoint id or empty string if checkpoint id is invalid.
        """
        # we need to check if the checkpoint is valid - i.e. if the post still exists
        # otherwise the API will return nothing
        if checkpoint_id:
            try:
                res = requests.get(
                    f"https://www.reddit.com/api/info.json?id={checkpoint_id}",
                    auth=_AUTH,
                    data=_CREDENTIALS,
                    headers=_HEADERS,
                )
                res.raise_for_status()
                children = res.json()["data"]["children"]
                if len(children) == 0:
                    # if the post has been deleted, we need to reset the checkpoint
                    return ""
                data = children[0]["data"]
                # if the post has been deleted (no author) or removed (is not indexable), we need to reset the checkpoint
                if data.get("author") is None or not data.get("is_robot_indexable", False):
                    return ""
                return checkpoint_id
            except RequestException as e:
                print_request_exception(e, rollbar_level="warning")
                return ""

    @staticmethod
    def update_s3_if_necessary(
        s3_client: S3Client, bucket_name: str, default_start_timestamp: float
    ) -> None:
        """
        Please see parent class for documentation.
        """
        # send our request for an OAuth token
        try:
            res = requests.post(
                "https://www.reddit.com/api/v1/access_token",
                auth=_AUTH,
                data=_CREDENTIALS,
                headers=_HEADERS,
            )
            res.raise_for_status()
        except RequestException as e:
            print_request_exception(e, rollbar_level="warning")
            return
        TOKEN = res.json()["access_token"]
        headers = {**_HEADERS, **{"Authorization": f"bearer {TOKEN}"}}
        checkpoint_file = RedditManager.get_checkpoint_file_name()
        if not list(s3_client.yield_filenames(bucket_name, path_prefix=checkpoint_file)):
            # Create checkpoint file using default timestamp
            new_checkpoint_data = json.dumps(
                {
                    "checkpoint_id": "",
                    "checkpoint_datetime": datetime_to_str(
                        datetime.fromtimestamp(default_start_timestamp)
                    ),
                }
            )
            s3_client.upload(bucket_name, checkpoint_file, new_checkpoint_data)

        # Get up to _MAX_SUBMISSIONS_PER_UPDATE reddit submissions since checkpoint datetime

        stored_document_count = 0
        checkpoint_datetime, checkpoint_id = RedditManager._get_checkpoint_datetime_and_id(
            s3_client, bucket_name
        )
        checkpoint_id = RedditManager._check_checkpoint_id(checkpoint_id)

        while stored_document_count < _MAX_SUBMISSIONS_PER_UPDATE:
            try:
                # while the token is valid (~2 hours) we just add headers=headers to our requests
                # before params selects for messages newer that the checkpoint
                response = requests.get(
                    "https://oauth.reddit.com/r/duolingo/new",
                    headers=headers,
                    params={"limit": _MAX_SUBMISSIONS_PER_UPDATE, "before": checkpoint_id},
                )
                response.raise_for_status()
            except RequestException as e:
                print_request_exception(e, rollbar_level="warning")
                return
            response_json = response.json()

            if response_json.get("data", {}).get("children", None) is None:
                rollbar.report_message(
                    f"Reddit response missing data and children keys {response_json}", "warning"
                )
                break
            submissions = response.json()["data"]["children"]
            if not submissions:
                break
            for submission in submissions:
                stored_document_count += 1
                checkpoint_id, checkpoint_datetime = RedditManager._store_document_to_s3(
                    s3_client, bucket_name, submission["data"], checkpoint_datetime, checkpoint_id
                )

    @staticmethod
    def get_most_recent_s3_populated_date(s3_client: S3Client, bucket_name: str) -> datetime:
        """
        Please see parent class for documentation.
        """
        checkpoint_datetime, _ = RedditManager._get_checkpoint_datetime_and_id(
            s3_client, bucket_name
        )
        return checkpoint_datetime

    @staticmethod
    def _get_checkpoint_datetime_and_id(
        s3_client: S3Client, bucket_name: str
    ) -> Tuple[str, datetime]:
        checkpoint_data = json.loads(
            s3_client.download(bucket_name, RedditManager.get_checkpoint_file_name()).decode(
                "utf-8"
            )
        )
        return (
            parse_external_datetime(checkpoint_data["checkpoint_datetime"]),
            checkpoint_data["checkpoint_id"],
        )

    @staticmethod
    def process_document(doc_json: JSON) -> Optional[JeevesDocument]:
        """
        Please see parent class for documentation.
        """
        test_doc = RedditDocument.deserialize_from_external_json(doc_json)
        if RedditDocument.check_should_index_document(test_doc):
            return test_doc
        return None

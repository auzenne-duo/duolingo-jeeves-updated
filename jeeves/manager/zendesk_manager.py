"""
Manager for Zendesk documents.
"""

import json
import os
import time
from collections import Counter
from datetime import datetime
from typing import Type

import rollbar
from duolingo_base.dal.s3 import S3Client
from requests import RequestException, Session

from jeeves.manager.jeeves_manager import JeevesManager
from jeeves.model.custom_types import JSON
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.zendesk_document import ZendeskDocument
from jeeves.util.date_util import date_to_str, datetime_to_str, parse_external_datetime
from jeeves.util.error_util import print_request_exception

_USER = os.environ.get("ZENDESK_USER")
_PASSWORD = os.environ.get("ZENDESK_PASSWORD")


class ZendeskManager(JeevesManager):
    @staticmethod
    def get_managed_document_type() -> Type[JeevesDocument]:
        """
        Please see parent class for documentation
        """
        return ZendeskDocument

    @staticmethod
    def get_checkpoint_file_name() -> str:
        """
        Returns the name of the S3 file used for storing checkpoint data.
        """
        return f"{ZendeskManager.get_managed_document_type().get_data_source_identifier()}/checkpoint_data.txt"

    @staticmethod
    def update_s3_if_necessary(s3_client, bucket_name: str, default_start_timestamp: float) -> None:
        """
        Please see parent class for documentation
        """

        _CHECKPOINT_FILE = ZendeskManager.get_checkpoint_file_name()
        if not list(s3_client.yield_filenames(bucket_name, path_prefix=_CHECKPOINT_FILE)):
            new_checkpoint_string = str(int(default_start_timestamp))
            s3_client.upload(bucket_name, _CHECKPOINT_FILE, new_checkpoint_string)

        start_timestamp = int(s3_client.download(bucket_name, _CHECKPOINT_FILE))
        zendesk_host = "https://duolingotest.zendesk.com"
        next_url = f"{zendesk_host}/api/v2/incremental/tickets.json?start_time={start_timestamp}"

        urls = []

        with Session() as s:
            s.auth = (_USER, _PASSWORD)
            while True:
                if len(urls) > 0:
                    print("Sleeping", flush=True)
                    time.sleep(10)

                urls.append(next_url)
                # Break if same URL is requested for 5 times in a row
                if len(urls) > 5 and len(Counter(urls[-5:])) == 1:
                    print("Stopped making request to zendesk after consecutive errors")
                    break
                r = ZendeskDocument.rate_limited_get(s, next_url)
                j = json.loads(r.text)
                if "error" in j:
                    raise Exception("Error returned from Zendesk")

                for ticket_json in j["tickets"]:
                    ticket_id = ticket_json["id"]
                    comments_url = f"{zendesk_host}/api/v2/tickets/{ticket_id}/comments.json"
                    attachments = []
                    try:
                        comments_response = ZendeskDocument.rate_limited_get(s, comments_url)
                        comments_response.raise_for_status()
                        comments_structure = json.loads(comments_response.text)
                        for com in comments_structure.get("comments", {}):
                            for attach in com.get("attachments", {}):
                                attachments.append(attach["content_url"])
                    except RequestException as e:
                        print_request_exception(e)
                        # If the comment page cannot be found, then skip it
                        if e.response.status_code == 404:
                            rollbar.report_message(f"Couldn't find url: {comments_url}", "warning")
                        else:
                            # If something non-recoverable has happened, escalate.
                            raise (e)
                    ticket_json["attachments"] = attachments
                    ZendeskManager._store_document_to_s3(s3_client, bucket_name, ticket_json)

                if j["end_time"]:
                    print(
                        f"Downloaded {len(j['tickets'])} tickets until: {datetime_to_str(datetime.fromtimestamp(j['end_time']))}"
                    )
                    s3_client.upload(bucket_name, _CHECKPOINT_FILE, str(int(j["end_time"])))

                if j["next_page"]:
                    next_url = j["next_page"]

                if j["end_of_stream"]:
                    break

    @staticmethod
    def _store_document_to_s3(s3_client: S3Client, bucket_name: str, doc: JSON) -> None:
        """
        Stores a given document to a given S3 bucket.
        File path in bucket is 'Zendesk/<date>/<document ID>'

        Parameters:
            s3_client: Duolingo base library S3 object. Expected to have write
                       access to the bucket specified by bucket_name.
            bucket_name: Name of the bucket we want to store the document to.
            doc: JSON representation of a document we wish to store.
        """

        identifier_directory = (
            ZendeskManager.get_managed_document_type().get_data_source_identifier()
        )
        date_directory = date_to_str(parse_external_datetime(doc["created_at"]))
        full_path = f"{identifier_directory}/{date_directory}/{doc['id']}"

        s3_client.upload(bucket_name, full_path, json.dumps(doc))

    @staticmethod
    def get_most_recent_s3_populated_date(s3_client: S3Client, bucket_name: str) -> datetime:
        """
        Please see parent class for documentation.
        """
        checkpoint_timestamp = int(
            s3_client.download(bucket_name, ZendeskManager.get_checkpoint_file_name())
        )
        return datetime.fromtimestamp(checkpoint_timestamp)

    @staticmethod
    def process_document(doc_json: JSON) -> JeevesDocument:
        """
        Please see parent class for documentation.
        """

        test_doc = ZendeskDocument.deserialize_from_external_json(doc_json)
        if ZendeskDocument.check_should_index_document(test_doc):
            return test_doc

        return None

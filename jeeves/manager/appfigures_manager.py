"""
Manager for Appfigures documents.
"""


from datetime import datetime
import json
import os
from typing import Optional

from requests import Session
from requests.exceptions import RequestException

from duolingo_base.dal.s3 import S3Client

from jeeves.manager.jeeves_manager import JeevesManager

from jeeves.model.custom_types import JSON
from jeeves.model.appfigures_document import AppfiguresDocument
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.util.date_util import date_to_str, parse_external_datetime
from jeeves.util.error_util import print_request_exception

_USER = os.environ.get("APPFIGURES_USER")
_PASSWORD = os.environ.get("APPFIGURES_PASSWORD")
_CLIENT_KEY = os.environ.get("APPFIGURES_CLIENT_KEY")


class AppfiguresManager(JeevesManager):
    @staticmethod
    def get_managed_document_type():
        """
        Please see parent class for documentation
        """
        return AppfiguresDocument

    @staticmethod
    def _get_checkpoint_file_name() -> str:
        """
        Returns the name of the S3 file used for storing checkpoint data.
        """
        return f"{AppfiguresManager.get_managed_document_type().get_data_source_identifier()}/checkpoint_data.txt"

    @staticmethod
    def _store_document_to_s3(
        s3_client: S3Client, bucket_name: str, checkpoint_date: str, doc: JSON
    ) -> str:
        """
        Stores a given document to a given S3 bucket.
        File path in bucket is 'AppFigures/<date>/<document ID>'

        Parameters:
            s3_client: Duolingo base library S3 object. Expected to have write
                       access to the bucket specified by bucket_name.
            bucket_name: Name of the bucket we want to store the document to.
            checkpoint_date: String representation of a date used for
                             checkpointing, format YYYY-MM-DD.
            doc: JSON representation of a document we wish to store.

        Returns:
            String representing date to be used for checkpointing. Will be the
            more recent of checkpoint_date and the date specified in doc.
            Format YYYY-MM-DD.
        """

        # Upload document to S3
        date_str = date_to_str(parse_external_datetime(doc["date"]))
        document_path = f"{AppfiguresManager.get_managed_document_type().get_data_source_identifier()}/{date_str}/{doc['id']}"
        s3_client.upload(bucket_name, document_path, json.dumps(doc))

        # Update checkpointing information if necessary
        if date_str > checkpoint_date:
            _CHECKPOINT_FILE = AppfiguresManager._get_checkpoint_file_name()
            checkpoint_date = date_str
            s3_client.upload(bucket_name, _CHECKPOINT_FILE, checkpoint_date)

        return checkpoint_date

    @staticmethod
    def update_s3_if_necessary(
        s3_client: S3Client, bucket_name: str, default_start_timestamp: float
    ) -> None:
        """
        Please see parent class for documentation.
        """
        _DOCUMENTS_PER_PAGE = 500

        _CHECKPOINT_FILE = AppfiguresManager._get_checkpoint_file_name()
        if not list(s3_client.yield_filenames(bucket_name, path_prefix=_CHECKPOINT_FILE)):
            # Create checkpoint file using default timestamp
            new_checkpoint_string = f"{datetime.utcfromtimestamp(default_start_timestamp).date()}"
            s3_client.upload(bucket_name, _CHECKPOINT_FILE, new_checkpoint_string)

        # Get count of documents stored on s3
        checkpoint_date = s3_client.download(bucket_name, _CHECKPOINT_FILE).decode("utf-8")
        checkpoint_path_prefix = f"{AppfiguresManager.get_managed_document_type().get_data_source_identifier()}/{checkpoint_date}"
        num_stored_files = len(
            list(s3_client.yield_filenames(bucket_name, path_prefix=checkpoint_path_prefix))
        )

        # Get count of available remote documents
        appfigures_host = "https://api.appfigures.com"
        special_headers = {"X-Client-Key": _CLIENT_KEY}
        # The returned value of "total" does not depend on what we pass for
        # "page", so we can pass a value for "page" that will let us start
        # downloading new documents immediately if we need to.
        start_page = 1 + (num_stored_files // _DOCUMENTS_PER_PAGE)
        url_params = {
            "start": f"{checkpoint_date}",
            "sort": "date",
            "count": f"{_DOCUMENTS_PER_PAGE}",
            "page": f"{start_page}",
        }
        template_url = f"{appfigures_host}/v2/reviews"

        print(url_params)

        r = None
        with Session() as s:
            s.auth = (_USER, _PASSWORD)
            s.headers.update(special_headers)
            print(f"Downloading reviews from AppFigures: {url_params}")
            try:
                r = s.get(template_url, params=url_params)
                r.raise_for_status()
            except RequestException as e:
                print_request_exception(e)
                return
            j = json.loads(r.text)
            if j["total"] == num_stored_files:
                # The number of available documents matches how many we have, so
                # there are no new documents available and we are done
                return
            # Otherwise, begin reading new documents, starting from where our
            # stored documents leave off
            page_rover = num_stored_files % _DOCUMENTS_PER_PAGE

            for review_json in j["reviews"][page_rover:]:
                checkpoint_date = AppfiguresManager._store_document_to_s3(
                    s3_client, bucket_name, checkpoint_date, review_json
                )

            while j["pages"] != j["this_page"]:
                next_page = j["this_page"] + 1
                print(next_page, flush=True)
                url_params.update({"page": f"{next_page}"})
                print(f"Downloading reviews from AppFigures: {url_params}", flush=True)
                try:
                    r = s.get(template_url, params=url_params)
                    r.raise_for_status()
                    j = json.loads(r.text)
                    for review_json in j["reviews"]:
                        checkpoint_date = AppfiguresManager._store_document_to_s3(
                            s3_client, bucket_name, checkpoint_date, review_json
                        )

                except RequestException as e:
                    print_request_exception(e)
                    break

    @staticmethod
    def get_most_recent_s3_populated_date(s3_client: S3Client, bucket_name: str) -> datetime:
        """
        Please see parent class for documentation.
        """
        checkpoint_timestamp = s3_client.download(
            bucket_name, AppfiguresManager._get_checkpoint_file_name()
        ).decode("utf-8")
        return parse_external_datetime(checkpoint_timestamp)

    @staticmethod
    def process_document(doc_json: JSON) -> Optional[JeevesDocument]:
        """
        Please see parent class for documentation.
        """
        test_doc = AppfiguresDocument.deserialize_from_external_json(doc_json)
        if AppfiguresDocument.check_should_index_document(test_doc):
            return test_doc
        return None

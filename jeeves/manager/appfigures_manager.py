"""
Manager for Appfigures documents.
"""


import json
import logging
import os
from datetime import date, datetime
from typing import Dict, Optional, Type

from duolingo_base.dal.s3 import S3Client
from requests import Session
from requests.exceptions import RequestException

from jeeves.manager.jeeves_manager import JeevesManager
from jeeves.model.appfigures_document import AppfiguresDocument
from jeeves.model.custom_types import JSON
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.util.date_util import (
    date_to_str,
    get_utc_today,
    parse_external_datetime,
    str_to_date,
    yield_intermediate_dates,
)
from jeeves.util.error_util import print_request_exception

_APPFIGURES_HOST = "https://api.appfigures.com"

_USER = os.environ.get("APPFIGURES_USER", "")
_PASSWORD = os.environ.get("APPFIGURES_PASSWORD", "")
_CLIENT_KEY = os.environ.get("APPFIGURES_CLIENT_KEY", "")

_DOCUMENTS_PER_PAGE = 500
_MAX_DOCS_PER_REQUEST = 10_000

LOG = logging.getLogger(__name__)


class AppfiguresManager(JeevesManager):
    @staticmethod
    def get_managed_document_type() -> Type[JeevesDocument]:
        """
        Please see parent class for documentation
        """
        return AppfiguresDocument

    @staticmethod
    def get_checkpoint_file_name() -> str:
        """
        Returns the name of the S3 file used for storing checkpoint data.
        """
        return f"{AppfiguresManager.get_managed_document_type().get_data_source_identifier()}/checkpoint_data.txt"

    @staticmethod
    def _store_document_to_s3(
        s3_client: S3Client, bucket_name: str, checkpoint_date: date, doc: JSON
    ) -> date:
        """
        Stores a given document to a given S3 bucket.
        File path in bucket is 'Appfigures/<date>/<document ID>'

        Parameters:
            s3_client: Duolingo base library S3 object. Expected to have write
                       access to the bucket specified by bucket_name.
            bucket_name: Name of the bucket we want to store the document to.
            checkpoint_date: The current checkpoint date.
            doc: JSON representation of a document we wish to store.

        Returns:
            The new checkpoint date, which may have just been updated in S3.
        """
        # Upload document to S3
        appfigures_dir = AppfiguresManager.get_managed_document_type().get_data_source_identifier()
        doc_id = doc["id"]
        doc_date = parse_external_datetime(doc["date"]).date()
        document_path = f"{appfigures_dir}/{date_to_str(doc_date)}/{doc_id}"
        s3_client.upload(bucket_name, document_path, json.dumps(doc).encode("utf-8"))

        # Update checkpointing information if necessary
        if doc_date > checkpoint_date:
            _CHECKPOINT_FILE = AppfiguresManager.get_checkpoint_file_name()
            checkpoint_date = doc_date
            s3_client.upload(
                bucket_name, _CHECKPOINT_FILE, checkpoint_date.isoformat().encode("utf-8")
            )

        return checkpoint_date

    @staticmethod
    def update_s3_if_necessary(
        s3_client: S3Client, bucket_name: str, default_start_timestamp: float
    ) -> None:
        """
        Please see parent class for documentation.
        """
        _CHECKPOINT_FILE = AppfiguresManager.get_checkpoint_file_name()
        if not list(s3_client.yield_filenames(bucket_name, path_prefix=_CHECKPOINT_FILE)):
            # Create checkpoint file using default timestamp
            new_checkpoint_string = (
                datetime.utcfromtimestamp(default_start_timestamp).date().isoformat()
            )
            s3_client.upload(bucket_name, _CHECKPOINT_FILE, new_checkpoint_string.encode("utf-8"))

        checkpoint_str = s3_client.download(bucket_name, _CHECKPOINT_FILE).decode("utf-8")
        checkpoint_date = str_to_date(checkpoint_str)

        for date_to_fetch in yield_intermediate_dates(
            str_to_date(checkpoint_str), get_utc_today().date()
        ):
            checkpoint_date = AppfiguresManager.update_s3_for_date(
                s3_client, bucket_name, checkpoint_date, date_to_fetch
            )

    @staticmethod
    def update_s3_for_date(
        s3_client: S3Client, bucket_name: str, checkpoint_date: date, date_to_fetch: date
    ) -> date:
        appfigures_dir = AppfiguresManager.get_managed_document_type().get_data_source_identifier()
        # Get count of documents stored on s3
        num_stored_files = len(
            list(
                s3_client.yield_filenames(
                    bucket_name, path_prefix=f"{appfigures_dir}/{date_to_fetch}"
                )
            )
        )

        # Get count of available remote documents
        special_headers: Dict[str, str] = {"X-Client-Key": _CLIENT_KEY}

        # The returned value of "total" does not depend on what we pass for
        # "page", so we can pass a value for "page" that will let us start
        # downloading new documents immediately if we need to.
        start_page = 1 + (num_stored_files // _DOCUMENTS_PER_PAGE)
        url_params = {
            "start": f"{date_to_fetch}",
            "end": f"{date_to_fetch}",
            "sort": "date",
            "count": f"{_DOCUMENTS_PER_PAGE}",
            "page": f"{start_page}",
        }
        template_url = f"{_APPFIGURES_HOST}/v2/reviews"

        with Session() as s:
            s.auth = (_USER, _PASSWORD)
            s.headers.update(special_headers)
            LOG.info(f"Downloading reviews from Appfigures: {url_params}")
            try:
                r = s.get(template_url, params=url_params)
                r.raise_for_status()
            except RequestException as e:
                print_request_exception(e, rollbar_level="error")
                return checkpoint_date
            j = json.loads(r.text)
            LOG.info(
                f"Total Appfigures reviews for date {date_to_fetch}: {j['total']} ({j['pages']} pages)"
            )
            if j["total"] == num_stored_files:
                # The number of available documents matches how many we have, so
                # there are no new documents available and we are done
                LOG.info(
                    f"Skipping date {date_to_fetch} because the Appfigures S3 bucket is up-to-date"
                )
                return checkpoint_date

            # Otherwise, begin reading new documents, starting from where our
            # stored documents leave off
            page_rover = num_stored_files % _DOCUMENTS_PER_PAGE

            for review_json in j["reviews"][page_rover:]:
                checkpoint_date = AppfiguresManager._store_document_to_s3(
                    s3_client, bucket_name, checkpoint_date, review_json
                )

            while j["pages"] != j["this_page"]:
                next_page = j["this_page"] + 1
                if next_page * _DOCUMENTS_PER_PAGE > _MAX_DOCS_PER_REQUEST:
                    # The Appfigures API only allows us to request a maximum of 10,000 documents at a time.
                    # We cannot request documents with a resolution of less than a day, so for now, we have to
                    # accept this limit. We will work on replacing Appfigures with other APIs to fetch app reviews.
                    # (See discussion in PR duolingo-jeeves #880 for more details.)
                    LOG.warning(
                        f"Appfigures cannot return more than {_MAX_DOCS_PER_REQUEST} reviews."
                    )
                    break

                LOG.info(f"Requesting page {next_page} of Appfigures reviews...")
                url_params.update({"page": f"{next_page}"})
                try:
                    r = s.get(template_url, params=url_params)
                    r.raise_for_status()
                    j = json.loads(r.text)
                    for review_json in j["reviews"]:
                        checkpoint_date = AppfiguresManager._store_document_to_s3(
                            s3_client, bucket_name, checkpoint_date, review_json
                        )

                except RequestException as e:
                    print_request_exception(e, rollbar_level="error")
                    break

        return checkpoint_date

    @staticmethod
    def get_most_recent_s3_populated_date(s3_client: S3Client, bucket_name: str) -> datetime:
        """
        Please see parent class for documentation.
        """
        checkpoint_timestamp = s3_client.download(
            bucket_name, AppfiguresManager.get_checkpoint_file_name()
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

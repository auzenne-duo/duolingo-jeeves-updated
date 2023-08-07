import os
from collections import defaultdict
from datetime import datetime
from typing import Any, DefaultDict, List, Tuple
from uuid import uuid4

import rollbar
from duolingo_base.config import Config
from duolingo_base.dal import s3, sqs

from jeeves import registry as app_registry
from jeeves.config.config import CRAWL_WINDOW_SIZE
from jeeves.dal.opensearch_interface import OpenSearchDAL
from jeeves.lib.identifier_manager_mapping import IDManagerMap
from jeeves.manager.jeeves_manager import JeevesManager
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.util.date_util import (
    date_to_str,
    datetime_to_str,
    get_n_days_ago,
    get_utc_today,
    parse_external_datetime,
    str_to_date,
    yield_intermediate_dates,
)
from jeeves.util.s3_client_and_bucket import get_s3_client_and_bucket

_THRESHOLD_DATE = get_n_days_ago(get_utc_today(), CRAWL_WINDOW_SIZE)
_REFRESH_START_DATE = os.environ.get("REFRESH_START_DATE")  # String in ISO format
_REFRESH_END_DATE = os.environ.get("REFRESH_END_DATE")  # String in ISO format

# Size, in bytes, above which we exclude tickets from indexing.
# This originally was a method of ensuring reasonable network packet sizes
# but turned out to also be a decent method for filtering out newsletter emails.
# Note that this size applies to the entire ticket data structure, not just the
# title/description of the ticket.
_INDEX_LINE_LENGTH_LIMIT = 3500


_config = Config.load_config()


def count_tickets(ticket_dict: DefaultDict[str, List[Any]]) -> DefaultDict[str, int]:
    """
    Given a dictionary of language -> ticket list, counts how many tickets
        there are in the dictionary for each language.

    Paramaters:
        ticket_dict (DefaultDict[str, List[Any]]): a defaultdict of
            lists of support tickets in various languages.

    Returns:
        DefaultDict[str, int]: a defaultdict that represents the length
            of each list in the input dict.
    """
    ticket_counts = defaultdict(int)
    for lang, tickets in ticket_dict.items():
        ticket_counts[lang] = len(tickets)
    return ticket_counts


def diff_counts(
    counts_a: DefaultDict[str, int], counts_b: DefaultDict[str, int]
) -> DefaultDict[str, int]:
    """
    Given two dictionaries of ticket counts with the same keys,
        computes the difference (a - b) in ticket counts for each key

    Parameters:
        counts_a (DefaultDict[Any, int]): A dictionary of integers, presumably
            counts of support tickets produced by count_tickets. Expected
            to have the same keys as counts_b. Represents the minuend of
            the subtraction operation.
        counts_b (DefaultDict[Any, int]): A dictionary of integers, presumably
            counts of support tickets produced by count_tickets. Expected
            to have the same keys as counts_a. Represents the subtrahend of
            the subtraction operation.

    Returns:
        DefaultDict[Any, int]: A defaultdict representing the element-wise
            subtraction of counts_b from counts_a.
    """
    diffs = defaultdict(int)
    for key in counts_a:
        diffs[key] = counts_a[key] - counts_b[key]
    return diffs


def perform_checkpoint(ticket_list: List[JeevesDocument]) -> None:
    """
    Indexes a batch of tickets into OpenSearch to checkpoint them,
    then performs spike detection based on that batch of tickets.

    Parameters:
        ticket_list: List of documents to index
    """
    app_registry(OpenSearchDAL).bulk_index_tickets(ticket_list)


def _send_s3_doc_to_sqs(
    s3_client: s3.S3Client,
    s3_bucket_name: str,
    sqs_client: sqs.SQSClient,
    manager: JeevesManager,
    s3_file: str,
) -> None:
    """
    Given an S3 bucket, information on where to find a file in that bucket,
    an SQS queue, and which manager that file should be associated with,
    access the file with the given name in the given bucket, and enqueue it in
    the given SQS queue with the given manager providing an attribute.

    Parameters:
        s3_client: Duolingo base library S3 DAL object. Expected to have
                   read/write access to a bucket with name bucket_name.
        bucket_name: The name of the S3 bucket we should read documents from.
        sqs_client: Duolingo base library SQS DAL object. Downstream consumers
                    of the represented queue are responsible for verifying
                    documents and indexing them into OpenSearch.
        manager: A subclass of JeevesManager responsible for managing a given
                 subclass of JeevesDocuments. In this method, provides a string
                 to attach as an attribute to the enqueued document.
        s3_file: File path representing the file we wish to enqueue into SQS.
    """
    data_to_enqueue = s3_client.download(s3_bucket_name, s3_file).decode("utf-8")
    data_source_attribute = sqs.SQSMessageAttribute(
        "data_source",
        "String",
        manager.get_managed_document_type().get_data_source_identifier(),
    )
    message_id = uuid4().hex
    message_to_send = sqs.SQSMessage(
        message_id=message_id,
        message_body=data_to_enqueue,
        message_attributes=[data_source_attribute],
    )
    sqs_client.send_messages([message_to_send])


def _crawl_documents_for_data_source(
    s3_client: s3.S3Client, s3_bucket_name: str, sqs_client: sqs.SQSClient, manager: JeevesManager
) -> None:
    """
    Downloads documents from a particular data source and stores them to S3.
    Then, determines what documents need to be indexed into OpenSearch, and
    inserts them into an SQS queue.

    Parameters:
        s3_client: Duolingo base library S3 DAL object. Expected to have
                   read/write access to a bucket with name bucket_name.
        bucket_name: The name of the S3 bucket we should store documents to.
        sqs_client: Duolingo base library SQS DAL object. Downstream consumers
                    of the represented queue are responsible for verifying
                    documents and indexing them into OpenSearch.
        manager: A subclass of JeevesManager responsible for managing a given
                 subclass of JeevesDocuments.
    """

    data_source_identifier = manager.get_managed_document_type().get_data_source_identifier()
    print(f"Finding latest indexed timestamp for data source {data_source_identifier}", flush=True)
    latest_timestamp = app_registry(OpenSearchDAL).get_most_recent_timestamp(
        data_source=data_source_identifier
    )
    any_documents_indexed = bool(latest_timestamp)

    if not any_documents_indexed:
        message = (
            f"Didn't find any documents indexed for data source {data_source_identifier}. "
            + f"Will index documents starting from {date_to_str(_THRESHOLD_DATE)}"
        )
        print(message, flush=True)
        rollbar.report_message(message, "warning")
        latest_timestamp = _THRESHOLD_DATE.timestamp()

    print(
        f"Update starting for {data_source_identifier}",
        flush=True,
    )

    updater = manager.update_s3_if_necessary
    updater(s3_client, s3_bucket_name, _THRESHOLD_DATE.timestamp())

    print(
        f"Update complete for {data_source_identifier}",
        flush=True,
    )

    # After updating we expect the date for which S3 has its most recent data
    # will be at least as recent as the date for which OpenSearch has its
    # most recent data. We then determine all dates between and including these
    # two dates, and export appropriate data from S3 to OpenSearch.

    # Right now, "appropriate data" means "all data", which is acceptable for
    # MVP but there is almost certainly a more intelligent way to select which
    # data should be exported.

    s3_latest_timestamp = manager.get_most_recent_s3_populated_date(s3_client, s3_bucket_name)
    s3_path_stem = f"{data_source_identifier}"
    print(
        f"Sending {data_source_identifier} documents from {datetime_to_str(datetime.fromtimestamp(latest_timestamp))} to {datetime_to_str(s3_latest_timestamp)} to SQS",
        flush=True,
    )
    for inter_date in yield_intermediate_dates(
        datetime.fromtimestamp(latest_timestamp).date(), s3_latest_timestamp.date()
    ):
        date_str = date_to_str(inter_date)
        s3_date_dir = f"{s3_path_stem}/{date_str}"
        for s3_file in s3_client.yield_filenames(s3_bucket_name, path_prefix=s3_date_dir):
            _send_s3_doc_to_sqs(s3_client, s3_bucket_name, sqs_client, manager, s3_file)


def get_s3_client_buckets_and_sqs() -> Tuple[s3.S3Client, str, sqs.SQSClient]:
    """
    Return s3 client, s3 bucket name, and sqs client
    """
    s3_client, s3_bucket_name = get_s3_client_and_bucket()
    sqs_client = sqs.SQSClient(
        _config.get_nested(["sqs_download_verify_pipeline", "queue_url"]),
        region_name=_config.get_nested(["sqs_download_verify_pipeline", "region_name"]),
        endpoint_url=_config.get_nested(["sqs_download_verify_pipeline", "endpoint_url"]),
    )
    return s3_client, s3_bucket_name, sqs_client


def crawl_tickets() -> None:
    """
    Runs _crawl_documents_for_data_source on each available data source; see
    that method for more details.
    """
    s3_client, s3_bucket_name, sqs_client = get_s3_client_buckets_and_sqs()
    for manager in IDManagerMap.get_all_managers():
        _crawl_documents_for_data_source(s3_client, s3_bucket_name, sqs_client, manager)


def force_refresh_tickets() -> None:
    """
    Refreshes tickets by getting all the tickets from s3 and adding them to sqs
    """
    s3_client, s3_bucket_name, sqs_client = get_s3_client_buckets_and_sqs()

    start_date = _THRESHOLD_DATE.date()
    end_date = get_utc_today().date()
    if _REFRESH_START_DATE is None or _REFRESH_START_DATE == "":
        raise Exception("Please provide a start date")
    try:
        start_date = str_to_date(_REFRESH_START_DATE)
    except:
        raise Exception("Could not parse start date range string")
    if _REFRESH_END_DATE is not None and _REFRESH_END_DATE != "":
        try:
            end_date = str_to_date(_REFRESH_END_DATE)
        except:
            raise Exception("Could not parse end date range string")
    if start_date > end_date or end_date > get_utc_today().date():
        raise Exception("Invalid date range")

    print(
        f"Forcefully refreshing all documents from S3 from {start_date} to {end_date}",
        flush=True,
    )
    for manager in IDManagerMap.get_all_managers():
        s3_path_stem = manager.get_managed_document_type().get_data_source_identifier()
        document_count, document_scan_count = 0, 0
        for s3_file in s3_client.yield_filenames(s3_bucket_name, path_prefix=s3_path_stem):
            document_scan_count += 1
            if document_scan_count % 1000 == 0:
                print(f"{document_scan_count} {s3_path_stem} documents scanned through", flush=True)
            try:
                date = parse_external_datetime(s3_file.split("/")[1])
            except:
                print(f"couldn't parse {date}")
                continue
            if date.date() < start_date or date.date() > end_date:
                continue
            if document_count % 1000 == 0:
                print(f"{document_count} {s3_path_stem} documents refreshed", flush=True)
            if s3_file != manager.get_checkpoint_file_name():
                _send_s3_doc_to_sqs(s3_client, s3_bucket_name, sqs_client, manager, s3_file)
                document_count += 1

        print(f"Finished refreshing documents from {s3_path_stem}", flush=True)

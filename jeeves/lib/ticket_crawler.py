from collections import defaultdict
from datetime import datetime
import re
from typing import Any, DefaultDict, List
from uuid import uuid4

from duolingo_base.config import Config
from duolingo_base.dal import sqs, s3

from jeeves.config.config import CRAWL_WINDOW_SIZE
from jeeves.dal.elasticsearch_interface import ElasticDAL
from jeeves.lib.identifier_manager_mapping import IDManagerMap
from jeeves.lib.spike_detector import split_beta_batches_and_run_detector
from jeeves.manager.jeeves_manager import JeevesManager
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.util.date_util import (
    date_to_str,
    get_n_days_ago,
    get_utc_today,
    yield_intermediate_dates,
)


_THRESHOLD_DATE = get_n_days_ago(get_utc_today(), CRAWL_WINDOW_SIZE)

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
    Indexes a batch of tickets into Elasticsearch to checkpoint them,
    then performs spike detection based on that batch of tickets.

    Parameters:
        ticket_list: List of documents to index
    """
    ElasticDAL.bulk_index_tickets(ticket_list)

    split_beta_batches_and_run_detector([])
    # split_beta_batches_and_run_detector(ticket_list)


def _crawl_documents_for_data_source(
    s3_client: s3.S3Client, s3_bucket_name: str, sqs_client: sqs.SQSClient, manager: JeevesManager
) -> None:
    """
    Downloads documents from a particular data source and stores them to S3.
    Then, determines what documents need to be indexed into Elasticsearch, and
    inserts them into an SQS queue.

    Parameters:
        s3_client: Duolingo base library S3 DAL object. Expected to have
                   read/write access to a bucket with name bucket_name.
        bucket_name: The name of the S3 bucket we should store documents to.
        sqs_client: Duolingo base library SQS DAL object. Downstream consumers
                    of the represented queue are responsible for verifying
                    documents and indexing them into Elasticsearch.
        manager: A subclass of JeevesManager responsible for managing a given
                 subclass of JeevesDocuments.
    """

    latest_timestamp = ElasticDAL.get_most_recent_timestamp(
        data_source=manager.get_managed_document_type().get_data_source_identifier()
    )
    any_documents_indexed = bool(latest_timestamp)

    if not any_documents_indexed:
        latest_timestamp = _THRESHOLD_DATE.timestamp()

    print(
        f"Update starting for {manager.get_managed_document_type().get_data_source_identifier()}",
        flush=True,
    )

    updater = manager.update_s3_if_necessary
    updater(s3_client, s3_bucket_name, _THRESHOLD_DATE.timestamp())

    print(
        f"Update complete for {manager.get_managed_document_type().get_data_source_identifier()}",
        flush=True,
    )

    # After updating we expect the date for which S3 has its most recent data
    # will be at least as recent as the date for which Elasticsearch has its
    # most recent data. We then determine all dates between and including these
    # two dates, and export appropriate data from S3 to Elasticsearch.

    # Right now, "appropriate data" means "all data", which is acceptable for
    # MVP but there is almost certainly a more intelligent way to select which
    # data should be exported.

    s3_latest_timestamp = manager.get_most_recent_s3_populated_date(s3_client, s3_bucket_name)
    s3_path_stem = f"{manager.get_managed_document_type().get_data_source_identifier()}"
    for inter_date in yield_intermediate_dates(
        datetime.fromtimestamp(latest_timestamp).date(), s3_latest_timestamp.date()
    ):
        date_str = date_to_str(inter_date)
        s3_date_dir = f"{s3_path_stem}/{date_str}"
        for s3_file in s3_client.yield_filenames(s3_bucket_name, path_prefix=s3_date_dir):
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


def crawl_tickets() -> None:
    """
    Runs _crawl_documents_for_data_source on each available data source; see
    that method for more details.
    """

    s3_client = None
    if _config.get_nested(["s3_document_cache", "endpoint_url"]):
        s3_client = s3.S3Client(_config.get_nested(["s3_document_cache", "endpoint_url"]))
    else:
        s3_client = s3.S3Client()
    s3_bucket_name = _config.get_nested(["s3_document_cache", "bucket_name"])

    sqs_client = sqs.SQSClient(
        _config.get_nested(["sqs_download_verify_pipeline", "queue_url"]),
        region_name=_config.get_nested(["sqs_download_verify_pipeline", "region_name"]),
        endpoint_url=_config.get_nested(["sqs_download_verify_pipeline", "endpoint_url"]),
    )

    for manager in IDManagerMap.get_all_managers():
        _crawl_documents_for_data_source(s3_client, s3_bucket_name, sqs_client, manager)


def load_zh_stop_words() -> List[str]:
    """
    Loads a list of Chinese words from a static file that should not be
        considered for spikiness analysis.

    Returns:
        List[str]: A list of strings representing Chinese stop words, with
            one stop word per line.
    """
    with open("jeeves/resources/zh_stop_words.txt", "r") as stop_word_file:
        stripped_lines = [line.strip() for line in stop_word_file]
        stop_words = [word for word in stripped_lines if word]
        return stop_words


# The list of Chinese stop words is VERY LARGE so we don't want to load it
# every time we check a word. Instead, load it once and use that copy.
_ZH_STOP_WORDS = load_zh_stop_words()


def _valid_word(lang, word):
    if lang == "en":
        # Word should be at least 3 letters and can have chars [a-zA-Z] only.
        return bool(re.search(r"^[a-zA-Z]{3,}$", word))
    elif lang == "es":
        # Same as the English filter but also include diacritic characters
        return bool(re.search(r"^[a-zA-ZÁáÉéÍíÓóÚúÜüÑñ]{3,}$", word))
    elif lang == "zh":
        return word not in _ZH_STOP_WORDS
    else:
        return True

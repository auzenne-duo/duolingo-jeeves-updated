from collections import defaultdict
from datetime import datetime
import re
import time
from typing import Any, DefaultDict, List

from jeeves.config.config import CRAWL_WINDOW_SIZE
from jeeves.dal.elasticsearch_interface import ElasticDAL
from jeeves.lib.identifier_document_mapping import IDENTIFIER_DOCUMENT_MAPPING
from jeeves.lib.spike_detector import run_spike_detector_for_batch
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.util.date_util import datetime_to_str, get_n_days_ago, get_utc_today


# Jeeves ignores tickets sent by the following emails
_SENDERS_TO_IGNORE = {"no-reply@duolingo.com", "community@duolingo.com"}
# It will also ignore tickets sent to the following emails
_RECEIVERS_TO_IGNORE = {
    "luis@duolingotest.zendesk.com",
    "luis@duolingo.com",
    "institution@testcenter.zendesk.com",
    "testcenter-support@duolingo.com",
}
# It will also ignore tickets with one or more of the following tags
_TAGS_TO_IGNORE = {"duolingo_english_test___appeal_results"}

_THRESHOLD_DATE = get_n_days_ago(get_utc_today(), CRAWL_WINDOW_SIZE)

# Size, in bytes, above which we exclude tickets from indexing.
# This originally was a method of ensuring reasonable network packet sizes
# but turned out to also be a decent method for filtering out newsletter emails.
# Note that this size applies to the entire ticket data structure, not just the
# title/description of the ticket.
_INDEX_LINE_LENGTH_LIMIT = 3500

# Number of tickets we collect in one batch before putting them in Elasticsearch
_CHECKPOINTING_THRESHOLD = 1000


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


def _perform_checkpoint(ticket_list: List[JeevesDocument]) -> None:
    """
    Indexes a batch of tickets into Elasticsearch to checkpoint them,
    then performs spike detection based on that batch of tickets.

    If we do incremental spike detection like this with multiple data sources,
    and we ingest one data source fully before moving on to the next one, then
    we end up having to re-run spike detection at least once per data source.
    We could avoid this by interleaving how we ingest data, however, spike
    detection is probably fast enough that doing so wouldn't save more than a
    few seconds.

    Parameters:
        ticket_list: List of documents to index
    """
    ElasticDAL.bulk_index_tickets(
        [document.serialize_to_json(document) for document in ticket_list]
    )

    time.sleep(2)

    run_spike_detector_for_batch(ticket_list)


def _crawl_documents_for_data_source(data_source) -> None:
    """
    Downloads documents from a particular data source, indexes them to
    Elasticsearch, and performs spike detection.

    Parameters:
        data_source (str): Identifier of data source to download from
        downloader: Function to call to download tickets

        TODO: USING A FUNCTION HERE IS TEMPORARY UNTIL WE INTRODUCE A MORE
              ROBUST CHECKPOINTING STRATEGY.
    """

    latest_timestamp = ElasticDAL.get_most_recent_timestamp(data_source=data_source)
    any_documents_indexed = bool(latest_timestamp)
    if not any_documents_indexed:
        latest_timestamp = _THRESHOLD_DATE.timestamp()

    print(
        "Downloading new documents since {}".format(
            datetime_to_str(datetime.fromtimestamp(latest_timestamp))
        ),
        flush=True,
    )

    good_document_list = []

    downloader = IDENTIFIER_DOCUMENT_MAPPING[data_source].download_external_documents

    for document in downloader(latest_timestamp):

        # Filter out old documents
        if _THRESHOLD_DATE > document.date_time:
            continue

        if not document.check_should_index_document(document):
            continue

        # Some things break if the document index is unpopulated so we want to
        # get a nonzero number of documents indexed ASAP, and the fastest nonzero
        # number of documents to index is "one document".
        if not any_documents_indexed:
            print("Indexing first document", flush=True)
            _perform_checkpoint([document])
            any_documents_indexed = True
            continue

        good_document_list.append(document)
        if len(good_document_list) % (_CHECKPOINTING_THRESHOLD / 10) == 0:
            print(f"Document list has size {len(good_document_list)}", flush=True)

        # Store documents in batches as a form of checkpointing
        if len(good_document_list) >= _CHECKPOINTING_THRESHOLD:
            _perform_checkpoint(good_document_list)
            good_document_list = []

    _perform_checkpoint(good_document_list)


def crawl_tickets() -> None:
    """
    Downloads documents from all data sources, indexes them to Elasticsearch,
    and performs spike detection incrementally.
    """

    for identifier in IDENTIFIER_DOCUMENT_MAPPING:
        _crawl_documents_for_data_source(identifier)


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

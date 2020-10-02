from collections import defaultdict
from datetime import datetime
import json
import re
import time
from typing import Any, DefaultDict, List

from jeeves.config.config import CRAWL_WINDOW_SIZE
from jeeves.dal.elasticsearch_interface import ElasticDAL

from jeeves.lib.json_serializer import deserialize_zendesk_ticket_json, serialize_tickets
from jeeves.lib.spike_detector import run_spike_detector_for_batch
from jeeves.lib.zendesk_ticket_downloader import yield_json_tickets
from jeeves.model.products import Products
from jeeves.model.support_ticket import SupportTicket
from jeeves.model.supported_languages import SUPPORTED_LANGUAGES
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


def _perform_checkpoint(ticket_list: List[SupportTicket]) -> None:
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
        ticket_list: List of support tickets to index
    """
    ElasticDAL.bulk_index_tickets(
        [
            json.loads(line)
            for line in serialize_tickets(ticket_list).split("\n")
            if len(line) < _INDEX_LINE_LENGTH_LIMIT
        ]
    )

    time.sleep(2)

    run_spike_detector_for_batch(ticket_list)


def crawl_tickets():
    """ Downloads recent tickets and stores them to Elasticsearch. """

    latest_timestamp = ElasticDAL.get_most_recent_timestamp()
    any_tickets_indexed = bool(latest_timestamp)
    if not any_tickets_indexed:
        latest_timestamp = _THRESHOLD_DATE.timestamp()

    print(
        "Downloading new tickets since {}".format(
            datetime_to_str(datetime.fromtimestamp(latest_timestamp))
        ),
        flush=True,
    )

    good_ticket_list = []

    for ticket_json in yield_json_tickets(latest_timestamp):

        ticket = deserialize_zendesk_ticket_json(ticket_json)

        # Filter out old tickets
        if _THRESHOLD_DATE > ticket.date_time:
            continue

        # Ignore a ticket if created via chat because they add noise
        if ticket.via["channel"] == "chat":
            continue

        # Ignore a ticket if a sender email is on a blocklist
        from_data = ticket.via["source"]["from"]
        if from_data and "address" in from_data and from_data["address"] in _SENDERS_TO_IGNORE:
            continue

        # Ignore a ticket if receiving email is on a blocklist
        to_data = ticket.via["source"]["to"]
        if to_data and "address" in to_data and to_data["address"] in _RECEIVERS_TO_IGNORE:
            continue

        tag_data = ticket.tags
        if tag_data and set(tag_data) & _TAGS_TO_IGNORE:
            continue

        # Skip tickets that have an empty string ('') description
        # after cleanup, which are those that consist of just
        # punctuation/spacing after cleanup
        if not ticket.description:
            continue

        if ticket.language not in SUPPORTED_LANGUAGES.__members__:
            continue

        if ticket.product != Products.LA.name:
            continue

        # Some things break if the ticket index is unpopulated so we want to
        # get a nonzero number of tickets indexed ASAP, and the fastest nonzero
        # number of tickets to index is "one ticket".
        if not any_tickets_indexed:
            print("Indexing first ticket", flush=True)
            _perform_checkpoint([ticket])
            any_tickets_indexed = True
            continue

        good_ticket_list.append(ticket)
        if len(good_ticket_list) % (_CHECKPOINTING_THRESHOLD / 10) == 0:
            print(f"Ticket list has size {len(good_ticket_list)}", flush=True)

        # Store tickets in batches as a form of checkpointing
        if len(good_ticket_list) >= _CHECKPOINTING_THRESHOLD:
            _perform_checkpoint(good_ticket_list)
            good_ticket_list = []

    _perform_checkpoint(good_ticket_list)

    return latest_timestamp


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

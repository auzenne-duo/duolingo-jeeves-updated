from collections import defaultdict
from datetime import datetime
from hashlib import md5
import re
from typing import Any, DefaultDict, List
from unicodedata import normalize

from jeeves.config.config import CRAWL_WINDOW_SIZE
from jeeves.dal.support_tickets import SupportTicketDAL
from jeeves.lib.json_serializer import deserialize_zendesk_ticket_json
from jeeves.lib.zendesk_ticket_downloader import yield_json_tickets
from jeeves.model.products import Products
from jeeves.model.supported_languages import SUPPORTED_LANGUAGES
from jeeves.util.date_util import datetime_to_str, date_to_str, get_n_days_ago, get_utc_today
from jeeves.util.email_preprocessor import cleanup_email
from jeeves.util.tokenizer import Tokenizer


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


def crawl_tickets():
    """ Downloads recent tickets from Zendesk and stores them to Memcache. """
    ticket_dict = defaultdict(list)
    for lang_name, lang in SUPPORTED_LANGUAGES.__members__.items():
        ticket_dict[lang_name] = SupportTicketDAL.get_labeled_support_tickets(language=lang)

    original_ticket_counts = count_tickets(ticket_dict)
    num_original_tickets = sum(original_ticket_counts.values())

    if num_original_tickets:
        latest_timestamp = max(
            ticket.date_time for tickets in ticket_dict.values() for ticket in tickets
        ).timestamp()
    else:
        latest_timestamp = _THRESHOLD_DATE.timestamp()

    print(
        "Downloading new tickets since {}".format(
            datetime_to_str(datetime.fromtimestamp(latest_timestamp))
        )
    )

    def get_hash(ticket):
        hash_seed = ticket.description + date_to_str(ticket.date_time)
        return md5(hash_seed.encode("utf-8")).hexdigest()

    tokenizer = Tokenizer()

    content_history = {get_hash(ticket) for tickets in ticket_dict.values() for ticket in tickets}
    for ticket_json in yield_json_tickets(latest_timestamp):

        ticket = deserialize_zendesk_ticket_json(ticket_json)

        # Filter out old tickets
        if _THRESHOLD_DATE > ticket.date_time:
            continue

        # Ignore a ticket with a duplicate description sent on a specific day
        content_hash = get_hash(ticket)
        if content_hash in content_history:
            continue
        content_history.add(content_hash)

        # Ignore a ticket if created via chat because they add noise
        if ticket.via["channel"] == "chat":
            continue

        # Ignore a ticket if a sender email is on a blacklist
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

        # By this point we have determined that the ticket is OK to save
        # so it is now safe to invest resources in tokenization
        subj_tokens = tokenizer.tokenize(ticket.subject, ticket.language)
        desc_tokens = tokenizer.tokenize(cleanup_email(ticket.description), ticket.language)
        prenormal_tokens = subj_tokens + desc_tokens
        normalized_tokens = [normalize("NFKC", tok) for tok in prenormal_tokens]
        valid_tokens = [tok for tok in normalized_tokens if _valid_word(ticket.language, tok)]

        ticket = deserialize_zendesk_ticket_json(ticket_json, valid_tokens)

        ticket_dict[ticket.language].append(ticket)

    ticket_counts_after_crawling = count_tickets(ticket_dict)

    # Remove tickets that are too old and save memory
    for lang_name in SUPPORTED_LANGUAGES.__members__:
        ticket_dict[lang_name] = [
            t for t in ticket_dict[lang_name] if t.date_time > _THRESHOLD_DATE
        ]

    ticket_counts_after_filtering = count_tickets(ticket_dict)

    num_tickets_added = diff_counts(ticket_counts_after_crawling, original_ticket_counts)
    num_tickets_decreased = diff_counts(ticket_counts_after_crawling, ticket_counts_after_filtering)

    for lang_name, lang in SUPPORTED_LANGUAGES.__members__.items():
        SupportTicketDAL.set_labeled_support_tickets(ticket_dict[lang_name], language=lang)

    print(f"# original tickets: {original_ticket_counts}")
    print(f"# tickets after crawling: {ticket_counts_after_crawling}")
    print(
        f"# of tickets in DB: {ticket_counts_after_filtering} (+{num_tickets_added}, -{num_tickets_decreased})"
    )

    return num_tickets_added


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

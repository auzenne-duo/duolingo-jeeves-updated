from datetime import datetime
from hashlib import md5

from jeeves.config.config import CRAWL_WINDOW_SIZE
from jeeves.dal.support_tickets import SupportTicketDAL
from jeeves.lib.zendesk_ticket_downloader import yield_tickets
from jeeves.model.products import Products
from jeeves.model.supported_languages import SUPPORTED_LANGUAGES
from jeeves.util.date_util import datetime_to_str, date_to_str, get_n_days_ago, get_utc_today

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


def crawl_tickets():
    """ Downloads recent tickets from Zendesk and store them to Memcache. """
    tickets = SupportTicketDAL.get_labeled_support_tickets()

    num_original_tickets = len(tickets)

    if tickets:
        latest_timestamp = max(ticket.date_time for ticket in tickets).timestamp()
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

    content_history = {get_hash(ticket) for ticket in tickets}
    for ticket in yield_tickets(latest_timestamp):
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

        if ticket.language != SUPPORTED_LANGUAGES.en.name:
            continue

        if ticket.product != Products.LA.name:
            continue

        tickets.append(ticket)

    num_tickets_after_crawling = len(tickets)

    # Remove tickets that are too old and save memory
    tickets = list(filter(lambda t: t.date_time > _THRESHOLD_DATE, tickets))

    num_tickets_after_filtering = len(tickets)

    num_tickets_added = num_tickets_after_crawling - num_original_tickets
    num_tickets_decreased = num_tickets_after_crawling - num_tickets_after_filtering

    print(
        "# of tickets in DB: %s (+%s, -%s)"
        % (len(tickets), num_tickets_added, num_tickets_decreased)
    )

    SupportTicketDAL.set_labeled_support_tickets(tickets)

    return num_tickets_added

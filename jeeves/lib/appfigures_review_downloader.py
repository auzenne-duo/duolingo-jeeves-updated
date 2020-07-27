"""
Exports reviews from AppFigures.
This file is basically a carbon-copy of zendesk_ticket_downloader.py,
but with modifications to the REST API calls to work with AppFigures.
API doc: https://docs.appfigures.com/api/reference/v2/reviews

We also do conversion on the returned JSON to make it fit into the
existing Zendesk ticket structure. This is very hacky and probably a 'bad idea'.
In the future we should probably change the ticket storage structure to support
different formats of tickets without having to convert them like this.
"""

from datetime import datetime
import os
import requests
import simplejson as json
from typing import Any, Dict

_APPFIGURES_HOST = "https://api.appfigures.com"

_SOURCE_PREFIX = "AF"

_USER = os.environ.get("APPFIGURES_USER")
_PASSWORD = os.environ.get("APPFIGURES_PASSWORD")
_CLIENT_KEY = os.environ.get("APPFIGURES_CLIENT_KEY")


def yield_json_reviews(start_timestamp: int) -> Dict[str, Any]:
    """
    Yields app store reviews gathered by the AppFigures API.

    Parameters:
        start_timestamp: A unix timestamp (UTC).

    Yields:
        A JSON representation of an app store review.
    """

    special_headers = {"X-Client-Key": _CLIENT_KEY}

    url_params = {
        "start": f"{datetime.utcfromtimestamp(start_timestamp).date()}",
        "sort": "date",
        "count": "500",
        "page": "1",
    }

    template_url = f"{_APPFIGURES_HOST}/v2/reviews"

    r = None
    while True:
        print(f"Downloading reviews from AppFigures: {url_params}")
        try:
            r = requests.get(
                template_url, auth=(_USER, _PASSWORD), headers=special_headers, params=url_params
            )
            if r.status_code >= 400:
                r.raise_for_status()
            j = json.loads(r.text)

            for review_json in j["reviews"]:
                yield convert_to_ticket_json(review_json)

            if j["pages"] == j["this_page"]:
                break

            next_page = j["this_page"] + 1
            url_params.update({"page": f"{next_page}"})

        except requests.exceptions.RequestException as e:
            print("An exception occured for the following request:")
            print(e.request)
            print("The above request generated the following response:")
            print(e.response)
            break


def convert_to_ticket_json(review_json: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convert the review JSON spat out by AppFigures into something that looks
    like what Zendesk produces. Specifics will be discussed as they appear.

    Parameters:
        review_json: A JSON representation of an AppFigures review.

    Returns:
        A JSON representation of a functionally identical Zendesk ticket.
    """

    ticket_json = {}

    # Prepend a source designator to the review ID
    ticket_json["id"] = "{_SOURCE_PREFIX}_{review_json['id']}"

    # These ones are easy because AppFigures just gives us what we want
    ticket_json["created_at"] = review_json["date"]
    ticket_json["subject"] = review_json["title"]
    ticket_json["description"] = review_json["review"]

    # Set up the 'via' data structure
    ticket_json["via"] = {}
    # Channel is whatever store the review came from
    ticket_json["via"]["channel"] = review_json["store"]
    # Manually set up the one relevant source field
    ticket_json["via"]["source"] = {}
    ticket_json["via"]["source"]["from"] = {}
    ticket_json["via"]["source"]["from"]["name"] = review_json["author"]
    # Other "via" fields are not relevant
    ticket_json["via"]["source"]["to"] = {}
    ticket_json["via"]["source"]["rel"] = None

    # Mark that this is an AppFigures review
    ticket_json["data_source"] = "AppFigures"

    # All other fields can't be filled in so we set them to 0 (or equivalent)
    ticket_json["priority"] = None
    ticket_json["tags"] = []
    ticket_json["requester_id"] = 0

    return ticket_json

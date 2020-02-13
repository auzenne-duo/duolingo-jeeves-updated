"""
Exports Zendesk tickets.
We are using `incremental_export` API that allows us to get 1000 tickets at a time.
We have proper sleeps in each iteration in order to avoid being rate-limited.
API doc: https://developer.zendesk.com/rest_api/docs/core/incremental_export
"""

from collections import Counter
from datetime import datetime
import os
import requests
import simplejson as json
import time

from jeeves.lib.json_serializer import deserialize_zendesk_ticket_json
from jeeves.util.date_util import datetime_to_str

_ZENDESK_HOST = "https://duolingotest.zendesk.com"

_USER = os.environ.get("ZENDESK_USER")
_PASSWORD = os.environ.get("ZENDESK_PASSWORD")


def yield_tickets(start_timestamp):
    """
    Yields tickets downloaded from Zendesk API.

    Parameters:
        start_timestamp: A unix timestamp (UTC).

    Yields:
        A SupportTicket object.
    """
    next_url = "%s/api/v2/incremental/tickets.json?start_time=%s" % (
        _ZENDESK_HOST,
        int(start_timestamp),
    )

    urls = []
    while True:
        if len(urls) > 0:
            time.sleep(10)

        urls.append(next_url)
        # Break if same URL is requested for 5 times in a row
        if len(urls) > 5 and len(Counter(urls[-5:])) == 1:
            print("Stopped making request to zendesk after consecutive errors")
            break
        print("Downloading tickets from zendesk:", next_url)
        r = requests.get(next_url, auth=(_USER, _PASSWORD))
        j = json.loads(r.text)
        try:
            if "error" in j:
                raise Exception("Error returned from Zendesk")

            for ticket_json in j["tickets"]:
                ticket = deserialize_zendesk_ticket_json(ticket_json)
                yield ticket

            if j["end_time"]:
                print(
                    "Downloaded %s tickets until: %s"
                    % (len(j["tickets"]), datetime_to_str(datetime.fromtimestamp(j["end_time"])))
                )

            if j["next_page"]:
                next_url = j["next_page"]

            if j["count"] < 1000:
                break

        except Exception as e:
            print("Exception happened for URL:", next_url)
            print("Status code:", r.status_code)
            print("Returned JSON:", r.text)
            raise (e)

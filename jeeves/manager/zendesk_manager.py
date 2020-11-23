"""
Manager for Zendesk documents.
"""

from collections import Counter
from datetime import datetime
import json
import os
import time
from typing import Iterator, Type

from requests import Response, Session

from jeeves.manager.jeeves_manager import JeevesManager
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.zendesk_document import ZendeskDocument
from jeeves.util.date_util import datetime_to_str


_USER = os.environ.get("ZENDESK_USER")
_PASSWORD = os.environ.get("ZENDESK_PASSWORD")


class ZendeskManager(JeevesManager):
    @staticmethod
    def get_managed_document_type() -> Type[JeevesDocument]:
        """
        Please see parent class for documentation
        """
        return ZendeskDocument

    @staticmethod
    def _rate_limited_get(s: Session, request_url: str) -> Response:
        """
        Zendesk has some rate limits in place that we need to respect. According to
        https://developer.zendesk.com/rest_api/docs/support/usage_limits, we can
        track the X-Rate-Limit-Remaining header and slow down our request frequency
        as we start to run out of requests. This function is a wrapper around
        Session.get() with such a modification.

        Parameters:
            s: The Session object that will be making our request.
            request_url: The URL we want to make a GET request to.

        Returns:
            The Response object returned by Session.get().
        """

        r = s.get(request_url)

        if "X-Rate-Limit-Remaining" in r.headers:
            remaining_limit = int(r.headers["X-Rate-Limit-Remaining"])
            # These values are pretty arbitrary
            # We need a gradual throttling like this because multiple instances
            # of this code can be running at once, all tied to the same Zendesk
            # account (i.e. prod, dev, and local dev all eat into the rate limit)
            if remaining_limit < 5:
                time.sleep(60)
            elif remaining_limit < 10:
                time.sleep(30)
            elif remaining_limit < 50:
                time.sleep(10)
            elif remaining_limit < 100:
                time.sleep(5)
            elif remaining_limit < 150:
                time.sleep(1)
        return r

    @staticmethod
    def download_documents(start_timestamp: float) -> Iterator[JeevesDocument]:
        """
        Please see parent class for documentation
        """

        zendesk_host = "https://duolingotest.zendesk.com"

        next_url = (
            f"{zendesk_host}/api/v2/incremental/tickets.json?start_time={int(start_timestamp)}"
        )

        urls = []

        with Session() as s:
            s.auth = (_USER, _PASSWORD)
            while True:
                if len(urls) > 0:
                    print("Sleeping", flush=True)
                    time.sleep(10)

                urls.append(next_url)
                # Break if same URL is requested for 5 times in a row
                if len(urls) > 5 and len(Counter(urls[-5:])) == 1:
                    print("Stopped making request to zendesk after consecutive errors")
                    break
                r = ZendeskManager._rate_limited_get(s, next_url)
                j = json.loads(r.text)
                try:
                    if "error" in j:
                        raise Exception("Error returned from Zendesk")

                    for ticket_json in j["tickets"]:
                        ticket_json.update({"attachments": []})
                        test_doc = ZendeskDocument.deserialize_from_external_json(ticket_json)
                        # This is a speedup measure, don't bother downloading attachments
                        # for otherwise invalid documents.
                        if not ZendeskDocument.check_should_index_document(test_doc):
                            continue

                        attachments = []

                        # Only download attachments for beta feedback items until
                        # we figure out a faster way to do this
                        if test_doc.shake_to_report_category.name == "EXTERNAL":
                            ticket_id = ticket_json["id"]
                            comments_url = (
                                f"{zendesk_host}/api/v2/tickets/{ticket_id}/comments.json"
                            )
                            comments_response = ZendeskManager._rate_limited_get(s, comments_url)
                            comments_structure = json.loads(comments_response.text)
                            for com in comments_structure.get("comments", {}):
                                for attach in com.get("attachments", {}):
                                    attachments.append(attach["content_url"])

                        ticket_json["attachments"] = attachments

                        yield ZendeskDocument.deserialize_from_external_json(ticket_json)

                    if j["end_time"]:
                        print(
                            f"Downloaded {len(j['tickets'])} tickets until: {datetime_to_str(datetime.fromtimestamp(j['end_time']))}"
                        )

                    if j["next_page"]:
                        next_url = j["next_page"]

                    if j["count"] < 1000:
                        break

                except Exception as e:
                    print(
                        f"""
                        Exception happened for URL: {next_url}
                        Status code: {r.status_code}
                        Returned headers: {r.headers}
                        Returned body: {r.text}
                        """
                    )
                    # If we exceeded a rate limit, we should just wait and try again.
                    if r.status_code == 429 and "Retry-After" in r.headers:
                        print("Exception was due to rate-limiting. Sleeping.")
                        time.sleep(int(r.headers["Retry-After"]))
                        continue
                    # If something non-recoverable has happened, escalate.
                    raise (e)

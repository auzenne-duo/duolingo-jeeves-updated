"""
Manager for Zendesk documents.
"""


from collections import Counter
from datetime import datetime
import json
import os
import time
from typing import Iterator, Type

from requests import Session

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
                r = s.get(next_url)
                j = json.loads(r.text)
                try:
                    if "error" in j:
                        raise Exception("Error returned from Zendesk")

                    for ticket_json in j["tickets"]:
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
                        Returned JSON: {r.text}
                        """
                    )
                    raise (e)

"""
Our model for a ticket from the Zendesk API
"""
from collections import Counter
from datetime import datetime
import json
import os
import time
from typing import List

import attr
import requests

from jeeves.model.custom_types import JSON
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.products import Products
from jeeves.util.classify import detect_language, detect_product
from jeeves.util.cleanup import clean_and_parse_description
from jeeves.util.date_util import datetime_to_str, parse_external_datetime


@attr.s(kw_only=True)
class ZendeskDocument(JeevesDocument):

    product: str = attr.ib()
    priority: str = attr.ib()
    via: JSON = attr.ib()
    tags: List[str] = attr.ib()
    requester_id: str = attr.ib()
    metadata: JSON = attr.ib()

    @staticmethod
    def get_data_source_identifier():
        """
        Please see parent class for documentation
        """
        return "Zendesk"

    @classmethod
    def deserialize_from_external_json(cls, external_json: JSON) -> JeevesDocument:
        """
        Please see parent class for documentation
        """

        body, metadata = clean_and_parse_description(external_json["description"])
        header = external_json["subject"] if external_json["subject"] else ""

        link_url_base = "https://duolingotest.zendesk.com/agent"
        ticket_link = f"{link_url_base}/tickets/{external_json['id']}"
        user_link = f"{link_url_base}/users/{external_json['requester_id']}"

        return cls(
            data_source=cls.get_data_source_identifier(),
            document_id=str(external_json["id"]),
            date_time=parse_external_datetime(external_json["created_at"]),
            header_text=header,
            body_text=body,
            language=detect_language(body),
            links=[ticket_link, user_link],
            product=detect_product(external_json["tags"], header).name,
            priority=external_json["priority"],
            via=external_json["via"],
            tags=external_json["tags"],
            requester_id=external_json["requester_id"],
            metadata=metadata,
        )

    @classmethod
    def deserialize_from_internal_json(cls, internal_json: JSON) -> JeevesDocument:
        """
        Please see parent class for documentation
        """
        header = internal_json["header_text"] if internal_json["header_text"] else ""

        return cls(
            data_source=internal_json["data_source"],
            document_id=internal_json["document_id"],
            date_time=internal_json["date_time"],
            header_text=header,
            body_text=internal_json["body_text"],
            language=internal_json["language"],
            links=internal_json["links"],
            product=internal_json["product"],
            priority=internal_json["priority"],
            via=internal_json["via"],
            tags=internal_json["tags"],
            requester_id=internal_json["requester_id"],
            metadata=internal_json["metadata"],
        )

    @classmethod
    def check_should_index_document(cls, document: JeevesDocument) -> bool:
        """
        Please see parent class for documentation
        """
        if not super().check_should_index_document(document):
            return False

        # Ignore tickets sent BY the following emails
        _SENDERS_TO_IGNORE = {"no-reply@duolingo.com", "community@duolingo.com"}
        # Also ignore tickets sent TO the following emails
        _RECEIVERS_TO_IGNORE = {
            "luis@duolingotest.zendesk.com",
            "luis@duolingo.com",
            "institution@testcenter.zendesk.com",
            "testcenter-support@duolingo.com",
        }
        # Also also ignore tickets with one or more of the following tags
        _TAGS_TO_IGNORE = {"duolingo_english_test___appeal_results"}

        if document.via["channel"] == "chat":
            return False

        # Ignore a ticket if a sender email is on a blocklist
        from_data = document.via["source"]["from"]
        if from_data and "address" in from_data and from_data["address"] in _SENDERS_TO_IGNORE:
            return False

        # Ignore a ticket if receiving email is on a blocklist
        to_data = document.via["source"]["to"]
        if to_data and "address" in to_data and to_data["address"] in _RECEIVERS_TO_IGNORE:
            return False

        tag_data = document.tags
        if tag_data and set(tag_data) & _TAGS_TO_IGNORE:
            return False

        # Skip tickets that have an empty string ('') description
        # after cleanup, which are those that consist of just
        # punctuation/spacing after cleanup
        if not document.body_text:
            return False

        if document.product != Products.LA.name:
            return False

        return True

    @classmethod
    def download_external_documents(cls, start_timestamp):
        """
        Please see parent class for documentation
        """
        _ZENDESK_HOST = "https://duolingotest.zendesk.com"

        _USER = os.environ.get("ZENDESK_USER")
        _PASSWORD = os.environ.get("ZENDESK_PASSWORD")

        next_url = (
            f"{_ZENDESK_HOST}/api/v2/incremental/tickets.json?start_time={int(start_timestamp)}"
        )

        urls = []
        while True:
            if len(urls) > 0:
                print("Sleeping", flush=True)
                time.sleep(10)

            urls.append(next_url)
            # Break if same URL is requested for 5 times in a row
            if len(urls) > 5 and len(Counter(urls[-5:])) == 1:
                print("Stopped making request to zendesk after consecutive errors")
                break
            r = requests.get(next_url, auth=(_USER, _PASSWORD))
            j = json.loads(r.text)
            try:
                if "error" in j:
                    raise Exception("Error returned from Zendesk")

                for ticket_json in j["tickets"]:
                    yield cls.deserialize_from_external_json(ticket_json)

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

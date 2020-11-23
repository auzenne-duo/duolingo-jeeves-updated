"""
Manager for Appfigures documents.
"""


from datetime import datetime
import json
import os
from typing import Iterator

from requests import Session
from requests.exceptions import RequestException

from jeeves.manager.jeeves_manager import JeevesManager
from jeeves.model.appfigures_document import AppfiguresDocument
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.util.error_util import print_request_exception

_USER = os.environ.get("APPFIGURES_USER")
_PASSWORD = os.environ.get("APPFIGURES_PASSWORD")
_CLIENT_KEY = os.environ.get("APPFIGURES_CLIENT_KEY")


class AppfiguresManager(JeevesManager):
    @staticmethod
    def get_managed_document_type():
        """
        Please see parent class for documentation
        """
        return AppfiguresDocument

    @staticmethod
    def download_documents(start_timestamp: float) -> Iterator[JeevesDocument]:
        """
        Please see parent class for documentation
        """

        appfigures_host = "https://api.appfigures.com"

        special_headers = {"X-Client-Key": _CLIENT_KEY}

        url_params = {
            "start": f"{datetime.utcfromtimestamp(start_timestamp).date()}",
            "sort": "date",
            "count": "500",
            "page": "1",
        }

        template_url = f"{appfigures_host}/v2/reviews"

        r = None
        with Session() as s:
            s.auth = (_USER, _PASSWORD)
            s.headers.update(special_headers)
            while True:
                print(f"Downloading reviews from AppFigures: {url_params}")
                try:
                    r = s.get(template_url, params=url_params)

                    r.raise_for_status()

                    j = json.loads(r.text)

                    for review_json in j["reviews"]:
                        yield AppfiguresDocument.deserialize_from_external_json(review_json)

                    if j["pages"] == j["this_page"]:
                        break

                    next_page = j["this_page"] + 1
                    url_params.update({"page": f"{next_page}"})

                except RequestException as e:
                    print_request_exception(e)
                    break

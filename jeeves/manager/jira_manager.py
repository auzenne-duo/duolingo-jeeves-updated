"""
Manager for JIRA documents.
"""

import json
import os
from typing import Iterator

from requests import Session
from requests.auth import HTTPBasicAuth
from requests.exceptions import RequestException

from jeeves.manager.jeeves_manager import JeevesManager
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.jira_document import JiraDocument

_USERNAME = os.environ.get("JIRA_USERNAME")
_API_TOKEN = os.environ.get("JIRA_API_TOKEN")


class JiraManager(JeevesManager):
    @staticmethod
    def get_managed_document_type():
        """
        Please see parent class for documentation
        """
        return JiraDocument

    @staticmethod
    def download_documents(start_timestamp: float) -> Iterator[JeevesDocument]:
        """
        Please see parent class for documentation
        """

        start_timestamp_millis = int(start_timestamp * 1000)

        jira_host = "https://duolingo.atlassian.net"

        template_url = f"{jira_host}/rest/api/3/search"

        headers = {"Accept": "application/json"}

        # This is apparently a restriction of the JIRA API; trying to get more
        # than 1000 issues at a time will only return the first 1000.
        max_issues_per_fetch = 1000

        projects_to_fetch = ["DLAA", "DLAI", "DLAW"]
        projects_fetch_string = f"project IN ({','.join(projects_to_fetch)}) AND updated > {start_timestamp_millis} ORDER BY updated asc"

        url_params = {"maxResults": 0, "startAt": 0, "jql": projects_fetch_string}

        r = None
        with Session() as s:
            s.auth = HTTPBasicAuth(_USERNAME, _API_TOKEN)
            s.headers = headers
            try:
                # This call is just to make sure we don't download more issues than are available.
                r = s.get(template_url, params=url_params)
                r.raise_for_status()
                response_JSON = json.loads(r.text)
                url_params["maxResults"] = min(max_issues_per_fetch, response_JSON["total"])

                while url_params["startAt"] < response_JSON["total"]:

                    r = s.get(template_url, params=url_params)
                    r.raise_for_status()

                    response_JSON = json.loads(r.text)
                    yield from [
                        JiraDocument.deserialize_from_external_json(issue)
                        for issue in response_JSON["issues"]
                    ]

                    url_params["startAt"] += len(response_JSON["issues"])

            except RequestException as e:
                print(
                    f"""
                    An exception occurred for the following request:
                    {e.request}
                    The above request generated the following response:
                    {e.response}
                    """
                )

            except Exception as e:
                print(e)

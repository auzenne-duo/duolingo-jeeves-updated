"""
Manager for JIRA documents.
"""

import json
import os
from typing import Iterator, Optional

from requests import get, Session
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
                response_json = json.loads(r.text)
                url_params["maxResults"] = min(max_issues_per_fetch, response_json["total"])

                while url_params["startAt"] < response_json["total"]:

                    r = s.get(template_url, params=url_params)
                    r.raise_for_status()

                    response_json = json.loads(r.text)
                    yield from [
                        JiraDocument.deserialize_from_external_json(issue)
                        for issue in response_json["issues"]
                    ]

                    url_params["startAt"] += len(response_json["issues"])

            except RequestException as e:
                print(
                    f"""
                    An exception occurred for the following request:
                    {e.request}
                    The above request generated the following response:
                    {e.response}
                    """
                )

    @staticmethod
    def download_specific_issue(issue_key: str) -> Optional[JeevesDocument]:
        """
        Performs a one-off download of a specific issue with the given issue key.
        It is assumed but not required that Jeeves does not already have the
        requested document. It is also assumed but not required that the document
        in question exists in JIRA.

        Parameters:
            issue_key: Issue key of the issue we wish to download.

        Returns:
            A JeevesDocument object representing the requested issue if we were
            able to download it, and None otherwise.
        """

        base_api_url = "https://duolingo.atlassian.net/rest/api/3/issue"
        headers = {"Accept": "application/json"}
        auth = HTTPBasicAuth(_USERNAME, _API_TOKEN)

        request_url = f"{base_api_url}/{issue_key}"

        try:
            r = get(request_url, auth=auth, headers=headers)
            r.raise_for_status()

            response_JSON = json.loads(r.text)
            return JiraDocument.deserialize_from_external_json(response_JSON)

        except RequestException as e:
            print(
                f"""
                An exception occurred for the following request:
                {e.request}
                The above request generated the following response:
                {e.response}

                The requested record could not be found, returning None.
                """
            )
            return None

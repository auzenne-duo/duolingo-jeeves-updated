"""
Manager for JIRA documents.
"""

import json
import os
from typing import Iterator, Optional

from requests import get, post, Session
from requests.auth import HTTPBasicAuth
from requests.exceptions import RequestException

from jeeves.manager.jeeves_manager import JeevesManager
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.jira_document import JiraDocument
from jeeves.util.error_util import print_request_exception

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
        projects_fetch_string = f"project IN ({','.join(projects_to_fetch)}) AND updated > {start_timestamp_millis} AND issueType = Bug ORDER BY updated asc"

        url_params = {"fields": "*all", "maxResults": 0, "startAt": 0, "jql": projects_fetch_string}

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
                    for issue in response_json["issues"]:
                        attachments = []

                        if "attachment" in issue["fields"]:
                            for attachment_json in issue["fields"]["attachment"]:
                                attachments.append(attachment_json["content"])

                        issue["attachments"] = attachments
                        yield JiraDocument.deserialize_from_external_json(issue)

                    url_params["startAt"] += len(response_json["issues"])

            except RequestException as e:
                print_request_exception(e)

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
            print_request_exception(e)
            return None

    @staticmethod
    def mark_duplicate_remote(outward_key: str, inward_key: str) -> bool:
        """
        Given two issue keys, one outward and one inward, marks them as
        duplicates of each other on JIRA. We distinguish between outward and
        inward here because JIRA's architecture does not consider the relation
        to be symmetric. To my knowledge, all other parts of Jeeves discard
        this directionality information and treat the relationship as though
        it were symmetric, so flipping the order of the parameters here should
        not matter.

        Parameters:
            outward_key: Issue key on the "outward" side of the duplicate link.
            inward_key: Issue key on the "inward" side of the duplicate link.

        Returns:
            True if the link is created, otherwise False. This is actually as
            informative of a return value as we're able to provide. JIRA's API
            has three failure response codes on the relevant route, those being
            400 (comment not created), 401 (Unauthorized), and 404 (Other). We
            are not using comments here so 400 will never be returned. The
            credentials used here are identical to those used on other JIRA API
            functionality in this file, so if this request would generate a 401,
            so would a lot of other, much more visible requests. That only
            leaves 404 as a failure condition, and JIRA explicitly states that
            they do not define a response schema for 404 on this route. As a
            result, we do not have any information beyond "the request failed".

        Note: We do not need to explicitly update Elasticsearch with the link
              created in this function, since creating the duplicate relation
              should trigger an update on both of the issues, which will be
              later picked up by the normal document downloader.
        """

        issue_link_url = "https://duolingo.atlassian.net/rest/api/3/issueLink"
        auth = HTTPBasicAuth(_USERNAME, _API_TOKEN)
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        data = {
            "outwardIssue": {"key": outward_key},
            "inwardIssue": {"key": inward_key},
            "type": {"name": "Duplicate"},
        }

        try:
            r = post(issue_link_url, auth=auth, headers=headers, data=json.dumps(data))
            r.raise_for_status()
        except RequestException as e:
            print_request_exception(e)
            return False

        return True

    @staticmethod
    def close_as_duplicate(issue_key: str) -> bool:
        """
        Closes the specified issue as a duplicate
        """
        url = f"https://duolingo.atlassian.net/rest/api/3/issue/{issue_key}/transitions"
        auth = HTTPBasicAuth(_USERNAME, _API_TOKEN)
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        data = {
            # This is the close transition ID for a bug issue type. Since Shakira only creates bugs, this is fine.
            "transition": {"id": "251"},
            "fields": {"resolution": {"name": "Duplicate"}},
        }
        try:
            r = post(url, auth=auth, headers=headers, data=json.dumps(data))
            r.raise_for_status()

        except RequestException as e:
            print_request_exception(e)
            return False

        return True

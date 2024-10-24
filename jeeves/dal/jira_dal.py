import asyncio
import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from timeit import default_timer
from typing import Dict, Iterable, Iterator, List, Optional, Tuple, Union

import duo_logging
from requests import RequestException, Response, Session, delete, get, post, put
from requests.auth import HTTPBasicAuth

from jeeves.lib.profiling import traced_function
from jeeves.model.custom_types import JSON
from jeeves.model.jira_document import PARENT_BUG_LABEL, JiraDocument
from jeeves.model.jira_issue_metadata import JiraIssueTypeMetaData
from jeeves.util.async_util import get_asyncio_loop
from jeeves.util.error_util import print_request_exception

_USERNAME = os.environ.get("JIRA_USERNAME")
_API_TOKEN = os.environ.get("JIRA_API_TOKEN")

_RETRY_LIMIT = 3


class JiraApiDAL:
    def __init__(self):
        self._host = "https://duolingo.atlassian.net"
        self._auth = HTTPBasicAuth(_USERNAME, _API_TOKEN)

    def _get_with_retry(self, url, headers=None, params=None, auth=None) -> Response:
        for _ in range(_RETRY_LIMIT):
            try:
                # TODO investigate using a Retry object with the requests library
                # https://github.com/duolingo/duolingo-jeeves/pull/531#discussion_r974582983
                r = get(url, headers=headers, params=params, auth=auth)
                r.raise_for_status()
                return r
            except RequestException as e:
                if e.response.status_code == 429 and "Retry-After" in r.headers:
                    delay = int(r.headers["Retry-After"])
                    print(f"Retrying request to {url} after {delay} seconds")
                    time.sleep(delay)
                    continue
                print_request_exception(e)
                raise

    def get_issuetype_metadata(self, projects, issue_types) -> List[JiraIssueTypeMetaData]:
        """
        Get metadata about the requested issue types.

        Parameters:
            projects: project keys of the projects to look at.
            issue_types: names of the issue types that we want metadata for.

        Returns:
            A list of JiraIssueTypeMetaData for each issue type requested.
        """
        # copied from shakira_jira, because I didn't want to tie the code together
        url = self._host + "/rest/api/2/issue/createmeta"
        headers = {"Accept": "application/json"}
        params = {
            "expand": "projects.issuetypes.fields",
            "projectKeys": projects,
            "issuetypeNames": issue_types,
        }

        r = self._get_with_retry(url, headers=headers, params=params, auth=self._auth)
        response_json = json.loads(r.text)
        return [
            JiraIssueTypeMetaData.from_json(issuetype)
            for project in response_json["projects"]
            for issuetype in project["issuetypes"]
        ]

    def get_feature_for_jira_document(self, doc: JiraDocument) -> str:
        """
        Get the most up-to-date name of the JiraDocument's feature according to Jira.
        """
        url = doc.feature_url
        if url is None or len(url) == 0:
            return None

        headers = {"Accept": "application/json"}

        try:
            r = self._get_with_retry(url, headers=headers, auth=self._auth)
            response_json = json.loads(r.text)
            return response_json["value"]
        except RequestException as e:
            status_code = e.response.status_code if e.response is not None else None
            reason = e.response.reason if e.response is not None else None

            duo_logging.capture_message(
                f"Feature url {url} returned {status_code} {reason}. Falling back to feature {doc.feature}",
                "warning",
            )
            return doc.feature

    def _get_attachment_url(self, attachment_json: JSON) -> str:
        # YK 2022-02-25 This is a hack to get a URL that has a file extension at the end of it but
        # I don't think this URL is part of the official API so it might suddenly stop working.
        # Ideally we should store attachments in our own S3 (DEL-852).
        return f"https://duolingo.atlassian.net/secure/attachment/{attachment_json['id']}/{attachment_json['filename']}"

    def search_issues_json(self, s: Session, params: Dict[str, Union[int, str]]) -> JSON:
        """
        Perform a search for Jira issues and return the response JSON.

        Parameters:
            s: A Session object; can be shared across calls to this method.
            params: The query params to be sent to the API.

        Returns:
            The full JSON returned by the API, with some custom modification.
        """

        def _add_attachments_to_issue_json(json: Dict) -> Dict:
            """
            An object hook method for the json.loads method that sets the attachments field to
            issue JSON only.
            """
            if "fields" not in json:
                # we're not looking at an issue dictionary, don't modify the dict.
                return json

            issue = json.copy()
            attachments = []
            if "attachment" in issue["fields"]:
                for attachment_json in issue["fields"]["attachment"]:
                    attachments.append(self._get_attachment_url(attachment_json))
            issue["attachments"] = attachments
            return issue

        url = self._host + "/rest/api/3/search"
        s.auth = self._auth
        s.headers = {"Accept": "application/json"}

        try:
            r = s.get(url, params=params)
            r.raise_for_status()

            response_json = json.loads(r.text, object_hook=_add_attachments_to_issue_json)
            return response_json
        except RequestException as e:
            print_request_exception(e, log_level="error")
            raise

    def paginate_search_issues(self, url_params) -> Iterator[JSON]:
        """
        Executes a jira search with url_params and yields issues
        """
        # copy the params input since we will updating "startAt" field
        url_params = url_params.copy()
        total = None
        with Session() as s:
            while total is None or url_params["startAt"] < total:
                response_json = self.search_issues_json(s, params=url_params)
                yield from response_json["issues"]
                url_params["startAt"] += len(response_json["issues"])
                if len(response_json["issues"]) == 0:
                    break
                if total is None:
                    # only update total once, rather than trying to hit a moving target of total
                    # issues downloaded.
                    total = response_json["total"]

    @traced_function()
    def get_bulk_issues(self, issue_keys: List[str]) -> List[JiraDocument]:
        """
        Downloads issues as JiraDocuments.
        """
        docs = []
        # Download JiraDocuments in chunks to avoid too long of urls
        slice_size = 20
        for i in range(0, len(issue_keys), slice_size):
            url = (
                self._host
                + f"/rest/api/3/search?jql=key%20in%20({',%20'.join(issue_keys[i:i+slice_size])})"
            )
            headers = {"Accept": "application/json"}
            response_json = json.loads(self.make_jira_get(url, headers))
            docs.extend(
                [
                    JiraDocument.deserialize_from_external_json(issue)
                    for issue in response_json["issues"]
                ]
            )
        return docs

    def get_issue(self, issue_key: str) -> JiraDocument:
        """
        Download a particular issue as a JiraDocument.
        """
        url = self._host + "/rest/api/3/issue/" + issue_key
        headers = {"Accept": "application/json"}
        # TODO warning if JiraDocument._feature_field_key is not set!
        return JiraDocument.deserialize_from_external_json(
            json.loads(self.make_jira_get(url, headers))
        )

    def get_attachment_contents(self, attachment_key: str) -> str:
        """
        Downloads the contents of a specific attachment
        """
        url = self._host + "/rest/api/3/attachment/content/" + attachment_key
        headers = {"Accept": "application/json"}
        return self.make_jira_get(url, headers)

    def make_jira_get(self, url: str, headers: Dict):
        """
        Performs a get request
        """
        try:
            r = get(url, auth=self._auth, headers=headers)
            r.raise_for_status()
            return r.text
        except RequestException as e:
            print_request_exception(e, log_level="error")
            raise

    def update_issue(
        self,
        issue_key: str,
        summary: Optional[str] = None,
        description: Optional[JSON] = None,
        remove_parent_bug_label: bool = False,
        feature: Optional[str] = None,
        priority: Optional[str] = None,
    ) -> None:
        """
        Update the issue's fields.
        """
        url = self._host + "/rest/api/3/issue/" + issue_key
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        update_dict = {}
        fields_dict = {}
        if summary:
            update_dict["summary"] = [{"set": summary}]
        if description:
            update_dict["description"] = [{"set": description}]
        if remove_parent_bug_label:
            update_dict["labels"] = [{"remove": PARENT_BUG_LABEL}]
        if feature:
            feature_field_key = JiraDocument.get_feature_field_key()
            if feature_field_key:
                fields_dict[feature_field_key] = {"value": feature}
        if priority:
            update_dict["priority"] = [{"set": {"name": priority}}]

        data_operation = {"update": update_dict, "fields": fields_dict}
        try:
            r = put(url, headers=headers, auth=self._auth, data=json.dumps(data_operation))
            r.raise_for_status()
        except RequestException as e:
            print_request_exception(e, log_level="error")
            raise

    def close_issue_as_duplicate(self, issue_key: str):
        """
        Close the issue with the Duplicate resolution
        """
        url = self._host + f"/rest/api/3/issue/{issue_key}/transitions"
        headers = {"Accept": "application/json", "Content-Type": "application/json"}

        data_operation = {
            "transition": {"id": 251},
            "fields": {"resolution": {"name": "Duplicate"}},
        }

        try:
            r = post(url, headers=headers, auth=self._auth, data=json.dumps(data_operation))
            r.raise_for_status()
        except RequestException as e:
            print_request_exception(e, log_level="error")
            raise

    def create_bug_issue(self, project: str, summary: str, description_json: JSON) -> str:
        """
        Creates a new issue with the given parameters as a Bug issuetype.

        Parameters:
            project: the key of the project to create the issue in.
            summary: the bug summary/header.
            description_json: JSON defining the description field of the issue.

        Returns:
            The issue key of the created issue.
        """
        url = self._host + "/rest/api/3/issue/"
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        issue_data = {
            "fields": {
                "project": {
                    "key": project,
                },
                "issuetype": {
                    "name": "Bug",
                },
                "summary": summary,
                "description": description_json,
                "labels": [
                    PARENT_BUG_LABEL,
                ],
            }
        }

        try:
            r = post(url, auth=self._auth, headers=headers, data=json.dumps(issue_data))
            r.raise_for_status()

            response_JSON = json.loads(r.text)
            return response_JSON["key"]
        except RequestException as e:
            print_request_exception(e, log_level="error")
            raise

    @traced_function()
    def mark_duplicate(self, outward_key: str, inward_key: str):
        """
        Given two issue keys, one outward and one inward, marks them as
        duplicates of each other on JIRA.

        Parameters:
            outward_key: Issue key on the "outward" side of the duplicate link.
            inward_key: Issue key on the "inward" side of the duplicate link.

        Returns:
            True if the link is created, otherwise False.
        """
        url = self._host + "/rest/api/3/issueLink"
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        data = {
            "outwardIssue": {"key": outward_key},
            "inwardIssue": {"key": inward_key},
            "type": {"name": "Duplicate"},
        }

        try:
            r = post(url, auth=self._auth, headers=headers, data=json.dumps(data))
            r.raise_for_status()
        except RequestException as e:
            print_request_exception(e, log_level="error")
            return (outward_key, inward_key, False)
        return (outward_key, inward_key, True)

    async def mark_duplicates_async(
        self, links: List[Tuple[str, str]]
    ) -> List[Tuple[str, str, bool]]:
        results = []
        with ThreadPoolExecutor(max_workers=10) as executor:
            loop = get_asyncio_loop()
            default_timer()
            tasks = [
                loop.run_in_executor(
                    executor,
                    self.mark_duplicate,
                    *(outward_key, inward_key),
                )
                for outward_key, inward_key in links
            ]
            for response in await asyncio.gather(*tasks):
                results.append(response)
        return results

    @traced_function()
    def delete_link(self, link_id: str):
        """
        Given a link ID, delete the link from JIRA.

        Parameters:
            link_id: ID of the link to delete.

        Returns:
            True if the link is deleted, otherwise False.
        """
        url = self._host + f"/rest/api/3/issueLink/{link_id}"
        headers = {"Accept": "application/json"}

        try:
            r = delete(url, auth=self._auth, headers=headers)
            r.raise_for_status()
        except RequestException as e:
            print_request_exception(e, log_level="error")
            return (link_id, False)
        return (link_id, True)

    async def delete_links_async(self, link_ids: Iterable[str]) -> List[Tuple[str, bool]]:
        results = []
        # NOTE: The curious reviewer may wonder why we're combining ThreadPoolExecutor with asyncio.
        # The reason is that the requests library is not async-compatible, so we need to put each request
        # in its own thread to avoid blocking the event loop. At that point, one might ask why we're using
        # asyncio at all. I went along with it because it appeared to be the standard in this codebase.
        # It would probably be worth switching to aiohttp in the near future.
        with ThreadPoolExecutor(max_workers=10) as executor:
            loop = get_asyncio_loop()
            default_timer()
            tasks = [
                loop.run_in_executor(
                    executor,
                    self.delete_link,
                    link_id,
                )
                for link_id in link_ids
            ]
            for response in await asyncio.gather(*tasks, return_exceptions=True):
                results.append(response)
        return results


JiraDAL = JiraApiDAL()

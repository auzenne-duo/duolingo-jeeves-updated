import json
import os
from typing import Dict, List, Union

from requests import RequestException, Session, get, post, put
from requests.auth import HTTPBasicAuth

from jeeves.model.custom_types import JSON
from jeeves.model.jira_document import JiraDocument
from jeeves.model.jira_issue_metadata import JiraIssueTypeMetaData
from jeeves.util.error_util import print_request_exception

_USERNAME = os.environ.get("JIRA_USERNAME")
_API_TOKEN = os.environ.get("JIRA_API_TOKEN")


class JiraApiDAL:
    def __init__(self):
        self._host = "https://duolingo.atlassian.net"
        self._auth = HTTPBasicAuth(_USERNAME, _API_TOKEN)

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

        try:
            r = get(url, auth=self._auth, headers=headers, params=params)
            r.raise_for_status()

            response_json = json.loads(r.text)
            return [
                JiraIssueTypeMetaData.from_json(issuetype)
                for project in response_json["projects"]
                for issuetype in project["issuetypes"]
            ]
        except RequestException as e:
            print_request_exception(e)
            raise

    def get_feature_for_jira_document(self, doc: JiraDocument) -> str:
        """
        Get the most up-to-date name of the JiraDocument's feature according to Jira.
        """
        url = doc.feature_url
        if url is None or len(url) == 0:
            return None

        headers = {"Accept": "application/json"}

        try:
            r = get(url, auth=self._auth, headers=headers)
            r.raise_for_status()

            response_json = json.loads(r.text)
            return response_json["value"]
        except RequestException as e:
            print_request_exception(e)
            raise

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
            print_request_exception(e)
            raise

    def get_issue(self, issue_key: str) -> JiraDocument:
        """
        Download a particular issue as a JiraDocument.
        """
        url = self._host + "/rest/api/3/issue/" + issue_key
        headers = {"Accept": "application/json"}

        try:
            r = get(url, auth=self._auth, headers=headers)
            r.raise_for_status()

            response_json = json.loads(r.text)
            # TODO warning if JiraDocument._feature_field_key is not set!
            return JiraDocument.deserialize_from_external_json(response_json)
        except RequestException as e:
            print_request_exception(e)
            raise

    def set_issue_description(self, issue_key: str, description: str):
        """
        Replace the issue's description with the given string.
        """
        url = self._host + "/rest/api/3/issue/" + issue_key
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        data_operation = {"update": {"description": [{"set": description}]}}

        try:
            r = put(url, headers=headers, auth=self._auth, data=json.dumps(data_operation))
            r.raise_for_status()
        except RequestException as e:
            print_request_exception(e)
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
                    "parent_bug",
                ],
            }
        }

        try:
            r = post(url, auth=self._auth, headers=headers, data=json.dumps(issue_data))
            r.raise_for_status()

            response_JSON = json.loads(r.text)
            return response_JSON["key"]
        except RequestException as e:
            print_request_exception(e)
            raise

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
            print_request_exception(e)
            raise


JiraDAL = JiraApiDAL()

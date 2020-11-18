"""
DAL for interacting with the JIRA API for shakira.
"""

import os
import json
from typing import Set, Dict, Optional, Union, List
from requests import get, post
from requests.auth import HTTPBasicAuth
from requests.exceptions import RequestException

from jeeves.model.jira_issue_metadata import JiraIssueTypeMetaData
from jeeves.util.error_util import print_request_exception

_API = "https://duolingo.atlassian.net/rest/api/2"
_USERNAME = os.environ.get("SHAKIRA_JIRA_USERNAME")
_API_TOKEN = os.environ.get("SHAKIRA_JIRA_API_TOKEN")

_ISSUE_TYPE_BUG = "Bug"
_ISSUE_TYPE_STORY = "Story"
_ALL_ISSUE_TYPES = [_ISSUE_TYPE_BUG, _ISSUE_TYPE_STORY]


class ShakiraApiDAL:
    def _get_metadata_url_and_params(self, project: str, issue_types: Union[str, List]) -> str:
        url = f"{_API}/issue/createmeta"
        params = {
            "expand": "projects.issuetypes.fields",
            "projectKeys": project,
            "issuetypeNames": issue_types,
        }
        return (url, params)

    def get_features(self, project: str) -> Set[str]:
        """
        Get possible values for the "Feature" issue field in a project.

        parameters
            project: e.g. DLAA, DLAI
        """
        url, params = self._get_metadata_url_and_params(project, _ALL_ISSUE_TYPES)
        headers = {"Accept": "application/json"}
        auth = HTTPBasicAuth(_USERNAME, _API_TOKEN)
        try:
            r = get(url, auth=auth, headers=headers, params=params)
            r.raise_for_status()

            response_json = json.loads(r.text)
            if len(response_json["projects"]) > 0:
                issuetypes = [
                    JiraIssueTypeMetaData.from_json(issuetype)
                    for issuetype in response_json["projects"][0]["issuetypes"]
                ]
                return [
                    name for issuetype in issuetypes for name in issuetype.allowed_feature_values()
                ]
        except RequestException as e:
            print_request_exception(e)
            return None

    def _get_metadata_for_specific_issuetype(
        self, project, issuetype: str
    ) -> Optional[JiraIssueTypeMetaData]:
        url, params = self._get_metadata_url_and_params(project, issuetype)
        headers = {"Accept": "application/json"}
        auth = HTTPBasicAuth(_USERNAME, _API_TOKEN)
        try:
            r = get(url, auth=auth, headers=headers, params=params)
            r.raise_for_status()
            response_json = json.loads(r.text)
            if len(response_json["projects"]) > 0:
                issuetypes = response_json["projects"][0]["issuetypes"]
                if len(issuetypes) > 0:
                    return JiraIssueTypeMetaData.from_json(issuetypes[0])
            return None
        except RequestException as e:
            print_request_exception(e)
            return None

    def _get_id_for_user(self, email: str) -> Optional[str]:
        url = f"{_API}/user/search"
        params = {"query": email}
        headers = {"Accept": "application/json"}
        auth = HTTPBasicAuth(_USERNAME, _API_TOKEN)
        try:
            r = get(url, auth=auth, headers=headers, params=params)
            r.raise_for_status()
            response_json = json.loads(r.text)
            return response_json[0]["accountId"] if len(response_json) > 0 else None
        except RequestException as e:
            print_request_exception(e)
            return None

    def create_issue(
        self,
        project: str,
        feature: str,
        summary,
        description: str,
        generated_description: str,
        reporter_email: Optional[str],
        pre_release: bool,
    ) -> Optional[str]:
        """
        Create an issue in JIRA.
        For reference: https://docs.atlassian.com/software/jira/docs/api/REST/8.13.1/#api/2/issue

        parameters:
            project: e.g. DLAI, DLAA
            feature: e.g. Achievements
            summary: ~One sentence summary of issue.
            description: Longer issue description.
            generated_description: Generated information such as app version, fullstory url, session type, etc.
            reporter_emai: Email of the duo reporting the issue.
            pre_release: Whether the bug is being reported from pre-release app version.

        returns:
            issue key: str e.g. DLAA-2508

        """
        # If user selected "Feature request / feedback" then we want to create a "Story" instead of a "Bug"
        # Generalize to any name containing "request" in case we change the names.
        if "request" in feature.lower():
            issuetype = self._get_metadata_for_specific_issuetype(project, _ISSUE_TYPE_STORY)
        else:
            issuetype = self._get_metadata_for_specific_issuetype(project, _ISSUE_TYPE_BUG)

        if issuetype:
            fields = {
                "project": {"key": project},
                "summary": summary,
                "description": f"{description}\n{generated_description}",
                "issuetype": {"id": issuetype.id},
            }

            feature_field_key = issuetype.feature_field_key()
            feature_value_id = issuetype.get_id_for_allowed_feature_value(feature)
            if feature_field_key and feature_value_id:
                fields[feature_field_key] = {"id": feature_value_id}

            labels = []

            reporter_id = None
            if reporter_email:
                reporter_id = self._get_id_for_user(reporter_email)
            if reporter_id:
                fields["reporter"] = {"id": reporter_id}
            else:
                labels.append("bug-triage")

            if pre_release:
                labels.append("rc-shakira")

            if len(labels) > 0:
                fields["labels"] = labels

            request = {"fields": fields}
            url = f"{_API}/issue"
            headers = {"Content-Type": "application/json"}
            auth = HTTPBasicAuth(_USERNAME, _API_TOKEN)
            try:
                r = post(url, auth=auth, headers=headers, data=json.dumps(request))
                r.raise_for_status()
                response_json = json.loads(r.text)
                return response_json["key"]
            except RequestException as e:
                print_request_exception(e)
                return None

    def upload_attachments(self, issue_key: str, files: Dict):
        """
        Upload attachment to JIRA issue with key issue_key
        For reference: https://docs.atlassian.com/software/jira/docs/api/REST/8.13.1/#api/2/issue/{issueIdOrKey}/attachments

        parameters:
            issue_key: JIRA issue to upload attachments to e.g. DLAA-5690
            files: MultiDict of form name to file

        """
        url = f"{_API}/issue/{issue_key}/attachments"
        headers = {"X-Atlassian-Token": "no-check"}  # header required by JIRA API
        auth = HTTPBasicAuth(_USERNAME, _API_TOKEN)
        jira_files = [
            ("file", f) for f in files.values()
        ]  # The JIRA API requires every file to have the form name 'file'
        try:
            r = post(url, auth=auth, headers=headers, files=jira_files)
            r.raise_for_status()
        except RequestException as e:
            print_request_exception(e)


ShakiraDAL = ShakiraApiDAL()

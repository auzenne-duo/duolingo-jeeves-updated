"""
Manager for interacting with the JIRA API for shakira.
"""

import json
import logging
import os
import time
from typing import Dict, List, Optional, Union

from duolingo_base.registry import inject
from requests import get, post, put
from requests.auth import HTTPBasicAuth
from requests.exceptions import RequestException
from werkzeug.datastructures import FileStorage

from jeeves.dal.employees import EmployeesDAL
from jeeves.lib.profiling import traced_function
from jeeves.model.jira_issue_metadata import JiraIssueTypeMetaData
from jeeves.model.jira_priorities import JiraPriority
from jeeves.util.error_util import print_request_exception

LOG = logging.getLogger(__name__)

_HOST = "https://duolingo.atlassian.net"
_API = f"{_HOST}/rest/api/2"


_USERNAME_ANDROID = os.environ.get("SHAKIRA_JIRA_USERNAME_ANDROID")
_API_TOKEN_ANDROID = os.environ.get("SHAKIRA_JIRA_API_TOKEN_ANDROID")
_USERNAME_IOS = os.environ.get("SHAKIRA_JIRA_USERNAME_IOS")
_API_TOKEN_IOS = os.environ.get("SHAKIRA_JIRA_API_TOKEN_IOS")
_USERNAME_WEB = os.environ.get("SHAKIRA_JIRA_USERNAME_WEB")
_API_TOKEN_WEB = os.environ.get("SHAKIRA_JIRA_API_TOKEN_WEB")
_USERNAME_LITERACY = os.environ.get("SHAKIRA_JIRA_USERNAME_LITERACY")
_API_TOKEN_LITERACY = os.environ.get("SHAKIRA_JIRA_API_TOKEN_LITERACY")
_USERNAME_DET = os.environ.get("JIRA_USERNAME")
_API_TOKEN_DET = os.environ.get("JIRA_API_TOKEN")
_USERNMAE_ALL_PROJECTS = os.environ.get("JIRA_USERNAME")
_API_TOKEN_ALL_PROJECTS = os.environ.get("JIRA_API_TOKEN")

_ISSUE_TYPE_BUG = "Bug"
_ISSUE_TYPE_STORY = "Story"
_ALL_ISSUE_TYPES = [_ISSUE_TYPE_BUG, _ISSUE_TYPE_STORY]

_DESCRIPTION_FOR_ISSUES_SENT_TO_SLACK = (
    "This issue will be shared to a feature-specific Slack channel."
)

_DESCRIPTION_FOR_LITERACY_ISSUES_SENT_TO_SLACK = (
    "This issue will be shared to the #team-literacy-testing Slack channel."
)

_DESCRIPTION_FOR_ISSUES_WITH_RELATED_TICKET = "This issue is linked to another issue."

_CACHE = {}
_CACHE_EXPIRATION = 60 * 60 * 24  # 24 hours in seconds


@inject.bind(
    employees_dal=inject.reference(EmployeesDAL),
)
class ShakiraJiraApiClient:
    def __init__(self, employees_dal: EmployeesDAL) -> None:
        self._employees_dal = employees_dal

    def issue_url(self, issue_key: str) -> str:
        """
        URL to issue in Jira.
        """
        return f"{_HOST}/browse/{issue_key}"

    def get_jira_api_token(self, project: Optional[str]):
        """
        Returns API token based on given project.
        """
        # If no project is provided, default to iOS for backwards-compatibility
        if project == "LIT":
            return _API_TOKEN_LITERACY
        elif project == "DETBUG":
            return _API_TOKEN_DET
        elif project == "DLAA":
            return _API_TOKEN_ANDROID
        elif project == "DLAW":
            return _API_TOKEN_WEB
        else:
            return _API_TOKEN_IOS

    def _get_jira_auth(self, project: Optional[str] = None) -> HTTPBasicAuth:
        """
        Returns authentication for the appropriate service account. If no project
        is provided default to the iOS account.
        """
        if project == "LIT":
            return HTTPBasicAuth(_USERNAME_LITERACY, _API_TOKEN_LITERACY)
        elif project == "DETBUG":
            return HTTPBasicAuth(_USERNAME_DET, _API_TOKEN_DET)
        elif project == "DLAA":
            return HTTPBasicAuth(_USERNAME_ANDROID, _API_TOKEN_ANDROID)
        elif project == "DLAW":
            return HTTPBasicAuth(_USERNAME_WEB, _API_TOKEN_WEB)
        else:
            return HTTPBasicAuth(_USERNAME_IOS, _API_TOKEN_IOS)

    def _get_full_access_jira_auth(self) -> HTTPBasicAuth:
        """
        Returns a Jira account with access to all projects.

        The individual Shake To Report credentials are desired because they make
        the reporting user align with people's expectations better, and for legacy reasons.
        In the future, we may like to consolidate accounts, but for now, the individual
        project accounts can run into issues when we try to link issues because they do not
        have access to all Jira projects. Thus, we provide an account with full access for
        making read-only or "link issues" backend requests.
        """
        return HTTPBasicAuth(_USERNMAE_ALL_PROJECTS, _API_TOKEN_ALL_PROJECTS)

    def _get_metadata_url_and_params(
        self, projects: Union[str, List[str]], issue_types: Union[str, List[str]]
    ) -> str:
        url = f"{_API}/issue/createmeta"
        params = {
            "expand": "projects.issuetypes.fields",
            "projectKeys": projects,
            "issuetypeNames": issue_types,
        }
        return (url, params)

    def get_issuetype_metadata(
        self, projects: Union[str, List[str]]
    ) -> List[JiraIssueTypeMetaData]:
        """
        Get metadata about issuetypes, including fields, in the given project(s).

        parameters
            projects: e.g. DLAA, DLAI, DLAW
        """
        url, params = self._get_metadata_url_and_params(projects, _ALL_ISSUE_TYPES)
        current_time = time.time()
        cache_key = tuple([url, json.dumps(params)])  # Use url and params as the cache key
        response_json = None

        headers = {"Accept": "application/json"}
        # TODO: The DLAW service account is the only one with which retrieving
        #  features for all projects has been tested. It has too much permissions
        #  so should be swapped out with a single service account with the correct
        #  permissions that works for all projects.
        auth = self._get_jira_auth("DLAW")

        # Check cache first, if not, call the Jira API
        try:
            if cache_key in _CACHE:
                cached_data, timestamp = _CACHE[cache_key]
                if current_time - timestamp < _CACHE_EXPIRATION:
                    LOG.info("Get features from cache")
                    response_json = cached_data
                else:
                    del _CACHE[cache_key]
                    r = get(url, auth=auth, headers=headers, params=params)
                    r.raise_for_status()

                    response_json = json.loads(r.text)
                    _CACHE[cache_key] = (response_json, current_time)
            else:
                r = get(url, auth=auth, headers=headers, params=params)
                r.raise_for_status()

                response_json = json.loads(r.text)
                _CACHE[cache_key] = (response_json, current_time)

            return list(
                {
                    JiraIssueTypeMetaData.from_json(issuetype).id: JiraIssueTypeMetaData.from_json(
                        issuetype
                    )
                    for project in response_json["projects"]
                    for issuetype in project["issuetypes"]
                }.values()
            )
        except RequestException as e:
            print_request_exception(e, log_level="error")
            return []

    def get_features(self, projects: Union[str, List[str]]) -> List[str]:
        """
        Get possible values for the "Feature" issue field in a project.

        parameters
            projects: e.g. DLAA, DLAI, DLAW
        """
        issuetypes = self.get_issuetype_metadata(projects)

        return list(
            {name for issuetype in issuetypes for name in issuetype.allowed_feature_values()}
        )

    def _get_context_url_for_field(self, field_key: str) -> str:
        return f"{_HOST}/rest/api/3/field/{field_key}/context"

    def get_contexts(self, field_key: str) -> List[str]:
        url = self._get_context_url_for_field(field_key)
        auth = self._get_jira_auth("DLAW")
        headers = {"Accept": "application/json"}

        try:
            r = get(url, auth=auth, headers=headers)
            r.raise_for_status()

            response_json = json.loads(r.text)
            return [context["id"] for context in response_json["values"]]
        except RequestException as e:
            print_request_exception(e, log_level="error")

    def _get_create_url_for_field_and_context(self, field_key: str, context_id: str) -> str:
        return f"{_HOST}/rest/api/2/field/{field_key}/context/{context_id}/option"

    def create_options_for_field(self, field_key: str, context_id: str, options: List[str]):
        url = self._get_create_url_for_field_and_context(field_key, context_id)
        auth = self._get_jira_auth("DLAW")
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        data = {"options": [{"value": option} for option in options]}

        try:
            r = post(url, auth=auth, headers=headers, data=json.dumps(data))
            r.raise_for_status()
        except RequestException as e:
            print_request_exception(e, log_level="error")
            raise

    def _get_metadata_for_specific_issuetype(
        self, project: str, issuetype: str
    ) -> Optional[JiraIssueTypeMetaData]:
        url, params = self._get_metadata_url_and_params(project, issuetype)
        headers = {"Accept": "application/json"}
        auth = self._get_jira_auth(project)
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
            print_request_exception(e, log_level="error")
            return None

    def _get_id_for_user(self, email: str) -> Optional[str]:
        try:
            employee = self._employees_dal.get_employee_by_email(email)
            if employee is None:
                return None
            return employee.get("atlassianId")
        except KeyError:
            print_request_exception(Exception("No Atlassian ID found for user"), log_level="error")
            return None

    def _get_slack_channel_description(self, project: str):
        if project == "LIT":
            return _DESCRIPTION_FOR_LITERACY_ISSUES_SENT_TO_SLACK
        return _DESCRIPTION_FOR_ISSUES_SENT_TO_SLACK

    @traced_function()
    def set_priority(self, project: str, issue_key: str, priority: JiraPriority):
        """
        Set the priority of an issue in JIRA.

        parameters:
            project: e.g. DLAA, DLAI, DLAW, LIT, DETBUG
            issue_key: e.g. DLAA-1234
            priority: e.g. Highest, High, Medium, Low, Lowest
        """
        url = f"{_HOST}/rest/api/2/issue/{issue_key}"
        auth = self._get_jira_auth(project)
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        data = {"fields": {"priority": {"name": priority}}}

        try:
            r = put(url, auth=auth, headers=headers, data=json.dumps(data))
            r.raise_for_status()
        except RequestException as e:
            print_request_exception(e, log_level="error")
            raise

    @traced_function()
    def create_issue(
        self,
        project: str,
        feature: Optional[str],
        labels: List[str],
        summary: str,
        description: Optional[str],
        generated_description: Optional[str],
        reporter_email: Optional[str],
        pre_release: bool,
        will_post_to_slack: Optional[bool],
        related_issue_exists: Optional[bool],
    ) -> Optional[str]:
        """
        Create an issue in JIRA.
        For reference: https://docs.atlassian.com/software/jira/docs/api/REST/8.13.1/#api/2/issue

        parameters:
            project: e.g. DLAA, DLAI, DLAW, LIT, DETBUG
            feature: e.g. Achievements
            labels: A list of labels to add to the Jira issue.
            summary: Rougly one-sentence summary of issue.
            description: Longer issue description.
            generated_description: Generated information such as app version, fullstory url, session type, etc.
            reporter_email: Email of the duo reporting the issue.
            pre_release: Whether the bug is being reported from pre-release app version.
            will_post_to_slack: Whether jeeves will post the issue link to Slack itself.

        returns:
            issue key: str e.g. DLAA-2508

        """
        # We currently only create bugs. In the future this could change based on the feature
        # or be specified by the client.
        issuetype = self._get_metadata_for_specific_issuetype(project, _ISSUE_TYPE_BUG)
        if issuetype:
            fields = {
                "project": {"key": project},
                "summary": summary,
                "description": "\n".join(
                    [
                        desc
                        for desc in [
                            description,
                            generated_description,
                            self._get_slack_channel_description(project)
                            if will_post_to_slack
                            else None,
                            _DESCRIPTION_FOR_ISSUES_WITH_RELATED_TICKET
                            if related_issue_exists
                            else None,
                        ]
                        if desc
                    ]
                ),
                "issuetype": {"id": issuetype.id},
            }

            if feature:
                feature_field_key = issuetype.feature_field_key()
                feature_value_id = issuetype.get_id_for_allowed_feature_value(feature)
                if feature_field_key and feature_value_id:
                    fields[feature_field_key] = {"id": feature_value_id}

            reporter_id = None
            if reporter_email:
                reporter_id = self._get_id_for_user(reporter_email)
            if reporter_id:
                fields["reporter"] = {"id": reporter_id}
            else:
                labels.append("bug-triage")

            # From TRI-4563. Teams can remove this label after they've reviewed the GPT-estimated priority.
            labels.append("prioritized-by-gpt")

            if pre_release:
                labels.append("rc-shakira")

            if len(labels) > 0:
                fields["labels"] = labels

            request = {"fields": fields}
            url = f"{_API}/issue"
            headers = {"Content-Type": "application/json"}
            auth = self._get_jira_auth(project)
            try:
                LOG.info(f"Creating JIRA issue for project {project}\n{request}")

                r = post(url, auth=auth, headers=headers, data=json.dumps(request))
                r.raise_for_status()
                response_json = json.loads(r.text)
                return response_json["key"]
            except RequestException as e:
                print_request_exception(e, log_level="error")
                return None

    def add_comment(self, project: str, issue_key: str, comment: str) -> None:
        request = {"body": comment}
        url = f"{_API}/issue/{issue_key}/comment"
        headers = {"Content-Type": "application/json"}
        auth = self._get_jira_auth("DLAW")
        try:
            r = post(url, auth=auth, headers=headers, data=json.dumps(request))
            r.raise_for_status()
        except RequestException as e:
            print_request_exception(e, log_level="error")
            return None

    def add_label(
        self,
        issue_key: str,
        label: str,
        project: str,
    ) -> None:
        """
        Adds a label to an existing Jira ticket.

        :param issue_key: ID of the Jira issue to add a label to.
        :param label: Label to add to the Jira issue.
        :param project: Project of this Jira issue.
        """
        auth = self._get_jira_auth(project)
        body = {"update": {"labels": [{"add": label}]}}
        headers = {"Content-Type": "application/json"}
        url = f"{_API}/issue/{issue_key}"
        try:
            r = put(url, auth=auth, headers=headers, json=json.dumps(body))
            r.raise_for_status()
        except RequestException as e:
            print_request_exception(e, log_level="error")
            return None

    def get_issue_details(self, issue_key: str) -> Optional[Dict]:
        """
        Get details for JIRA issue with key issue_key
        For reference: https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issues/#api-rest-api-3-issue-issueidorkey-get

        parameters:
            issue_key: JIRA issue to get details for e.g. DLAA-5690

        """
        url = f"{_HOST}/rest/api/3/issue/{issue_key}"
        headers = {"Accept": "application/json"}  # header required by JIRA API
        auth = self._get_full_access_jira_auth()

        try:
            r = get(url, auth=auth, headers=headers)
            r.raise_for_status()
            response = json.loads(r.text)
            return response
        except RequestException as e:
            print_request_exception(e, log_level="error")
            return None

    def link_issues(
        self,
        outward_issue_key: str,
        inward_issue_key: str,
        link_type: str = "Relates",
    ):
        """
        Link two Jira issues
        For reference: https://developer.atlassian.com/cloud/jira/platform/rest/v3/api-group-issue-links/#api-group-issue-links

        parameters:
            outward_issue_key: JIRA issue to create link from e.g. DLAA-5690
            inward_issue_key: JIRA issue to create link to e.g. DLAA-5691
        """
        url = f"{_HOST}/rest/api/3/issueLink"
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        auth = self._get_full_access_jira_auth()
        data = {
            "outwardIssue": {"key": outward_issue_key},
            "inwardIssue": {"key": inward_issue_key},
            "type": {"name": link_type},
        }
        try:
            r = post(url, auth=auth, headers=headers, data=json.dumps(data))
            r.raise_for_status()
        except RequestException as e:
            print_request_exception(e, log_level="error")

    @traced_function()
    def upload_attachments(self, project: str, issue_key: str, files: Dict[str, "FileStorage"]):
        """
        Upload attachment to JIRA issue with key issue_key
        For reference: https://docs.atlassian.com/software/jira/docs/api/REST/8.13.1/#api/2/issue/{issueIdOrKey}/attachments

        parameters:
            issue_key: JIRA issue to upload attachments to e.g. DLAA-5690
            files: MultiDict of form name to file

        raises:
            RequestException: if upload request fails
        """
        url = f"{_API}/issue/{issue_key}/attachments"
        headers = {"X-Atlassian-Token": "no-check"}  # header required by JIRA API
        auth = self._get_jira_auth(project)
        jira_files = [
            (
                "file",  # The JIRA API requires every file to have the form name 'file'
                FileStorage(
                    stream=f.stream,
                    content_type=f.content_type,
                    content_length=f.content_length,
                    filename=f.filename,
                    # This property seems to get set as the filename by the JIRA API, so we want it to
                    # be the filename and not the form name.
                    name=f.filename,
                ),
            )
            for l in files.listvalues()
            for f in l
        ]
        try:
            r = post(url, auth=auth, headers=headers, files=jira_files)
            r.raise_for_status()
        except RequestException as e:
            print_request_exception(e, log_level="error")
            raise e

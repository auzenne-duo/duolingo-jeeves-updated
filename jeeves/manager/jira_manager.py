"""
Manager for JIRA documents.
"""

import json
import logging
import re
import sys
from datetime import datetime
from typing import Dict, List, Optional, Type

import duo_logging  # type: ignore[import]
from duolingo_base.dal.s3 import S3Client, S3Exception

from jeeves.config.config import (
    JIRA_ISSUE_TYPE_BUG,
    JIRA_LOCALIZATION_CONTRACTORS_LABEL,
    JIRA_PROJECTS,
)
from jeeves.config.jira_features import ALL_CUSTOM_PROJECTS
from jeeves.dal.jira_dal import JiraDAL
from jeeves.manager.jeeves_manager import JeevesManager
from jeeves.model.custom_types import JSON
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.jira_document import JiraDocument
from jeeves.util.date_util import date_to_str, parse_external_datetime
from jeeves.util.shakira import JIRA_VIA_JEEVES_LABEL, SHAKE_TO_REPORT_LABEL

LOG = logging.getLogger(__name__)
LOG.setLevel(logging.INFO)


class JiraManager(JeevesManager):
    @staticmethod
    def _try_set_jira_document_feature_field_key() -> bool:
        if JiraDocument.get_feature_field_key() is not None:
            return True
        try:
            # The custom projects might not have feature fields so don't check them
            projects_to_set = [
                project for project in JIRA_PROJECTS if project not in ALL_CUSTOM_PROJECTS
            ]

            issuetypes = JiraDAL.get_issuetype_metadata(projects_to_set, JIRA_ISSUE_TYPE_BUG)
            codebase_field_keys = {issuetype.codebase_field_key() for issuetype in issuetypes}
            feature_field_keys = {issuetype.feature_field_key() for issuetype in issuetypes}
            team_field_keys = {issuetype.team_field_key() for issuetype in issuetypes}
            if len(codebase_field_keys) == 1:
                JiraDocument.set_codebase_field_key(codebase_field_keys.pop())
            else:
                duo_logging.capture_message(
                    f"Expected one unique codebase field key, got {len(codebase_field_keys)}",
                    "warning",
                )
            if len(team_field_keys) == 1:
                JiraDocument.set_team_field_key(team_field_keys.pop())
            else:
                duo_logging.capture_message(
                    f"Expected one unique team field key, got {len(team_field_keys)}", "warning"
                )
            if len(feature_field_keys) == 1:
                JiraDocument.set_feature_field_key(feature_field_keys.pop())
                return True
            else:
                duo_logging.capture_message(
                    f"Expected one unique feature field key, got {len(feature_field_keys)}", "error"
                )
                return False
        except:
            duo_logging.capture_exception(sys.exc_info())
            return False

    @staticmethod
    def _try_set_feature_for_jira_document(doc: JiraDocument) -> bool:
        try:
            feature_name = JiraDAL.get_feature_for_jira_document(doc)
            if feature_name is None:
                return False

            doc.feature = feature_name
            return True
        except:
            duo_logging.capture_exception(sys.exc_info())
            return False

    @staticmethod
    def get_feature_field():
        """
        Tries to set and then return the feature field key
        """
        JiraManager._try_set_jira_document_feature_field_key()
        return JiraDocument.get_feature_field_key()

    @staticmethod
    def get_managed_document_type() -> Type[JeevesDocument]:
        """
        Please see parent class for documentation
        """
        return JiraDocument

    @staticmethod
    def get_checkpoint_file_name() -> str:
        """
        Returns the name of the S3 file used for storing checkpoint data.
        """
        return f"{JiraManager.get_managed_document_type().get_data_source_identifier()}/checkpoint_data.txt"

    @staticmethod
    def update_s3_if_necessary(s3_client, bucket_name: str, default_start_timestamp: float) -> None:
        """
        Please see parent class for documentation
        """
        # Jira API adjusts the actual max based on the fields requested
        max_results_per_page = 100

        _CHECKPOINT_FILE = JiraManager.get_checkpoint_file_name()
        checkpoint_files = None
        try:
            checkpoint_files = list(
                s3_client.yield_filenames(bucket_name, path_prefix=_CHECKPOINT_FILE)
            )
        except S3Exception as e:
            print(
                f"No checkpoint file found for bucket {bucket_name}, creating one now",
                e,
                flush=True,
            )

        if not checkpoint_files:
            new_checkpoint_string = str(int(default_start_timestamp * 1000))
            print(f"Making new checkpoint file {new_checkpoint_string}", flush=True)
            s3_client.upload(bucket_name, _CHECKPOINT_FILE, new_checkpoint_string)

        start_timestamp_millis = int(s3_client.download(bucket_name, _CHECKPOINT_FILE))
        projects_fetch_string = (
            f"project IN ({','.join(JIRA_PROJECTS)}) "
            + f"AND updated > {start_timestamp_millis} "
            + f"AND issueType = {JIRA_ISSUE_TYPE_BUG} "
            + f"AND labels != {JIRA_VIA_JEEVES_LABEL} "
            + "ORDER BY updated asc"
        )

        url_params = {
            "fields": "*all",
            "maxResults": max_results_per_page,
            "startAt": 0,
            "jql": projects_fetch_string,
        }
        for issue in JiraDAL.paginate_search_issues(url_params):
            # Store to S3
            issue_updated_time = parse_external_datetime(issue["fields"]["updated"])
            issue_updated_date = date_to_str(issue_updated_time)
            LOG.info("%s, Store issue id %s to S3", issue_updated_time, str(issue["id"]))
            upload_path = f"{JiraManager.get_managed_document_type().get_data_source_identifier()}/{issue_updated_date}/{issue['id']}"
            s3_client.upload(bucket_name, upload_path, json.dumps(issue))
            issue_updated_millis = int(issue_updated_time.timestamp() * 1000)
            if issue_updated_millis > start_timestamp_millis:
                start_timestamp_millis = issue_updated_millis
                s3_client.upload(bucket_name, _CHECKPOINT_FILE, f"{start_timestamp_millis}")

    @staticmethod
    def download_specific_issue(issue_key: str) -> Optional[JiraDocument]:
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
        JiraManager._try_set_jira_document_feature_field_key()
        return JiraDAL.get_issue(issue_key)

    @staticmethod
    def download_bulk_issues_with_features(issue_keys: List[str]) -> List[JiraDocument]:
        """
        Sets the feature field key for jira documents and then downloads the issues by key

        Parameters:
            issue_keys: Issue keys of the issues we wish to download.

        Returns:
            List of JeevesDocuments object representing the requested issues we were
            able to download.
        """
        JiraManager._try_set_jira_document_feature_field_key()
        return JiraDAL.get_bulk_issues(issue_keys)

    @staticmethod
    def get_most_recent_s3_populated_date(s3_client: S3Client, bucket_name: str) -> datetime:
        """
        Please see parent class for documentation.
        """
        checkpoint_timestamp = (
            int(s3_client.download(bucket_name, JiraManager.get_checkpoint_file_name())) // 1000
        )
        return datetime.utcfromtimestamp(checkpoint_timestamp)

    @staticmethod
    def process_document(doc_json: JSON) -> Optional[JeevesDocument]:
        """
        Please see parent class for documentation.
        """
        JiraManager._try_set_jira_document_feature_field_key()
        test_doc = JiraDocument.deserialize_from_external_json(doc_json)
        JiraManager._try_set_feature_for_jira_document(test_doc)
        JiraManager._populate_with_experiment_conditions(test_doc)
        if JiraDocument.check_should_index_document(test_doc):
            return test_doc
        return None

    @staticmethod
    def _populate_with_experiment_conditions(jira_doc: JiraDocument) -> None:
        for attachment in jira_doc.jira_attachments:
            if attachment["filename"] == "experiment_conditions.txt":
                contents = JiraDAL.get_attachment_contents(attachment["id"])
                experiment_conditions = {}
                for condition in re.findall("[a-zA-Z\d_]+: [a-zA-Z\d_]+", contents):
                    key, value = condition.split(": ")
                    experiment_conditions[key] = value
                jira_doc.experiment_conditions = experiment_conditions
                return

    @staticmethod
    def get_str_tickets_jql(start_datetime: datetime) -> List[Dict]:
        start_str = start_datetime.strftime("%Y-%m-%d %H:%M")
        fetch_string = (
            f'updated >= "{start_str}" '
            + f"AND issueType = {JIRA_ISSUE_TYPE_BUG} "
            + f"AND labels in ('{SHAKE_TO_REPORT_LABEL}') "
            + "ORDER BY updated asc"
        )
        LOG.debug(f"fetch_string: {fetch_string}")
        url_params = {
            "fields": "*all",
            "maxResults": 100,
            "startAt": 0,
            "jql": fetch_string,
        }

        issues = []
        for issue in JiraDAL.paginate_search_issues(url_params):
            assert isinstance(issue, dict)
            issues.append(issue)
        return issues

    @staticmethod
    def get_str_tickets_since(start_datetime: datetime) -> List[Dict]:
        """
        Yields shake-to-report tickets that have been updated since the start date.

        Returns all issues with the "shake-to-report" label.

        Params:
            start_datetime: only consider issues updated after this datetime (must be tz-aware UTC)

        Returns:
            List of JSON as returned by Jira API (dict)
        """
        return JiraManager.get_str_tickets_jql(start_datetime)

    @staticmethod
    def get_jira_issues_since(start_datetime_string: str) -> List[JiraDocument]:
        """
        Yields bugs that have been updated since the start date

        Params:
            start_datetime_string (str): only consider issues with updated after this datetime
                examples include "2023-02-14" or "-40h"

        Returns:
            List of JiraDocuments
        """
        JiraManager._try_set_jira_document_feature_field_key()
        max_results_per_page = 100
        projects_fetch_string = (
            f"project IN ({','.join(JIRA_PROJECTS)}) "
            + f'AND updated >= "{start_datetime_string}" '
            + f"AND issueType = {JIRA_ISSUE_TYPE_BUG} "
            + f"AND labels NOT IN ('{JIRA_LOCALIZATION_CONTRACTORS_LABEL}') "
            + "ORDER BY updated asc"
        )

        url_params = {
            "fields": "*all",
            "maxResults": max_results_per_page,
            "startAt": 0,
            "jql": projects_fetch_string,
        }

        docs = []
        for i, issue in enumerate(JiraDAL.paginate_search_issues(url_params)):
            docs.append(JiraDocument.deserialize_from_external_json(issue))
            if i % 500 == 0:
                print(f"Paginating jira issues; at {i}", flush=True)
        print("finished paginating")
        return docs

    # Check if jira ticket already exists based on project and summary
    @staticmethod
    def check_duplicates_jira(project: str, summary: str) -> bool:
        if not project or not summary:
            return False

        summary = summary.replace('"', "")

        url_params = {
            "fields": "*all",
            "maxResults": 100,
            "startAt": 0,
            "jql": f'project = {project} AND summary ~ "{summary}"',
        }

        for _ in JiraDAL.paginate_search_issues(url_params):
            print(f"Duplicate Jira tickets detected: {summary}, stop creating Jira", flush=True)
            return False
        return True

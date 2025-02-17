"""
Manager for Zendesk documents.
"""

import base64
import json
import logging
import os
import time
from collections import Counter
from datetime import datetime
from io import BytesIO
from typing import Dict, Type

import requests
from duolingo_base.dal.auth_api import SearchKeys
from duolingo_base.dal.s3 import S3Client
from requests import RequestException, Session, post
from werkzeug.datastructures import FileStorage

from jeeves import registry as app_registry
from jeeves.dal.auth_dal import AuthDAL
from jeeves.manager.jeeves_manager import JeevesManager
from jeeves.manager.jira_manager import JiraManager
from jeeves.manager.shakira import ShakiraManager
from jeeves.manager.shakira_jira import ShakiraJiraApiClient
from jeeves.model.custom_types import JSON
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.zendesk_document import ZendeskDocument
from jeeves.util.date_util import date_to_str, datetime_to_str, parse_external_datetime
from jeeves.util.error_util import print_request_exception
from jeeves.util.sleep_check import sleep_check

_USER = os.environ.get("ZENDESK_USER")
_ZENDESK_API_TOKEN = os.environ.get("ZENDESK_API_TOKEN")

_HOST = "https://duolingo.atlassian.net"
_API = f"{_HOST}/rest/api/2"

_ENV = os.environ.get("SENTRY_ENVIRONMENT", "local")

LOG = logging.getLogger(__name__)


class ZendeskManager(JeevesManager):
    @staticmethod
    def get_managed_document_type() -> Type[JeevesDocument]:
        """
        Please see parent class for documentation
        """
        return ZendeskDocument

    @staticmethod
    def get_checkpoint_file_name() -> str:
        """
        Returns the name of the S3 file used for storing checkpoint data.
        """
        return f"{ZendeskManager.get_managed_document_type().get_data_source_identifier()}/checkpoint_data.txt"

    @staticmethod
    def is_localization_contractor(user_id: str) -> bool:
        auth_api = AuthDAL().auth_api

        try:
            user_id = int(user_id)
        except ValueError:
            return False

        user_info = auth_api.search(SearchKeys(user_id=[user_id]), fields=["groups"])

        time.sleep(5)

        if len(user_info) > 0 and AuthDAL().beta_user_security_roles in user_info[0]["groups"]:
            return True

        return False

    @staticmethod
    def create_jira_ticket(ticket_json: JSON, files: Dict[str, "FileStorage"]) -> str:
        description = ticket_json.get("description", "")
        feature = ticket_json.get("feature", "")
        tags = ticket_json.get("tags", [])
        project = None
        if "bug_report_ios" in tags or "iOS" in description:
            project = "DLAI"
        elif "bug_report_android" in tags or "Android" in description:
            project = "DLAA"
        summary = ticket_json.get("subject", "")

        if summary:
            summary = summary.replace("\n", " ")

        email = ticket_json.get("recipient", "")

        issue_status = None

        # Only prod env can create jira tickets from Zendesk
        if project and _ENV in ["prod"] and JiraManager.check_duplicates_jira(project, summary):
            issue_status = app_registry(ShakiraManager).report_issue(
                project=project,
                feature=feature,
                slack_report_type=None,
                client_specified_slack_channel_name=None,
                related_issue_key=None,
                summary=summary,
                description=description,
                generated_description=None,
                reporter_email=email,
                pre_release=False,
                release_blocker=False,
                files={},
                localization_contractor=True,
            )
            LOG.info(f"Jira ticket created: {issue_status}")

        if issue_status:
            ZendeskManager.attach_files(project, issue_status["issueKey"], files)
        return issue_status

    @staticmethod
    def _url_to_filestorage(url):
        # Download the file
        response = requests.get(url)
        if response.status_code != 200:
            raise ValueError(f"Failed to download file from {url}")

        # Extract the filename from the URL
        filename = url.split("name=")[-1]

        # Create a FileStorage object
        file_data = BytesIO(response.content)
        return FileStorage(file_data, filename=filename), filename

    @staticmethod
    def attach_files(project, issue_key, files) -> None:
        url = f"{_API}/issue/{issue_key}/attachments"
        headers = {"X-Atlassian-Token": "no-check"}  # header required by JIRA API
        auth = app_registry(ShakiraJiraApiClient)._get_jira_auth(project)
        jira_files = [
            (
                "file",  # The JIRA API requires every file to have the form name 'file'
                FileStorage(
                    stream=files[name].stream,
                    content_type=files[name].content_type,
                    content_length=files[name].content_length,
                    filename=files[name].filename,
                    # This property seems to get set as the filename by the JIRA API, so we want it to
                    # be the filename and not the form name.
                    name=files[name].filename,
                ),
            )
            for name in files
        ]
        try:
            r = post(url, auth=auth, headers=headers, files=jira_files)
            r.raise_for_status()
        except RequestException as e:
            print_request_exception(e, log_level="error")
            raise e

    @staticmethod
    def _extract_localization_contractors(ticket_json: JSON) -> None:
        # Get User id out from Zendesk ticket
        # Get User id contract group using auth api
        # Filter out Loc contratcor using ios-build-downloads group
        # Create Jira tickets for those filter out Zendesk tickets
        description = ticket_json.get("description", "")
        split_part = description.split("\n")
        for part in split_part:
            if "id" in part.lower():
                user_id = part.split(": ")[-1].strip()
                if ZendeskManager.is_localization_contractor(user_id):
                    file_dict = {}
                    for attachment in ticket_json["attachments"]:
                        file, name = ZendeskManager._url_to_filestorage(attachment)
                        file_dict[name] = file
                    ZendeskManager.create_jira_ticket(ticket_json, file_dict)

    @staticmethod
    def update_s3_if_necessary(s3_client, bucket_name: str, default_start_timestamp: float) -> None:
        """
        Please see parent class for documentation
        """
        _CHECKPOINT_FILE = ZendeskManager.get_checkpoint_file_name()
        if not list(s3_client.yield_filenames(bucket_name, path_prefix=_CHECKPOINT_FILE)):
            new_checkpoint_string = str(int(default_start_timestamp))
            s3_client.upload(bucket_name, _CHECKPOINT_FILE, new_checkpoint_string)

        start_timestamp = int(s3_client.download(bucket_name, _CHECKPOINT_FILE))
        zendesk_host = "https://duolingotest.zendesk.com"
        next_url = f"{zendesk_host}/api/v2/incremental/tickets.json?start_time={start_timestamp}"

        urls = []

        with Session() as s:
            auth_str = f"{_USER}/token:{_ZENDESK_API_TOKEN}"
            b64_auth_str = base64.b64encode(auth_str.encode()).decode()
            s.headers.update({"Authorization": f"Basic {b64_auth_str}"})

            while True:
                sleep_check()
                if len(urls) > 0:
                    print("Sleeping", flush=True)
                    time.sleep(10)

                urls.append(next_url)
                # Break if same URL is requested for 5 times in a row
                if len(urls) > 5 and len(Counter(urls[-5:])) == 1:
                    print("Stopped making request to zendesk after consecutive errors")
                    break
                r = ZendeskDocument.rate_limited_get(s, next_url)
                j = json.loads(r.text)
                if "error" in j:
                    raise Exception("Error returned from Zendesk")
                for ticket_json in j["tickets"]:
                    ticket_id = ticket_json["id"]
                    comments_url = f"{zendesk_host}/api/v2/tickets/{ticket_id}/comments.json"
                    attachments = []
                    try:
                        comments_response = ZendeskDocument.rate_limited_get(s, comments_url)
                        comments_response.raise_for_status()
                        comments_structure = json.loads(comments_response.text)
                        for com in comments_structure.get("comments", {}):
                            for attach in com.get("attachments", {}):
                                attachments.append(attach["content_url"])
                    except RequestException as e:
                        print_request_exception(e)
                        # If the comment page cannot be found, then skip it
                        if e.response.status_code == 404:
                            pass
                        else:
                            # If something non-recoverable has happened, escalate.
                            raise (e)
                    ticket_json["attachments"] = attachments

                    ZendeskManager._extract_localization_contractors(ticket_json)

                    ZendeskManager._store_document_to_s3(s3_client, bucket_name, ticket_json)

                if j["end_time"]:
                    print(
                        f"Downloaded {len(j['tickets'])} tickets until: {datetime_to_str(datetime.fromtimestamp(j['end_time']))}"
                    )
                    s3_client.upload(bucket_name, _CHECKPOINT_FILE, str(int(j["end_time"])))

                if j["next_page"]:
                    next_url = j["next_page"]

                if j["end_of_stream"]:
                    break

    @staticmethod
    def _store_document_to_s3(s3_client: S3Client, bucket_name: str, doc: JSON) -> None:
        """
        Stores a given document to a given S3 bucket.
        File path in bucket is 'Zendesk/<date>/<document ID>'

        Parameters:
            s3_client: Duolingo base library S3 object. Expected to have write
                       access to the bucket specified by bucket_name.
            bucket_name: Name of the bucket we want to store the document to.
            doc: JSON representation of a document we wish to store.
        """
        identifier_directory = (
            ZendeskManager.get_managed_document_type().get_data_source_identifier()
        )
        date_directory = date_to_str(parse_external_datetime(doc["created_at"]))
        full_path = f"{identifier_directory}/{date_directory}/{doc['id']}"

        s3_client.upload(bucket_name, full_path, json.dumps(doc))

    @staticmethod
    def get_most_recent_s3_populated_date(s3_client: S3Client, bucket_name: str) -> datetime:
        """
        Please see parent class for documentation.
        """
        checkpoint_timestamp = int(
            s3_client.download(bucket_name, ZendeskManager.get_checkpoint_file_name())
        )
        return datetime.utcfromtimestamp(checkpoint_timestamp)

    @staticmethod
    def process_document(doc_json: JSON) -> JeevesDocument:
        """
        Please see parent class for documentation.
        """
        test_doc = ZendeskDocument.deserialize_from_external_json(doc_json)
        if ZendeskDocument.check_should_index_document(test_doc):
            return test_doc

        return None

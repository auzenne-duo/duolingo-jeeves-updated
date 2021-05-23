"""
Manager for JIRA documents.
"""
from datetime import datetime
import json
import os
from typing import Dict, Optional

from requests import get, post, put, Session
from requests.auth import HTTPBasicAuth
from requests.exceptions import RequestException

from duolingo_base.dal.s3 import S3Client

from jeeves.manager.jeeves_manager import JeevesManager
from jeeves.model.custom_types import JSON
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.jira_document import JiraDocument
from jeeves.util.date_util import date_to_str, parse_external_datetime
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

        _CHECKPOINT_FILE = JiraManager.get_checkpoint_file_name()
        if not list(s3_client.yield_filenames(bucket_name, path_prefix=_CHECKPOINT_FILE)):
            new_checkpoint_string = str(int(default_start_timestamp * 1000))
            s3_client.upload(bucket_name, _CHECKPOINT_FILE, new_checkpoint_string)

        start_timestamp_millis = int(s3_client.download(bucket_name, _CHECKPOINT_FILE))
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
                        # Store to S3
                        issue_updated_time = parse_external_datetime(issue["fields"]["updated"])
                        issue_updated_date = date_to_str(issue_updated_time)
                        upload_path = f"{JiraManager.get_managed_document_type().get_data_source_identifier()}/{issue_updated_date}/{issue['id']}"
                        s3_client.upload(bucket_name, upload_path, json.dumps(issue))
                        issue_updated_millis = int(issue_updated_time.timestamp() * 1000)
                        if issue_updated_millis > start_timestamp_millis:
                            start_timestamp_millis = issue_updated_millis
                            s3_client.upload(
                                bucket_name, _CHECKPOINT_FILE, f"{start_timestamp_millis}"
                            )

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
    def _create_paragraph_block(block_contents: str) -> JSON:
        """
        Simple wrapper to create a paragraph block with the given contents.

        Parameters:
            block_contents: The text we want to put in the paragraph block

        Returns:
            A paragraph block with the given contents as text.
        """
        paragraph_json = {
            "type": "paragraph",
            "content": [
                {
                    "type": "text",
                    "text": block_contents,
                }
            ],
        }
        return paragraph_json

    @staticmethod
    def generate_parent_body_text_from_data(data: Dict[str, Dict[str, int]]) -> JSON:
        """
        Given data aggregated from several duplicate issues, constructs the body
        text for the parent issue of those duplicate issues.

        Parameters:
            data: A dictionary representing data aggregated from duplicates, see
                  the return value of parse_parent_description for details. This
                  must have as keys each of the values of the JiraDocument
                  parent category mappings.

        Returns:
            A JSON blob that can be directly passed as body text into a Jira
            API call.
        """
        paragraph_blocks = []
        category_mapping = JiraDocument.get_parent_category_mappings()
        for human_name, data_name in category_mapping.items():
            block_contents = f"{human_name}:\n"
            for data_type, data_count in data[data_name].items():
                block_contents = f"{block_contents}{data_type}: {data_count}\n"
            paragraph_blocks.append(JiraManager._create_paragraph_block(block_contents))

        body_json = {
            "type": "doc",
            "version": 1,
            "content": paragraph_blocks,
        }
        return body_json

    @staticmethod
    def set_remote_parent_body(parent_key: str, data: Dict[str, Dict[str, int]]) -> bool:
        """
        Sets the body text of the issue specified by parent_key to content
        specified by the provided data, and saves this change to Jira.

        Parameters:
            parent_key: The issue key of the parent issue we want to edit
            data: The data we will use to generate the new parent body. See
                  parse_parent_description for format.

        Returns:
            True if the Jira API indicates that the operation completed
            successfully, otherwise False.
        """
        jira_host = "https://duolingo.atlassian.net"
        target_url = f"{jira_host}/rest/api/3/issue/{parent_key}"
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        auth = HTTPBasicAuth(_USERNAME, _API_TOKEN)
        data_operation = {
            "update": {
                "description": [{"set": JiraManager.generate_parent_body_text_from_data(data)}]
            }
        }

        try:
            r = put(target_url, headers=headers, auth=auth, data=json.dumps(data_operation))
            r.raise_for_status()
            return True
        except RequestException as e:
            print_request_exception(e)
            return False

    @staticmethod
    def upload_template_parent_issue(project: str, header_text: str) -> str:
        """
        Uploads a template parent issue to the specified project with the
        specified header text.

        The template issue contains paragraph blocks that each consist of one of
        the parent categories defined in get_parent_category_mappings() in the
        JiraDocument class. The resulting body text is appropriate for adding
        data to, sourced from individual Jira documents.

        Parameters:
            project: The project this parent issue should live in.
            header_text: The header text this parent issue should have.

        Returns:
            The issue key of the new parent issue, as returned by Jira.
        """

        category_names = JiraDocument.get_parent_category_mappings().values()
        body_json = JiraManager.generate_parent_body_text_from_data(
            {category: {} for category in category_names}
        )

        issue_data = {
            "fields": {
                "project": {
                    "key": project,
                },
                "issuetype": {
                    "name": "Bug",
                },
                "summary": header_text,
                "description": body_json,
                "labels": [
                    "parent_bug",
                ],
            }
        }
        base_api_url = "https://duolingo.atlassian.net/rest/api/3/issue"
        headers = {"Accept": "application/json", "Content-Type": "application/json"}
        auth = HTTPBasicAuth(_USERNAME, _API_TOKEN)

        try:
            r = post(base_api_url, auth=auth, headers=headers, data=json.dumps(issue_data))
            r.raise_for_status()

            response_JSON = json.loads(r.text)
            return response_JSON["key"]

        except RequestException as e:
            print_request_exception(e)
            return None

    @staticmethod
    def parse_parent_description(body_text: str) -> Dict[str, Dict[str, int]]:
        """
        Given the body text of a parent "hub" issue for duplicates, extracts
        the aggregated information in that body text and returns it as a
        dictionary.

        The returned dictionary is a mapping from strings, representing
        information field names, to another layer of dictionaries. These inner
        dictionaries are mappings from strings, representing instance types, to
        ints, representing instance occurances. Overall, the body text of a
        parent issue consists of several groups of information (such as
        platforms a bug has been reported in, courses a bug has been reported
        in, etc) that form the keys in the outer dictionary. Each inner
        dictionary entry represents a count of an instance appropriate for that
        group.

        The expected format of the body text is as follows:
        - Zero or more paragraphs separated by exactly one empty line.
        - A paragraph consists of:
            - A line of text that ends in a colon (this is the group title)
            - Zero or more data entries, each on their own line, with no
              empty lines between them. A data entry consists of a string,
              representing the instance type, then a colon and a space, and
              finally an integer representing the instance count of that
              instance type.

        Parameters:
            body_text: The body text of a parent issue to parse. Note that there
                       is currently no error checking on this function, so if
                       you provide garbage in you're likely to get garbage out.
        Returns:
            A dictionary of strings mapped to dictionaries of strings mapped to
            ints, as described above.
        """

        category_mapping = JiraDocument.get_parent_category_mappings()
        extracted_stats = {}
        body_lines = [line.strip() for line in body_text.splitlines()]
        line_rover = 0
        while line_rover < len(body_lines):
            category_header = body_lines[line_rover][:-1]
            category = category_mapping[category_header]
            extracted_stats[category] = {}
            line_rover += 1
            while line_rover < len(body_lines) and body_lines[line_rover] != "":
                instance_type = body_lines[line_rover].split(": ")[0]
                instance_count = int(body_lines[line_rover].split(": ")[1])
                extracted_stats[category][instance_type] = instance_count
                line_rover += 1
            while line_rover < len(body_lines) and body_lines[line_rover] == "":
                line_rover += 1

        return extracted_stats

    @staticmethod
    def update_parent_data_from_child(
        parent_data: Dict[str, Dict[str, int]], child: JeevesDocument
    ) -> Dict[str, Dict[str, int]]:
        """
        Given a structure of parent issue data and a child issue, updates the
        parent data to include the information from the child issue.

        Parameters:
            parent_data: A structure of parent issue data. See
                         parse_parent_description for details.
            child: A document that has data we want to include in the parent.

        Returns:
            We return parent_data after modification for convenience, though
            the input argument will also be mutated and therefore this return
            value is optional and may be ignored.
        """

        child_json = child.serialize_to_json(child)
        for category in parent_data:
            if category in child_json:
                if category == "components":
                    area_components = [
                        subcat for subcat in child_json[category] if subcat.endswith("Area")
                    ]
                    for area in area_components:
                        if area not in parent_data[category]:
                            parent_data[category][area] = 0
                        parent_data[category][area] += 1
                else:
                    data_instance = "NOT PRESENT"
                    if child_json[category]:
                        data_instance = child_json[category]
                    if data_instance not in parent_data[category]:
                        parent_data[category][data_instance] = 0
                    parent_data[category][data_instance] += 1

        return parent_data

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
    def get_most_recent_s3_populated_date(s3_client: S3Client, bucket_name: str) -> datetime:
        """
        Please see parent class for documentation.
        """
        checkpoint_timestamp = (
            int(s3_client.download(bucket_name, JiraManager.get_checkpoint_file_name())) // 1000
        )
        return datetime.fromtimestamp(checkpoint_timestamp)

    @staticmethod
    def process_document(doc_json: JSON) -> Optional[JeevesDocument]:
        """
        Please see parent class for documentation.
        """
        test_doc = JiraDocument.deserialize_from_external_json(doc_json)
        if JiraDocument.check_should_index_document(test_doc):
            return test_doc
        return None

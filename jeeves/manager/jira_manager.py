"""
Manager for JIRA documents.
"""
import json
import sys
from datetime import datetime
from typing import Dict, Optional

import rollbar
from duolingo_base.dal.s3 import S3Client
from requests import Session

from jeeves.dal.jira_dal import JiraDAL
from jeeves.manager.jeeves_manager import JeevesManager
from jeeves.model.custom_types import JSON
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.jira_document import JiraDocument
from jeeves.util.date_util import date_to_str, parse_external_datetime

_JIRA_PROJECTS = ["DLAA", "DLAI", "DLAW"]
_JIRA_ISSUE_TYPE_BUG = "Bug"


class JiraManager(JeevesManager):
    @staticmethod
    def _try_set_jira_document_feature_field_key() -> bool:
        try:
            issuetypes = JiraDAL.get_issuetype_metadata(_JIRA_PROJECTS, _JIRA_ISSUE_TYPE_BUG)
            feature_field_keys = {issuetype.feature_field_key() for issuetype in issuetypes}
            if len(feature_field_keys) == 1:
                JiraDocument.set_feature_field_key(feature_field_keys.pop())
                return True
            else:
                rollbar.report_message(
                    f"Expected one unique feature field key, got {len(feature_field_keys)}", "error"
                )
                return False
        except:
            rollbar.report_exc_info(sys.exc_info())
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
            rollbar.report_exc_info(sys.exc_info())
            return False

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
        # Jira API adjusts the actual max based on the fields requested
        max_results_per_page = 100

        _CHECKPOINT_FILE = JiraManager.get_checkpoint_file_name()
        if not list(s3_client.yield_filenames(bucket_name, path_prefix=_CHECKPOINT_FILE)):
            new_checkpoint_string = str(int(default_start_timestamp * 1000))
            s3_client.upload(bucket_name, _CHECKPOINT_FILE, new_checkpoint_string)

        start_timestamp_millis = int(s3_client.download(bucket_name, _CHECKPOINT_FILE))
        projects_fetch_string = f"project IN ({','.join(_JIRA_PROJECTS)}) AND updated > {start_timestamp_millis} AND issueType = {_JIRA_ISSUE_TYPE_BUG} ORDER BY updated asc"

        url_params = {
            "fields": "*all",
            "maxResults": max_results_per_page,
            "startAt": 0,
            "jql": projects_fetch_string,
        }
        total = None

        with Session() as s:
            while total is None or url_params["startAt"] < total:
                response_json = JiraDAL.search_issues_json(s, params=url_params)

                for issue in response_json["issues"]:
                    # Store to S3
                    issue_updated_time = parse_external_datetime(issue["fields"]["updated"])
                    issue_updated_date = date_to_str(issue_updated_time)
                    upload_path = f"{JiraManager.get_managed_document_type().get_data_source_identifier()}/{issue_updated_date}/{issue['id']}"
                    s3_client.upload(bucket_name, upload_path, json.dumps(issue))
                    issue_updated_millis = int(issue_updated_time.timestamp() * 1000)
                    if issue_updated_millis > start_timestamp_millis:
                        start_timestamp_millis = issue_updated_millis
                        s3_client.upload(bucket_name, _CHECKPOINT_FILE, f"{start_timestamp_millis}")

                url_params["startAt"] += len(response_json["issues"])
                if total is None:
                    # only update total once, rather than trying to hit a moving target of total
                    # issues downlaoded.
                    total = response_json["total"]

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
        JiraManager._try_set_jira_document_feature_field_key()
        return JiraDAL.get_issue(issue_key)

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
    def try_set_remote_parent_body(parent_key: str, data: Dict[str, Dict[str, int]]) -> bool:
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
        try:
            JiraDAL.set_issue_description(
                parent_key, JiraManager.generate_parent_body_text_from_data(data)
            )
            return True
        except:
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
        return JiraDAL.create_bug_issue(project, header_text, body_json)

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
    def try_mark_duplicate_remote(outward_key: str, inward_key: str) -> bool:
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
            True if the link is created, otherwise False.
        """
        try:
            JiraDAL.mark_duplicate(outward_key, inward_key)
            return True
        except:
            return False

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
        JiraManager._try_set_jira_document_feature_field_key()
        test_doc = JiraDocument.deserialize_from_external_json(doc_json)
        JiraManager._try_set_feature_for_jira_document(test_doc)
        if JiraDocument.check_should_index_document(test_doc):
            return test_doc
        return None

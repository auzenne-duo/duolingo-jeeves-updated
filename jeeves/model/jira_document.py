"""
Our model for a JIRA issue from the JIRA API
"""
import datetime
from typing import Dict, List, Union

import attr

from jeeves.lib.duplicate_detector import DuplicateDetector
from jeeves.model.custom_types import JSON
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.shake_to_report_category import ShakeToReportCategory
from jeeves.model.supported_languages import SUPPORTED_LANGUAGES
from jeeves.util.classify import detect_language
from jeeves.util.cleanup import extract_duolingo_metadata
from jeeves.util.date_util import parse_external_datetime
from jeeves.util.metadata_standardizer import MetaStdizer

_SHAKE_TO_REPORT_MARKER = "Reported with shake-to-report"


@attr.s(kw_only=True)
class JiraDocument(JeevesDocument):

    issue_key: str = attr.ib()
    issue_links: List[str] = attr.ib()
    issue_type: str = attr.ib()
    project: str = attr.ib()
    linked_duplicate_keys: List[str] = attr.ib()
    creation_date: datetime.datetime = attr.ib()
    updated_date: datetime.datetime = attr.ib()
    resolution_date: datetime.datetime = attr.ib()
    status: str = attr.ib()
    resolution: str = attr.ib()
    components: List[str] = attr.ib()
    features: List[str] = attr.ib()
    priority: str = attr.ib()
    reporter: str = attr.ib()
    assignee: str = attr.ib()
    # Comments is a list of dicts, each dict representing one comment
    # A comment dict contains these keys with corresponding types:
    # author: str, body: str, created: datetime, id: str, updated: datetime
    comments: List[Dict[str, Union[str, datetime.datetime]]] = attr.ib()
    labels: List[str] = attr.ib()
    embedding_vector: List[float] = attr.ib()

    @staticmethod
    def get_data_source_identifier() -> str:
        """
        Please see parent class for documentation
        """
        return "JIRA"

    @classmethod
    def _compress_rich_text(cls, rich_text: JSON) -> str:
        """
        Converts an instance of JIRA's rich text format into a single string.
        Some liberties are taken when converting in this way, for example,
        bulleted lists have each entry start on a new line with a hyphen representing
        the bullet. Resulting text should ideally convey the same meaning as input.

        Parameters:
            rich_text: Text in JIRA's rich text format. See
                https://developer.atlassian.com/cloud/jira/platform/apis/document/structure/
                for more details.

        Returns:
            A string that should serve as a 'close-enough' representation of the input
        """

        # Rich Text Type, so I can save on typing
        rtt = rich_text["type"]

        if rtt == "doc":
            return "\n".join([cls._compress_rich_text(node) for node in rich_text["content"]])

        if rtt == "text":
            return rich_text["text"]

        if rtt == "paragraph":
            subcontent = "".join([cls._compress_rich_text(node) for node in rich_text["content"]])
            return f"{subcontent}\n"

        if rtt == "bulletList":
            list_items = [f"\t- {cls._compress_rich_text(node)}" for node in rich_text["content"]]
            return "".join(list_items)

        if rtt == "orderedList":
            list_items = [
                f"\t{node[0]}. {cls._compress_rich_text(node[1])}"
                for node in enumerate(rich_text["content"], start=1)
            ]
            return "".join(list_items)

        if rtt == "listItem":
            return "".join([cls._compress_rich_text(node) for node in rich_text["content"]])

        if rtt == "hardBreak":
            return "\n"

        if rtt == "mention":
            return rich_text["attrs"]["text"]

        if rtt == "media":
            if "id" in rich_text["attrs"]:
                return rich_text["attrs"]["id"]
            return "<ID NOT FOUND DESPITE BEING REQUIRED IN THE SPEC>"

        if rtt == "mediaGroup" or rtt == "mediaSingle":
            return ", ".join([cls._compress_rich_text(node) for node in rich_text["content"]])

        if rtt == "inlineCard":
            if "url" in rich_text["attrs"]:
                return rich_text["attrs"]["url"]
            return "<JSONLD TO BE IMPLEMENTED LATER>"

        return f"<UNIMPLEMENTED TYPE: {rtt}>"

    @classmethod
    def _deserialize_comment(cls, comment_json: JSON) -> Dict[str, Union[str, datetime.datetime]]:
        """
        Helper function for external deserialization.

        Parameters:
            comment_json: JSON representation of a single comment on a JIRA issue.

        Returns:
            A dictionary with string keys that we can insert directly into our ticket model.
        """

        return {
            "author": comment_json["author"],
            "body": comment_json["body"]
            if isinstance(comment_json["body"], str)
            else cls._compress_rich_text(comment_json["body"]),
            "created": parse_external_datetime(comment_json["created"])
            if isinstance(comment_json["created"], str)
            else comment_json["created"],
            "id": comment_json["id"],
            "updated": parse_external_datetime(comment_json["updated"])
            if isinstance(comment_json["updated"], str)
            else comment_json["updated"],
        }

    @classmethod
    def get_duplicate_keys_from_issue_links(cls, issue_links: JSON) -> List[str]:
        """
        Given a JSON data structure from Jira representing issue links, extract
        the issue keys of issues that are considered duplicate issues according
        to that data structure.

        Parameters:
            issue_links: JSON from the 'issuelinks' field of an issue's data

        Returns:
            A list of strings, where each string is the issue key of a duplicate
            issue according to the input link structure.
        """

        known_duplicates = []
        for link in issue_links:
            if "Duplicate" in link["type"]["name"]:
                if "inwardIssue" in link:
                    known_duplicates.append(link["inwardIssue"]["key"])
                if "outwardIssue" in link:
                    known_duplicates.append(link["outwardIssue"]["key"])
        return known_duplicates

    @classmethod
    def deserialize_from_external_json(cls, external_json: JSON) -> JeevesDocument:
        """
        Please see parent class for documentation
        """
        external_fields = external_json["fields"]

        body_text = (
            cls._compress_rich_text(external_fields["description"])
            if external_fields["description"]
            else ""
        )

        is_shake_to_report = _SHAKE_TO_REPORT_MARKER in body_text

        duolingo_metadata = {}
        if is_shake_to_report:
            body_text, duolingo_metadata = extract_duolingo_metadata(body_text)

        std_metadata = MetaStdizer.get_standardized_metadata(duolingo_metadata)

        return cls(
            data_source=cls.get_data_source_identifier(),
            document_id=external_json["id"],
            jeeves_uid=f"{cls.get_data_source_identifier()}_{external_json['id']}",
            date_time=parse_external_datetime(external_fields["created"]),
            header_text=external_fields["summary"],
            body_text=body_text,
            language=SUPPORTED_LANGUAGES.filter_misc_languages(
                detect_language(body_text if body_text else external_fields["summary"])
            ),
            links=[],
            shake_to_report_category=ShakeToReportCategory.INTERNAL
            if is_shake_to_report
            else ShakeToReportCategory.NON_STR_INTERNAL,
            attachments=external_json.get("attachments", []),
            duolingo_metadata=duolingo_metadata,
            app_version=std_metadata["app_version"],
            course=std_metadata["course"],
            fullstory_url=std_metadata["fullstory_url"],
            os_version=std_metadata["os_version"],
            platform=std_metadata["platform"],
            screen_size=std_metadata["screen_size"],
            screen_content=std_metadata["screen_content"],
            ui_language=std_metadata["ui_language"],
            username=std_metadata["username"],
            issue_key=external_json["key"],
            issue_links=external_fields.get("issuelinks", []),
            issue_type=external_fields.get("issuetype", {}).get("name", ""),
            project=external_fields["project"]["key"],
            linked_duplicate_keys=cls.get_duplicate_keys_from_issue_links(
                external_fields.get("issuelinks", [])
            ),
            creation_date=parse_external_datetime(external_fields["created"]),
            updated_date=parse_external_datetime(external_fields["updated"]),
            resolution_date=parse_external_datetime(external_fields["resolutiondate"])
            if external_fields["resolutiondate"]
            else None,
            status=external_fields["status"]["statusCategory"]["name"],
            resolution=external_fields["resolution"]["name"]
            if external_fields["resolution"]
            else "",
            components=[comp["name"] for comp in external_fields["components"]],
            features=[],
            priority=external_fields["priority"]["name"]
            if external_fields["priority"]
            else "NO PRIORITY GIVEN",
            reporter=external_fields["reporter"]["displayName"],
            assignee=external_fields["assignee"]["displayName"]
            if external_fields["assignee"]
            else "UNASSIGNED",
            comments=[
                cls._deserialize_comment(comment)
                for comment in external_fields["comment"]["comments"]
            ]
            if "comment" in external_fields
            else [],
            labels=external_fields["labels"],
            embedding_vector=DuplicateDetector.calculate_embedding_vector(
                external_fields["summary"]
            ),
        )

    @classmethod
    def deserialize_from_internal_json(cls, internal_json: JSON) -> JeevesDocument:
        """
        Please see parent class for documentation
        """
        return cls(
            data_source=internal_json["data_source"],
            document_id=internal_json["document_id"],
            jeeves_uid=internal_json["jeeves_uid"],
            date_time=parse_external_datetime(internal_json["date_time"])
            if isinstance(internal_json["date_time"], str)
            else internal_json["date_time"],
            header_text=internal_json["header_text"],
            body_text=internal_json["body_text"],
            language=internal_json["language"],
            links=internal_json["links"],
            shake_to_report_category=ShakeToReportCategory[
                internal_json["shake_to_report_category"]
            ],
            attachments=internal_json["attachments"],
            duolingo_metadata=internal_json["duolingo_metadata"],
            app_version=internal_json["app_version"],
            course=internal_json["course"],
            fullstory_url=internal_json["fullstory_url"],
            os_version=internal_json["os_version"],
            platform=internal_json["platform"],
            screen_size=internal_json["screen_size"],
            screen_content=internal_json["screen_content"],
            ui_language=internal_json["ui_language"],
            username=internal_json["username"],
            issue_key=internal_json["issue_key"],
            issue_links=internal_json["issue_links"],
            issue_type=internal_json["issue_type"],
            project=internal_json["project"],
            linked_duplicate_keys=internal_json["linked_duplicate_keys"],
            creation_date=parse_external_datetime(internal_json["creation_date"])
            if isinstance(internal_json["creation_date"], str)
            else internal_json["creation_date"],
            updated_date=parse_external_datetime(internal_json["updated_date"])
            if isinstance(internal_json["updated_date"], str)
            else internal_json["updated_date"],
            resolution_date=parse_external_datetime(internal_json["resolution_date"])
            if isinstance(internal_json["resolution_date"], str)
            else internal_json["resolution_date"],
            status=internal_json["status"],
            resolution=internal_json["resolution"],
            components=internal_json["components"],
            features=internal_json["features"],
            priority=internal_json["priority"],
            reporter=internal_json["reporter"],
            assignee=internal_json["assignee"],
            comments=[cls._deserialize_comment(comment) for comment in internal_json["comments"]],
            labels=internal_json["labels"],
            embedding_vector=internal_json["embedding_vector"],
        )

    @classmethod
    def check_should_index_document(cls, document: JeevesDocument) -> bool:
        """
        Please see parent class for documentation
        """
        # One-line solution for JEEVES-92
        return document.issue_type == "Bug" and super().check_should_index_document(document)

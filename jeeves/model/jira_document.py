"""
Our model for a JIRA issue from the JIRA API
"""

from __future__ import annotations

import datetime
import sys
from typing import Any, Optional, Union

import attr

from jeeves.config.config import SENTENCE_TRANSFORMER_MODEL
from jeeves.config.jira_features import (
    JIRA_AREA_TO_PILLAR,
    JIRA_FEATURE_TO_TEAM,
    JIRA_TEAM_TO_AREA,
    JIRA_TEAM_TO_PROJECT,
    TEAM_TO_FEATURES,
)
from jeeves.lib.duplicate_detector import DuplicateIssueDetector
from jeeves.model.custom_types import JSON
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.quality_score_params import QualityScoreParams
from jeeves.model.shake_to_report_category import ShakeToReportCategory
from jeeves.model.supported_languages import SUPPORTED_LANGUAGES
from jeeves.util.classify import detect_language
from jeeves.util.cleanup import extract_duolingo_metadata_and_body
from jeeves.util.date_util import parse_external_datetime
from jeeves.util.metadata_standardizer import MetaStdizer
from jeeves.util.quality_report_util import CODEBASE_TO_PLATFORM, PROJECT_TO_PLATFORM

_SHAKE_TO_REPORT_MARKER = "Reported with shake-to-report"
_BIRDS_EYE_MARKER = "Reported via Bird's Eye, shake-to-report"

PARENT_BUG_LABEL = "parent_bug"


@attr.s(kw_only=True)
class JiraDocument(JeevesDocument):
    _codebase_field_key = None
    _feature_field_key = None
    _team_field_key = None
    _duplicate_detector = None

    issue_key: str = attr.ib()
    issue_links: list[dict] = attr.ib()
    issue_type: str = attr.ib()
    project: str = attr.ib()
    linked_duplicate_keys: list[str] = attr.ib()
    creation_date: datetime.datetime = attr.ib()
    updated_date: datetime.datetime = attr.ib()
    resolution_date: Optional[datetime.datetime] = attr.ib()
    status: str = attr.ib()
    resolution: str = attr.ib()
    components: list[str] = attr.ib()
    feature_url: str = attr.ib()
    feature: str = attr.ib()
    priority: str = attr.ib()
    reporter: str = attr.ib()
    reporter_email: str = attr.ib()
    assignee: str = attr.ib()
    # Comments is a list of dicts, each dict representing one comment
    # A comment dict contains these keys with corresponding types:
    # author: str, body: str, created: datetime, id: str, updated: datetime
    comments: list[dict[str, Union[str, datetime.datetime]]] = attr.ib()
    labels: list[str] = attr.ib()
    jira_attachments: list[dict[str, str]] = attr.ib()
    parent_issue: Optional[str] = attr.ib()
    child_issues: list[str] = attr.ib()
    is_dev_related: bool = attr.ib()
    area: Optional[str] = attr.ib()
    team: Optional[str] = attr.ib()
    pillar: Optional[str] = attr.ib(default="")
    codebase: Optional[str] = attr.ib()

    # non-indexed fields
    quality_score_params: Optional[QualityScoreParams] = None
    client: Optional[str] = None

    @classmethod
    def _initialize_duplicate_detector(cls):
        if cls._duplicate_detector is None:
            cls._duplicate_detector = DuplicateIssueDetector()

    @staticmethod
    def get_data_source_identifier() -> str:
        """
        Please see parent class for documentation
        """
        return "JIRA"

    @classmethod
    def compress_rich_text(cls, rich_text: JSON) -> str:
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

        # Check to verify that content is in rtt for the types that require it
        if (
            rtt
            in {
                "doc",
                "paragraph",
                "bulletList",
                "orderedList",
                "listItem",
                "mediaGroup",
                "mediaSingle",
            }
            and "content" not in rich_text
        ):
            print(f"No content in rich text {rich_text}. Skipping.")
            return ""

        if rtt == "doc":
            return "\n".join([cls.compress_rich_text(node) for node in rich_text["content"]])

        if rtt == "text":
            return rich_text["text"]

        if rtt == "paragraph":
            subcontent = "".join([cls.compress_rich_text(node) for node in rich_text["content"]])
            return f"{subcontent}\n"

        if rtt == "bulletList":
            list_items = [f"\t- {cls.compress_rich_text(node)}" for node in rich_text["content"]]
            return "".join(list_items)

        if rtt == "orderedList":
            list_items = [
                f"\t{node[0]}. {cls.compress_rich_text(node[1])}"
                for node in enumerate(rich_text["content"], start=1)
            ]
            return "".join(list_items)

        if rtt == "listItem":
            return "".join([cls.compress_rich_text(node) for node in rich_text["content"]])

        if rtt == "hardBreak":
            return "\n"

        if rtt == "mention":
            return rich_text["attrs"]["text"]

        if rtt == "media":
            if "id" in rich_text["attrs"]:
                return rich_text["attrs"]["id"]
            return "<ID NOT FOUND DESPITE BEING REQUIRED IN THE SPEC>"

        if rtt == "mediaGroup" or rtt == "mediaSingle":
            return ", ".join([cls.compress_rich_text(node) for node in rich_text["content"]])

        if rtt == "inlineCard":
            if "url" in rich_text["attrs"]:
                return rich_text["attrs"]["url"]
            return "<JSONLD TO BE IMPLEMENTED LATER>"

        return f"<UNIMPLEMENTED TYPE: {rtt}>"

    @classmethod
    def _deserialize_comment(cls, comment_json: JSON) -> dict[str, Union[str, datetime.datetime]]:
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
            else cls.compress_rich_text(comment_json["body"]),
            "created": parse_external_datetime(comment_json["created"])
            if isinstance(comment_json["created"], str)
            else comment_json["created"],
            "id": comment_json["id"],
            "updated": parse_external_datetime(comment_json["updated"])
            if isinstance(comment_json["updated"], str)
            else comment_json["updated"],
        }

    @classmethod
    def get_duplicate_keys_from_issue_links(cls, issue_links: JSON) -> list[str]:
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
    def set_codebase_field_key(cls, codebase_field_key: str):
        cls._codebase_field_key = codebase_field_key

    @classmethod
    def get_codebase_field_key(cls) -> str:
        return cls._codebase_field_key

    @classmethod
    def set_feature_field_key(cls, feature_field_key: str):
        cls._feature_field_key = feature_field_key

    @classmethod
    def get_feature_field_key(cls) -> str:
        return cls._feature_field_key

    @classmethod
    def set_team_field_key(cls, team_field_key: str):
        cls._team_field_key = team_field_key

    @classmethod
    def get_team_field_key(cls) -> str:
        return cls._team_field_key

    @staticmethod
    def guess_platform(external_fields: dict[str, Any], codebase: str, body_text: str) -> str:
        project = external_fields["project"]["key"]
        if project in PROJECT_TO_PLATFORM:
            return PROJECT_TO_PLATFORM[project]

        if codebase in CODEBASE_TO_PLATFORM:
            return CODEBASE_TO_PLATFORM[codebase]

        body_tokens_rough = body_text.lower().split(" ")
        if "ios" in body_tokens_rough:
            return "iOS"
        if "android" in body_tokens_rough:
            return "Android"
        if "web" in body_tokens_rough:
            return "Web"

        return ""

    @classmethod
    def deserialize_from_external_json(cls, external_json: JSON) -> JiraDocument:
        """
        Please see parent class for documentation
        """
        external_fields: dict[str, Any] = external_json["fields"]

        body_text = (
            cls.compress_rich_text(external_fields["description"])
            if external_fields["description"]
            else ""
        )

        is_shake_to_report = _SHAKE_TO_REPORT_MARKER in body_text
        is_birds_eye_report = _BIRDS_EYE_MARKER in body_text

        duolingo_metadata = {}
        if is_shake_to_report or is_birds_eye_report:
            body_text, duolingo_metadata = extract_duolingo_metadata_and_body(body_text)

        std_metadata = MetaStdizer.get_standardized_metadata(duolingo_metadata)

        # Determine feature, area, and team based on the Jira fields
        codebase_field: Optional[dict[str, Any]] = (
            external_fields.get(cls._codebase_field_key)
            if cls._codebase_field_key is not None
            else None
        )
        feature_field: Optional[dict[str, Any]] = (
            external_fields.get(cls._feature_field_key)
            if cls._feature_field_key is not None
            else None
        )
        team_field: Optional[dict[str, Any]] = (
            external_fields.get(cls._team_field_key) if cls._team_field_key is not None else None
        )

        # If the codebase field is not set, we have no fallback and simply use an empty string
        codebase = codebase_field["value"] if codebase_field is not None else ""
        # If the feature field is not set, we have no fallback and simply use an empty string
        feature = feature_field["value"] if feature_field is not None else ""
        team = None

        # The below is Video Call quality report specific logic.
        # We override the team if the project is in the list of video call projects and the label field contains `vc-triaged`.
        jira_prefix = external_json.get("key", "").split("-")[0]
        for possible_team, prefixes in JIRA_TEAM_TO_PROJECT.items():
            labelsField = external_fields.get("labels", [])
            if jira_prefix in prefixes and "vc-triaged" in labelsField:
                team = possible_team
                break

        # Regular logic if team did not already get set in the special block above
        if not team:
            if team_field and team_field.get("name", "") in TEAM_TO_FEATURES:
                team = team_field.get("name", "")
            else:
                # If the team field is not valid, we can fall back to inferring the team from the feature
                team = JIRA_FEATURE_TO_TEAM.get(feature, "")

        area = JIRA_TEAM_TO_AREA.get(team, "")

        pillar = JIRA_AREA_TO_PILLAR.get(area, "")

        platform = std_metadata["platform"] or cls.guess_platform(
            external_fields, codebase, body_text
        )

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
            jira_attachments=external_fields.get("attachment", []),
            duolingo_metadata=duolingo_metadata,
            app_version=std_metadata["app_version"],
            challenge_id=std_metadata["challenge_id"],
            challenge_prompt_text=std_metadata["challenge_prompt_text"],
            challenge_type=std_metadata["challenge_type"],
            challenge_generator_specific_type=std_metadata["challenge_generator_specific_type"],
            codebase=codebase,
            course=std_metadata["course"],
            fullstory_url=std_metadata["fullstory_url"],
            lesson_number=std_metadata["lesson_number"],
            level_number=std_metadata["level_number"],
            os_version=std_metadata["os_version"],
            platform=platform,
            screen_size=std_metadata["screen_size"],
            screen_content=std_metadata["screen_content"],
            session_bundle_id=std_metadata["session_bundle_id"],
            session_id=std_metadata["session_id"],
            session_type=std_metadata["session_type"],
            skill_id=std_metadata["skill_id"],
            skill_name=std_metadata["skill_name"],
            skill_tree_id=std_metadata["skill_tree_id"],
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
            feature_url=external_fields[cls._feature_field_key]["self"]
            if cls._feature_field_key is not None
            and external_fields[cls._feature_field_key] is not None
            else "",
            feature=feature,
            priority=external_fields["priority"]["name"]
            if external_fields["priority"]
            else "NO PRIORITY GIVEN",
            reporter=external_fields["reporter"]["displayName"],
            reporter_email=external_fields["reporter"].get("emailAddress", ""),
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
            embeddings={},
            experiment_conditions={},
            user_id=std_metadata["user_id"],
            parent_issue=None,
            child_issues=[],
            is_dev_related=False,
            area=area,
            team=team,
            pillar=pillar,
        )

    @classmethod
    def deserialize_from_internal_json(cls, internal_json: JSON) -> JiraDocument:
        if internal_json.get("feature_url") is None:
            print(f"feature_url is missing for {internal_json['issue_key']}", file=sys.stderr)
        """
        Please see parent class for documentation
        """
        if not isinstance(internal_json, dict):
            return
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
            jira_attachments=internal_json.get("jira_attachments", []),
            duolingo_metadata=internal_json["duolingo_metadata"],
            app_version=internal_json["app_version"],
            challenge_id=internal_json.get("challenge_id", ""),
            challenge_prompt_text=internal_json.get("challenge_prompt_text", ""),
            challenge_type=internal_json.get("challenge_type", ""),
            challenge_generator_specific_type=internal_json.get(
                "challenge_generator_specific_type", ""
            ),
            codebase=internal_json.get("codebase"),
            course=internal_json["course"],
            fullstory_url=internal_json["fullstory_url"],
            lemmatized_terms=internal_json.get("lemmatized_terms", []),
            lesson_number=internal_json.get("lesson_number", ""),
            level_number=internal_json.get("level_number", ""),
            os_version=internal_json["os_version"],
            platform=internal_json["platform"],
            screen_size=internal_json["screen_size"],
            screen_content=internal_json["screen_content"],
            session_bundle_id=internal_json.get("session_bundle_id", ""),
            session_id=internal_json.get("session_id", ""),
            session_type=internal_json.get("session_type", ""),
            skill_id=internal_json.get("skill_id", ""),
            skill_name=internal_json.get("skill_name", ""),
            skill_tree_id=internal_json.get("skill_tree_id", ""),
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
            feature_url=internal_json.get("feature_url", ""),
            feature=internal_json.get("feature", ""),
            priority=internal_json["priority"],
            reporter=internal_json["reporter"],
            reporter_email=internal_json.get("reporter_email", ""),
            assignee=internal_json["assignee"],
            comments=[
                cls._deserialize_comment(comment) for comment in internal_json.get("comments", [])
            ],
            labels=internal_json["labels"],
            embeddings=internal_json.get("embeddings", {}),
            experiment_conditions=internal_json.get("experiment_conditions", {}),
            user_id=internal_json.get("user_id", ""),
            parent_issue=internal_json.get("parent_issue"),
            child_issues=internal_json.get("child_issues", []),
            is_dev_related=internal_json.get("is_dev_related", False),
            area=internal_json.get("area"),
            team=internal_json.get("team"),
            pillar=internal_json.get("pillar", ""),
        )

    @classmethod
    def check_should_index_document(cls, document: JeevesDocument) -> bool:
        """
        Please see parent class for documentation
        """
        # One-line solution for JEEVES-92
        return document.issue_type == "Bug" and super().check_should_index_document(document)

    @classmethod
    def get_parent_category_mappings(cls) -> dict[str, str]:
        """
        Returns a mapping of category names used in parent documents, and which
        field names those category names represent.

        Returns:
            A dictionary from strings to strings, representing the above mapping
        """
        parent_category_mapping = {
            "APP VERSIONS": "app_version",
            "PLATFORMS": "platform",
            "COURSES": "course",
            "INTERFACE LANGUAGES": "ui_language",
            "OPERATING SYSTEMS": "os_version",
            "AREAS": "components",
        }
        return parent_category_mapping

    @classmethod
    def is_group_parent(cls, target: JeevesDocument) -> bool:
        """
        Given a JeevesDocument object, determines if it should be considered
        a parent issue of some group of duplicate issues.

        Parameters:
            target: The JeevesDocument object we want to test

        Returns:
            True if the input should be considered a parent issue, else False.
        """
        # First we need to check that the generic JeevesDocument is for Jira.
        # Using an isinstance test here is annoying because we're inside the
        # class we're testing for, so we check the data_source instead.
        if target.data_source != cls.get_data_source_identifier():
            return False

        return "parent_bug" in target.labels

    @classmethod
    def calculate_embedding(cls, target: JiraDocument) -> list[float]:
        """
        Given a JeevesDocument object, calculates the SentenceTransformer embedding vector

        Parameters:
            target: The JeevesDocument object we want to have an embedding vector for
        """
        assert target.data_source == cls.get_data_source_identifier()

        if target.embeddings and target.embeddings.get(SENTENCE_TRANSFORMER_MODEL):
            return target.embeddings.get(SENTENCE_TRANSFORMER_MODEL)

        cls._initialize_duplicate_detector()
        return (
            cls._duplicate_detector.calculate_embedding_vector(
                f"{target.header_text}. {target.body_text}"
            )
            if cls._duplicate_detector is not None
            else []
        )

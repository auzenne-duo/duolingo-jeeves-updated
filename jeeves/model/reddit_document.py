"""
Our model for an app store review from the Reddit Pushshift API
"""
import attr

from jeeves.model.custom_types import JSON
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.shake_to_report_category import ShakeToReportCategory
from jeeves.util.date_util import parse_external_datetime


@attr.s(kw_only=True)
class RedditDocument(JeevesDocument):
    author: str = attr.ib()

    @staticmethod
    def get_data_source_identifier() -> str:
        """
        Please see parent class for documentation
        """
        return "Reddit"

    @classmethod
    def deserialize_from_external_json(cls, external_json: JSON) -> JeevesDocument:
        """
        Please see parent class for documentation
        """
        # TODO: Add text from top comments
        body_text = external_json["selftext"]

        return cls(
            data_source=cls.get_data_source_identifier(),
            document_id=external_json["id"],
            jeeves_uid=f"{cls.get_data_source_identifier()}_{external_json['id']}",
            date_time=parse_external_datetime(external_json["utc_datetime_str"]),
            header_text=external_json["title"],
            body_text=body_text,
            language="en",
            links=[f'https://reddit.com{external_json["permalink"]}'],
            shake_to_report_category=ShakeToReportCategory.NON_STR_EXTERNAL,
            attachments=[],
            duolingo_metadata={},
            app_version="",
            course="",
            fullstory_url="",
            os_version="",
            platform="",
            screen_size="",
            screen_content="",
            ui_language="",
            username="",
            author=external_json["author"],
            embeddings={},
            experiment_conditions={},
            user_id="",
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
            author=internal_json["author"],
            embeddings=internal_json.get("embeddings", {}),
            experiment_conditions=internal_json.get("experiment_conditions", {}),
            user_id=internal_json.get("user_id", ""),
        )

    @classmethod
    def check_should_index_document(cls, document: JeevesDocument) -> bool:
        """
        Please see parent class for documentation
        """

        return super().check_should_index_document(document)

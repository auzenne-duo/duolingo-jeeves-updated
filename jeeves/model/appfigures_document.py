"""
Our model for an app store review from the AppFigures API
"""
import attr

from jeeves.model.custom_types import JSON
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.util.classify import detect_language
from jeeves.util.date_util import parse_external_datetime


@attr.s(kw_only=True)
class AppfiguresDocument(JeevesDocument):

    author: str = attr.ib()
    stars: float = attr.ib()
    iso: str = attr.ib()
    version: str = attr.ib()
    deleted: bool = attr.ib()
    product_id: str = attr.ib()
    store: str = attr.ib()

    @staticmethod
    def get_data_source_identifier() -> str:
        """
        Please see parent class for documentation
        """
        return "AppFigures"

    @classmethod
    def deserialize_from_external_json(cls, external_json: JSON) -> JeevesDocument:
        """
        Please see parent class for documentation
        """
        # TODO: After web GUI is redesigned, add links as appropriate

        return cls(
            data_source=cls.get_data_source_identifier(),
            document_id=external_json["id"],
            date_time=parse_external_datetime(external_json["date"]),
            header_text=external_json["original_title"],
            body_text=external_json["original_review"],
            language=detect_language(external_json["original_review"]),
            links=[],
            author=external_json["author"],
            stars=float(external_json["stars"]),
            iso=external_json["iso"],
            version=external_json["version"],
            deleted=bool(external_json["deleted"]),
            product_id=external_json["product_id"],
            store=external_json["store"],
        )

    @classmethod
    def deserialize_from_internal_json(cls, internal_json: JSON) -> JeevesDocument:
        """
        Please see parent class for documentation
        """
        return cls(
            data_source=internal_json["data_source"],
            document_id=internal_json["document_id"],
            date_time=internal_json["date_time"],
            header_text=internal_json["header_text"],
            body_text=internal_json["body_text"],
            language=internal_json["language"],
            links=internal_json["links"],
            author=internal_json["author"],
            stars=internal_json["stars"],
            iso=internal_json["iso"],
            version=internal_json["version"],
            deleted=bool(internal_json["deleted"]),
            product_id=internal_json["product_id"],
            store=internal_json["store"],
        )

    @classmethod
    def check_should_index_document(cls, document: JeevesDocument) -> bool:
        """
        Please see parent class for documentation
        """

        return super().check_should_index_document(document)

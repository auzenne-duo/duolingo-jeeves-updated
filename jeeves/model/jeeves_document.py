"""
Our model for a general, abstract document
"""

from __future__ import annotations

import datetime
from abc import ABC, abstractmethod
from typing import Optional

import attr

from jeeves.model.custom_types import JSON
from jeeves.model.shake_to_report_category import ShakeToReportCategory
from jeeves.model.supported_languages import SUPPORTED_LANGUAGES


@attr.s(kw_only=True)
class JeevesDocument(ABC):
    data_source: str = attr.ib()
    document_id: str = attr.ib()
    jeeves_uid: str = attr.ib()
    date_time: datetime.datetime = attr.ib()
    header_text: str = attr.ib(default="")
    body_text: str = attr.ib()
    is_bug: bool = attr.ib(default=True)
    language: str = attr.ib()
    lemmatized_terms: list[str] = attr.ib(default=[])
    links: list[str] = attr.ib(default=[])
    shake_to_report_category: ShakeToReportCategory = attr.ib()
    attachments: list[str] = attr.ib()
    duolingo_metadata: dict[str, JSON] = attr.ib()
    app_version: str = attr.ib()
    challenge_id: str = attr.ib(default="")
    challenge_prompt_text: str = attr.ib(default="")
    challenge_type: str = attr.ib(default="")
    challenge_generator_specific_type: str = attr.ib(default="")
    course: str = attr.ib()
    fullstory_url: str = attr.ib()
    lesson_number: str = attr.ib(default="")
    level_number: str = attr.ib(default="")
    os_version: str = attr.ib()
    platform: str = attr.ib()
    screen_size: str = attr.ib()
    screen_content: str = attr.ib()
    session_bundle_id: str = attr.ib(default="")
    session_id: str = attr.ib(default="")
    session_type: str = attr.ib(default="")
    skill_id: str = attr.ib(default="")
    skill_name: str = attr.ib(default="")
    skill_tree_id: str = attr.ib(default="")
    ui_language: str = attr.ib()
    username: str = attr.ib()
    embeddings: dict[str, list[float]] = attr.ib(default={})
    experiment_conditions: dict[str, str] = attr.ib()
    user_id: str = attr.ib(default="")

    # It is VERY IMPORTANT, when you add attributes to a subclass of this class,
    # that the attribute names are distinct from each other attribute name across
    # all other subclasses of this class. If two subclasses share an attribute name,
    # when they both get tossed into OpenSearch, they will be treated as the same
    # field. If they have different datatypes this will cause an exception. If they
    # have the same datatype, you probably don't want them being treated identically
    # in all cases anyway.

    @staticmethod
    @abstractmethod
    def get_data_source_identifier() -> str:
        """
        Return a string that represents what data source documents of a specific
        type came from. Should be overridden in subclasses as appropriate.
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def deserialize_from_external_json(cls, external_json: JSON) -> JeevesDocument:
        """
        Create a document object from JSON that was received from a source
        external to Jeeves (i.e. a data source API).
        Should be overridden in subclasses to suit the needs of particular
        document formats.

        Parameters:
            external_json: JSON blob received from an external source.

        Returns:
            A document object with the same content as the provided JSON
        """
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def deserialize_from_internal_json(cls, internal_json: JSON) -> JeevesDocument:
        """
        Create a document object from JSON that was received from somewhere
        within Jeeves (likely OpenSearch).
        Should be overridden in subclasses to suit the needs of particular
        document formats.

        Parameters:
            external_json: JSON blob received from an internal source.

        Returns:
            A document object with the same content as the provided JSON
        """
        raise NotImplementedError

    @classmethod
    def serialize_to_json(
        cls, document: JeevesDocument, subserial_filter: Optional[list[str]] = None
    ) -> JSON:
        """
        Convert a document object into JSON. May be overridden as needed.
        If provided with a list of fields, JSON output will only contain
        the listed fields.

        Parameters:
            document: The document we wish to convert to JSON
            subserial_filter: An optional list of fields to not include in the
                              serialization.

        Returns:
            A JSON representation of the provided object.
        """
        retval = {}

        if subserial_filter:
            retval = attr.asdict(document, filter=lambda attr, _: attr.name not in subserial_filter)
        else:
            retval = attr.asdict(document)

        if "shake_to_report_category" in retval:
            retval["shake_to_report_category"] = document.shake_to_report_category.value

        return retval

    @classmethod
    @abstractmethod
    def check_should_index_document(cls, document: JeevesDocument) -> bool:
        """
        Checks if a given document should be indexed or not.
        This is meant to be called during document download; documents that
        do not pass this check should not be indexed and instead discarded.
        Should be overridden in subclasses to suit the needs of particular
        document formats.

        Parameters:
            document: The document we want to check prior to indexing

        Returns:
            True if we should index the given document, otherwise False
        """
        # Having non-empty abstract methods is explicitly allowed by the Python spec
        return document.language in SUPPORTED_LANGUAGES.__members__

    @classmethod
    def generate_opensearch_internal_id(cls, document: JeevesDocument) -> str:
        """
        Generates a string to be used as a unique internal identifier for a
        given document. Previously, the internal identifier in question was
        re-used from the more human-friendly `jeeves_uid` field, which was in
        turn generated based on a document's data source and source-specific
        identifier. However, some data sources were returning documents with
        nearly identical contents but different source-specific identifiers.
        After some research, the recommendation in the OpenSearch
        community is to leverage the uniqueness of OpenSearch's internal
        ID field to prevent duplicates, since attempting to index a document
        using an internal ID that already exists will just overwrite the
        existing document instead of creating a new entry. As such, if a data
        source can potentially return duplicate records with different
        identifiers in an undesired way, override this method as appropriate
        to prevent this duplication.

        Parameters:
            document: The document for which we want to generate an identifier.

        Returns:
            A string to be used as an identifier that can be leveraged for
            document de-duplication if needed.
        """
        return document.jeeves_uid

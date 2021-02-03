"""
Our model for a general, abstract document
"""

from abc import ABC, abstractmethod
import datetime
from typing import Dict, List, Optional

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
    language: str = attr.ib()
    links: List[str] = attr.ib(default=[])
    shake_to_report_category: ShakeToReportCategory = attr.ib()
    attachments: List[str] = attr.ib()
    duolingo_metadata: Dict[str, JSON] = attr.ib()
    app_version: str = attr.ib()
    course: str = attr.ib()
    fullstory_url: str = attr.ib()
    os_version: str = attr.ib()
    platform: str = attr.ib()
    screen_size: str = attr.ib()
    screen_content: str = attr.ib()
    ui_language: str = attr.ib()
    username: str = attr.ib()

    # It is VERY IMPORTANT, when you add attributes to a subclass of this class,
    # that the attribute names are distinct from each other attribute name across
    # all other subclasses of this class. If two subclasses share an attribute name,
    # when they both get tossed into Elasticsearch, they will be treated as the same
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
    def deserialize_from_external_json(cls, external_json: JSON) -> "JeevesDocument":
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
    def deserialize_from_internal_json(cls, internal_json: JSON) -> "JeevesDocument":
        """
        Create a document object from JSON that was received from somewhere
        within Jeeves (likely Elasticsearch).
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
        cls, document: "JeevesDocument", subserial_filter: Optional[List[str]] = None
    ) -> JSON:
        """
        Convert a document object into JSON. May be overridden as needed.
        If provided with a list of fields, JSON output will only contain
        the listed fields.

        Parameters:
            document: The document we wish to convert to JSON
            subserial_filter: An optional list of fields to restrict
                              the serialization to.

        Returns:
            A JSON representation of the provided object.
        """

        retval = {}

        if subserial_filter:
            retval = attr.asdict(document, filter=lambda attr, _: attr.name in subserial_filter)
        else:
            retval = attr.asdict(document)

        if "shake_to_report_category" in retval:
            retval["shake_to_report_category"] = document.shake_to_report_category.value

        return retval

    @classmethod
    @abstractmethod
    def check_should_index_document(cls, document: "JeevesDocument") -> bool:
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

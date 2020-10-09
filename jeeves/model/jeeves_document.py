"""
Our model for a general, abstract document
"""

from abc import ABC, abstractmethod
import datetime
from typing import List, Optional

import attr

from jeeves.model.custom_types import JSON


@attr.s(kw_only=True)
class JeevesDocument(ABC):

    data_source: str = attr.ib()
    document_id: str = attr.ib()
    date_time: datetime.datetime = attr.ib()
    header_text: str = attr.ib(default="")
    body_text: str = attr.ib()
    language: str = attr.ib()
    links: List[str] = attr.ib(default=[])

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
        if subserial_filter:
            return attr.asdict(document, filter=lambda attr, _: attr.name in subserial_filter)
        return attr.asdict(document)

    @staticmethod
    @abstractmethod
    def check_should_index_document(document: "JeevesDocument") -> bool:
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
        raise NotImplementedError

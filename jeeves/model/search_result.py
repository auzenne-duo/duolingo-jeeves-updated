"""
Models for the results of GPT Search or Sentiment Search
"""

from dataclasses import asdict, dataclass
from typing import Any, List, Optional, cast

from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.zendesk_document import ZendeskDocument


@dataclass
class DocumentContent:
    """
    The localized content of a JeevesDocument to display in a table cell in the frontend
    """

    body: str
    title: str

    def to_dict(self):
        return asdict(self)


@dataclass
class SearchResult:
    """
    A JeevesDocument that matches the search query
    """

    datetime: str
    origin: str
    original_text: DocumentContent
    score: float  # Cosine similarity score for GPT Search or sentiment score for Sentiment Search
    uid: str
    url: Optional[str]  # TODO: Add a link to all Jeeves documents so they can be made clickable

    @classmethod
    def get_origin(cls, document: JeevesDocument) -> str:
        origin = document.data_source
        if origin.lower() == "zendesk":
            zdoc = cast(ZendeskDocument, document)
            channel = zdoc.via["channel"]
            if channel.lower() == "twitter":
                origin = "Twitter (via Zendesk)"
        return origin

    def to_dict(self):
        return asdict(self)


@dataclass
class SearchResults:
    """
    A collection of search results that we will return to the frontend
    """

    lucene_query: List[str]
    query: str
    results: List[Any]

    def to_dict(self):
        return asdict(self)

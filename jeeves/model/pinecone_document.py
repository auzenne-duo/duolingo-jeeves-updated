"""
Our model for inserting Jeeves Documents into Pinecone
"""
import logging
from abc import ABC
from typing import List, Optional

import attr

from jeeves.config.config import GPT_EMBEDDING_MODEL
from jeeves.model.jeeves_document import JeevesDocument

LOG = logging.getLogger(__name__)


@attr.s(kw_only=True)
class PineconeDocument(ABC):
    id: str = attr.ib()
    values: List[float] = attr.ib()
    data_source: str = attr.ib()

    def serialize(self) -> dict:
        return {"id": self.id, "values": self.values, "metadata": {"data_source": self.data_source}}

    @staticmethod
    def convert_jeeves_doc_to_pinecone_doc(
        ticket: JeevesDocument, embedding_model: str = GPT_EMBEDDING_MODEL
    ) -> Optional["PineconeDocument"]:
        """
        Convert a single JeevesDocument to a format Pinecone accepts.
        """
        jeeves_uid = ticket.jeeves_uid
        embedding = ticket.embeddings.get(embedding_model)
        data_source = ticket.data_source
        if jeeves_uid is not None and embedding is not None and data_source is not None:
            return PineconeDocument(id=jeeves_uid, values=embedding, data_source=data_source)
        else:
            return None

    @staticmethod
    def convert_jeeves_docs_to_pinecone_docs(
        tickets: List[JeevesDocument]
    ) -> List["PineconeDocument"]:
        """
        Convert a list of JeevesDocuments to a format Pinecone accepts.
        """
        pinecone_docs = []
        failed_conversion_count = 0
        for ticket in tickets:
            pinecone_doc = PineconeDocument.convert_jeeves_doc_to_pinecone_doc(ticket)
            if pinecone_doc is not None:
                pinecone_docs.append(pinecone_doc)
            else:
                failed_conversion_count += 1
            if failed_conversion_count != 0 and failed_conversion_count % 10 == 0:
                LOG.debug(
                    f"Failed to convert {failed_conversion_count} tickets to Pinecone documents"
                )
        return pinecone_docs

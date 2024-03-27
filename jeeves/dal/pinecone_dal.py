"""
DAL for accessing pinecone index using the pinecone api
"""

import itertools
import logging
import os
from typing import Any, Dict, List, Optional

from duolingo_base.config import Config
from pinecone import Pinecone, PineconeException

from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.pinecone_document import PineconeDocument

_config = Config.load_config()
LOG = logging.getLogger(__name__)


class PineconeDAL:
    """
    DAL for interacting with the Pinecone Vector Database.
    """

    def __init__(self) -> None:
        # To run this locally set your PINECONE_API_KEY and PINECONE_INDEX_NAME in your environment
        _PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
        _PINECONE_INDEX_NAME = os.environ.get("PINECONE_INDEX_NAME")
        self._pc = Pinecone(api_key=_PINECONE_API_KEY)
        self._indexname = _PINECONE_INDEX_NAME
        self._index = self._pc.Index(self._indexname)

    def bulk_index_tickets(self, tickets: List[JeevesDocument]) -> None:
        """
        Store multiple tickets in Pinecone.
        """
        # Convert tickets to Pinecone representation
        pinecone_docs_to_upload = PineconeDocument.convert_jeeves_docs_to_pinecone_docs(tickets)

        if len(pinecone_docs_to_upload) == 0:
            raise ValueError("No documents to upload to Pinecone")

        serialized_pinecone_docs = [doc.serialize() for doc in pinecone_docs_to_upload]

        # Chunk data for batch upload
        def get_chunks(iterable, batch_size=100):
            it = iter(iterable)
            chunk = tuple(itertools.islice(it, batch_size))
            while chunk:
                yield chunk
                chunk = tuple(itertools.islice(it, batch_size))

        documents_inserted_count = 0
        for ids_vectors_chunk in get_chunks(serialized_pinecone_docs, batch_size=100):
            response = self._index.upsert(vectors=ids_vectors_chunk)
            documents_inserted_count += response["upserted_count"]
        if documents_inserted_count != len(pinecone_docs_to_upload):
            LOG.error(
                f"Failed to insert all documents into Pinecone. Expected {len(pinecone_docs_to_upload)} "
                f"documents to be inserted, but only {documents_inserted_count} were inserted."
            )
        else:
            LOG.info(
                f"Successfully inserted {documents_inserted_count} documents into {self._indexname} on Pinecone."
            )

    def execute_arbitrary_query(
        self,
        query_vector: List[float],
        include_metadata: bool = False,
        include_values: bool = False,
        metadata_filter: Optional[Dict[str, Any]] = None,
        top_k: int = 5,
    ) -> Dict[str, float]:
        """
        Execute an arbitrary query against the Pinecone index.

        Parameters:
            query_vector (List[float]): The vector to search against.
            include_metadata (bool): Whether to include the metadata in the response. This can slow down the response.
            include_values (bool): Whether to include the values in the response. This can slow down the response.
            metadata_filter (Optional[Dict[str, Any]]): Optional. A metadata filter to apply to the query.
            top_k (int): The number of results to return.

        Returns:
            Dict[str, float]: A dictionary of Pinecone results where the key is the
            document id and the value is the cosine similarity score.
        """
        try:
            if filter is None:
                response = self._index.query(
                    vector=query_vector,
                    top_k=top_k,
                    include_values=include_values,
                    include_metadata=include_metadata,
                )
            else:
                response = self._index.query(
                    vector=query_vector,
                    top_k=top_k,
                    filter=metadata_filter,
                    include_values=include_values,
                    include_metadata=include_metadata,
                )

            id_to_score_mapper = {}
            for match in response["matches"]:
                id_to_score_mapper[match["id"]] = match["score"]

            return id_to_score_mapper
        except PineconeException as e:
            LOG.error(
                f"Failed to execute arbitrary query against Pinecone index {self._indexname}: {e}"
            )

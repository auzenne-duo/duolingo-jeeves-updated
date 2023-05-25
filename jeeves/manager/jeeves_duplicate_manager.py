from datetime import timedelta
from typing import Dict, List

from duolingo_base.util import registry

from jeeves.dal.elasticsearch_interface import ElasticsearchDAL
from jeeves.model.jeeves_document import JeevesDocument


@registry.bind(elasticsearch_dal=registry.reference(ElasticsearchDAL))
class JeevesDuplicateManager:
    def __init__(self, elasticsearch_dal: ElasticsearchDAL):
        self._esd = elasticsearch_dal

    def dedup_document_batch(self, documents: List[JeevesDocument]) -> List[JeevesDocument]:
        documents_to_skip_dedup: List[JeevesDocument] = []
        deduped_documents: Dict[str, JeevesDocument] = {}
        for doc in documents:
            if doc.data_source != "Zendesk" or doc.via["channel"] != "email":
                documents_to_skip_dedup.append(doc)
                continue
            # This will mark two documents as duplicates as long as this concatenation is the same,
            # even if the individual fields are different. But, in that case,
            # we're still getting all of the relevant information in one way or another.
            doc_key = f'{doc.via["source"]["from"]["address"]} {doc.header_text} {doc.body_text}'
            if not doc_key in deduped_documents.keys():
                deduped_documents[doc_key] = doc

        return documents_to_skip_dedup + list(deduped_documents.values())

    def recent_duplicate_exists(self, doc: JeevesDocument) -> bool:
        # We only check for duplicate emails and tweets for now.
        if doc.data_source != "Zendesk":
            return False
        if doc.via["channel"] == "email":
            return self.recent_duplicate_email_exists(doc)
        if doc.via["channel"] == "twitter":
            return self._esd.check_if_duplicate_tweet(doc)
        return False

    def recent_duplicate_email_exists(self, doc: JeevesDocument) -> bool:
        def _clean_up_query_string(query_string):
            query_string.replace('"', " ")

        # See details on query syntax here
        # https://www.elastic.co/guide/en/elasticsearch/reference/current/query-dsl-query-string-query.html#query-string-syntax
        # Note that this searches for documents whose fields CONTAIN their respective search terms.
        query = (
            f'header_text: "{_clean_up_query_string(doc.header_text)}"'
            + f' AND body_text: "{_clean_up_query_string(doc.body_text)}"'
            + f' AND via.source.from.address: "{doc.via["source"]["from"]["address"]}"'
            + f' AND NOT jeeves_uid: "{doc.jeeves_uid}"'
        )
        return (
            len(
                self._esd.get_recent_paginated_tickets(
                    lang=doc.language,
                    word=query,
                    limit=1,
                    start_time=doc.date_time - timedelta(hours=24),
                )
            )
            > 0
        )

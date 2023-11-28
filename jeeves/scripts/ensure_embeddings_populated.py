import sys

import rollbar

from jeeves import apply_registry, close_registry, registry as app_registry
from jeeves.config.config import GPT_EMBEDDING_MODEL
from jeeves.dal.opensearch_interface import OpenSearchDAL
from jeeves.lib.identifier_manager_mapping import IDManagerMap

_BULK_INDEX_BATCH_SIZE = 20


if __name__ == "__main__":
    apply_registry()
    try:
        print("Checking for missing embeddings")
        query = {"size": 1000, "query": {"range": {"date_time": {"gte": "now-6M"}}}}
        document_list = []
        for i, doc in enumerate(app_registry(OpenSearchDAL).scroll_arbitrary_query(query)):
            if GPT_EMBEDDING_MODEL not in doc["_source"].get("embeddings"):
                document_list.append(
                    IDManagerMap.get_manager_for_identifier(doc["_source"]["data_source"])
                    .get_managed_document_type()
                    .deserialize_from_internal_json(doc["_source"])
                )
            if i % 10000 == 0:
                print(f"Scrolled to document {i}, found {len(document_list)} missing embeddings")

            if len(document_list) >= _BULK_INDEX_BATCH_SIZE:
                app_registry(OpenSearchDAL).bulk_index_tickets(document_list)
                document_list = []

        app_registry(OpenSearchDAL).bulk_index_tickets(document_list)
        print("Done checking for missing embeddings")
    except:
        rollbar.report_exc_info(sys.exc_info())
    finally:
        close_registry()

import json
import sys

import rollbar
from duolingo_base.config import Config
from duolingo_base.dal import sqs

import jeeves.lib.ticket_crawler as tc
from jeeves.dal.elasticsearch_interface import ElasticDAL
from jeeves.lib.identifier_manager_mapping import IDManagerMap
from jeeves.manager.jeeves_duplicate_manager import JeevesDuplicateManager

_config = Config.load_config()
_config.apply_logging()
_config.apply_rollbar()

_BATCH_GROUP_SIZE = 100

"""
This script is responsible for consuming documents from the verify/index pipeline break,
aggregating them into groups,
checking each document to see if a recent, similar document already exists,
and indexing the new documents into Elasticsearch.
"""


def _message_to_document(message):
    document_json = json.loads(message.message_body)
    data_source = document_json["data_source"]
    doc_class = IDManagerMap.get_manager_for_identifier(data_source).get_managed_document_type()
    return doc_class.deserialize_from_internal_json(document_json)


if __name__ == "__main__":
    try:
        sqs_client = sqs.SQSClient(
            _config.get_nested(["sqs_verify_index_pipeline", "queue_url"]),
            region_name=_config.get_nested(["sqs_verify_index_pipeline", "region_name"]),
            endpoint_url=_config.get_nested(["sqs_verify_index_pipeline", "endpoint_url"]),
        )

        duplicate_manager = JeevesDuplicateManager(ElasticDAL)

        batch_list = []
        while True:
            messages = sqs_client.receive_messages()
            print(f"Received {len(messages)} messages in batch", flush=True)
            documents = [_message_to_document(m) for m in messages]
            documents_deduped = duplicate_manager.dedup_document_batch(documents)
            for doc in documents_deduped:
                if doc.check_should_index_document(
                    doc
                ) and not duplicate_manager.recent_duplicate_exists(doc):
                    batch_list.append(doc)

            if messages:
                sqs_client.delete_messages(messages)

            if len(batch_list) >= _BATCH_GROUP_SIZE:
                tc.perform_checkpoint(batch_list)
                batch_list = []
    except:
        rollbar.report_exc_info(sys.exc_info())

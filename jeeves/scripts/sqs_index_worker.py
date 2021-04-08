import json


from duolingo_base.config import Config
from duolingo_base.dal import sqs

from jeeves.lib.identifier_manager_mapping import IDManagerMap
import jeeves.lib.ticket_crawler as tc


_config = Config.load_config()

_BATCH_GROUP_SIZE = 100

"""
This script is responsible for consuming documents from the verify/index
pipeline break, aggregating them into groups, indexing them into Elasticsearch,
and performing spike detection based on their contents.
"""

if __name__ == "__main__":
    sqs_client = sqs.SQSClient(
        _config.get_nested(["sqs_verify_index_pipeline", "queue_url"]),
        region_name=_config.get_nested(["sqs_verify_index_pipeline", "region_name"]),
        endpoint_url=_config.get_nested(["sqs_verify_index_pipeline", "endpoint_url"]),
    )

    batch_list = []
    while True:
        messages = sqs_client.receive_messages()
        print(f"Received {len(messages)} messages in batch", flush=True)
        for m in messages:
            document_json = json.loads(m.message_body)
            data_source = document_json["data_source"]
            doc_class = IDManagerMap.get_manager_for_identifier(
                data_source
            ).get_managed_document_type()
            doc = doc_class.deserialize_from_internal_json(document_json)
            if doc.check_should_index_document(doc):
                batch_list.append(doc)

        if messages:
            sqs_client.delete_messages(messages)

        if len(batch_list) >= _BATCH_GROUP_SIZE:
            tc.perform_checkpoint(batch_list)
            batch_list = []

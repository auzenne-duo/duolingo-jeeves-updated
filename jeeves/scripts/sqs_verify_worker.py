import json
import random
from typing import List

from duolingo_base.config import Config
from duolingo_base.dal import sqs

from jeeves.lib.identifier_manager_mapping import IDManagerMap
from jeeves.util.json_encoder import JeevesJSONEncoder

_config = Config.load_config()

"""
This script is responsible for receiving JSON representing raw external
documents from the download/verify pipeline SQS queue, converting them into
a JeevesDocument representation, verifying that their contents are appropriate
for indexing, and finally forwarding them to the verify/index pipeline queue.
"""


def _check_for_data_source(messages: List[sqs.SQSMessage]) -> bool:
    """
    Determines if a batch of received messages is not empty, and if all messages
    in that batch contain a data_source attribute.

    This check is necessary because, as far as I'm able to tell, AWS SQS can
    sometimes just decide to not return all attributes for a message, even if
    one or more of those attributes was explicitly requested.

    Parameters:
        messages: Batch of SQS messages returned from receive_messages

    Returns:
        True if all messages in the batch have a message attribute with name
        'data_source' and the batch is non-empty, otherwise False
    """

    for m in messages:
        if not m.message_attributes:
            return False
        if not any([msg_attr.name == "data_source" for msg_attr in m.message_attributes]):
            return False
    return bool(messages)


if __name__ == "__main__":
    sqs_client_input = sqs.SQSClient(
        _config.get_nested(["sqs_download_verify_pipeline", "queue_url"]),
        region_name=_config.get_nested(["sqs_download_verify_pipeline", "region_name"]),
        endpoint_url=_config.get_nested(["sqs_download_verify_pipeline", "endpoint_url"]),
    )
    sqs_client_output = sqs.SQSClient(
        _config.get_nested(["sqs_verify_index_pipeline", "queue_url"]),
        region_name=_config.get_nested(["sqs_verify_index_pipeline", "region_name"]),
        endpoint_url=_config.get_nested(["sqs_verify_index_pipeline", "endpoint_url"]),
    )

    while True:
        messages = sqs_client_input.receive_messages(MessageAttributeNames=["All"])

        # If one or more received messages are missing their data_source,
        # continue to next loop iteration so we can query this same batch later
        if not _check_for_data_source(messages):
            continue

        passable_docs = []
        for m in messages:
            message_attrs = m.message_attributes
            if not message_attrs:
                continue
            manager_name = ""
            for m_attr in message_attrs:
                if m_attr.name == "data_source":
                    manager_name = m_attr.value
            manager = IDManagerMap.get_manager_for_identifier(manager_name)
            if not manager:
                continue
            doc_json = json.loads(m.message_body)
            processed_doc = manager.process_document(doc_json)
            if processed_doc:
                passable_docs.append(processed_doc)

        output_messages = [
            sqs.SQSMessage(
                message_id=f"{doc.jeeves_uid}_{random.randint(1,100000)}",
                message_body=json.dumps(doc.serialize_to_json(doc), cls=JeevesJSONEncoder),
            )
            for doc in passable_docs
        ]
        if output_messages:
            sqs_client_output.send_messages(output_messages)

        if messages:
            sqs_client_input.delete_messages(messages)

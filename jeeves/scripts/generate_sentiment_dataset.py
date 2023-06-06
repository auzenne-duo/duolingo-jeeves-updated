"""
Script for generating a dataset from real Jeeves data as a baseline measurement for positive and negative labels. Saves train, test, and validation sets to JSON files
"""
import datetime
import json
import os
import random
from typing import List

from jeeves import registry as app_registry
from jeeves.dal.opensearch_interface import OpenSearchDAL
from jeeves.lib.identifier_manager_mapping import IDManagerMap
from jeeves.model.annotated_document import AnnotatedDocument
from jeeves.model.jeeves_document import JeevesDocument

TRAIN_SPLIT = 0.8
TEST_SPLIT = 0.1
VALIDATE_SPLIT = 0.1
DATASET_SIZE = 10
DOCUMENT_LANGUAGE = "en"
SEED = "1182022"
DATA_SOURCE = (
    "all"  # use 'all' to query from all data sources otherwise use the name of the desired source
)

assert TEST_SPLIT + TRAIN_SPLIT + VALIDATE_SPLIT == 1


def serialize_labeled_data_to_json(file_name: str, labeled_data: List[AnnotatedDocument]) -> None:
    """
    Store list of AnnotatedDocuments as a JSON file
    """
    json_labeled_data = {
        annotated_doc.jeeves_document.document_id: {
            "document": JeevesDocument.serialize_to_json(annotated_doc.jeeves_document),
            "label": annotated_doc.label,
        }
        for annotated_doc in labeled_data
    }

    with open(file_name, "w") as f:
        json.dump(json_labeled_data, f, default=str)


def deserialize_labeled_data_to_json(file_name: str) -> List[AnnotatedDocument]:
    """
    Retrieve list of AnnotatedDocuments from a JSON file
    """
    labeled_data = []
    with open(file_name, "r") as f:
        json_labeled_data = json.load(f)

    for document_dict in json_labeled_data.values():
        document = document_dict["document"]
        label = document_dict["label"]
        data_source = document["data_source"]
        doc_class = IDManagerMap.get_manager_for_identifier(data_source).get_managed_document_type()
        labeled_data.append(
            AnnotatedDocument(
                jeeves_document=doc_class.deserialize_from_internal_json(document), label=label
            )
        )
    return labeled_data


def fetch_unannotated_dataset(
    dataset_size=DATASET_SIZE,
    document_language=DOCUMENT_LANGUAGE,
    seed=SEED,
    data_source=DATA_SOURCE,
) -> List[JeevesDocument]:
    """
    Query the opensearch database to fetch a random list of jeeves documents
    """
    print("Querying database")
    source_term = f'{{"term": {{"data_source": "{data_source}"}}}},' if data_source != "all" else ""
    query_string = f'{{"query": {{ "function_score": {{ "query": {{"bool": {{"filter": [{source_term} {{"term": {{"language": "{document_language}"}}}}]}}}}, "functions": [{{"random_score": {{"seed": "{seed}"}}}}]}}}}, "size": {str(dataset_size)}}}'
    query_jsn = json.loads(query_string)
    return app_registry(OpenSearchDAL).execute_arbitrary_query(query_jsn)


def annotate_dataset(data_list: List[JeevesDocument]) -> List[AnnotatedDocument]:
    """
    Add sentiment labels to the dataset
    """
    labeled_data_list = []
    label_mapping = {"p": "positive", "n": "negative", "e": "none"}
    print(
        "Time to label the dataset. Enter 'p' for positive, 'n' for negative, 'e' for no label, and 'r' to remove the document from the dataset"
    )
    random.shuffle(data_list)
    for document in data_list:
        print("Header text: ", document.header_text)
        print("Body text: ", document.body_text)
        label = input("Please enter your label: ")
        while label not in {"p", "n", "r", "e"}:
            label = input("Invalid input please enter your label: ")
        if label != "r":
            labeled_data_list.append(
                AnnotatedDocument(jeeves_document=document, label=label_mapping[label])
            )
    return labeled_data_list


if __name__ == "__main__":
    data_list = fetch_unannotated_dataset()
    labeled_data_list = annotate_dataset(data_list)

    train_cutoff = int(len(labeled_data_list) * TRAIN_SPLIT)
    test_cutoff = train_cutoff + int(len(labeled_data_list) * TEST_SPLIT)
    val_cutoff = len(labeled_data_list)

    labeled_train = labeled_data_list[:train_cutoff]
    labeled_test = labeled_data_list[train_cutoff:test_cutoff]
    labeled_val = labeled_data_list[test_cutoff:]

    dir_path = f"annotations_{datetime.datetime.utcnow()}"
    os.mkdir(dir_path)
    serialize_labeled_data_to_json(f"{dir_path}/test_data.json", labeled_test)
    serialize_labeled_data_to_json(f"{dir_path}/train_data.json", labeled_train)
    serialize_labeled_data_to_json(f"{dir_path}/val_data.json", labeled_val)

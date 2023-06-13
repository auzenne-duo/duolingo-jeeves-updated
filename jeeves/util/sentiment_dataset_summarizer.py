"""
A utility that summarizes an annotated dataset as a TSV file
"""

import csv
from typing import List

from jeeves.model.annotated_document import AnnotatedDocument


def summarize_dataset(filename: str, labeled_data: List[AnnotatedDocument]) -> None:
    """
    Allow users to more easily view the annotated dataset by saving just the document
    id, label, header, and body to a tsv file
    """
    with open(filename, "w", newline="") as tsvfile:
        writer = csv.writer(tsvfile, delimiter="\t", lineterminator="\n")
        writer.writerow(["doc_id", "label", "header", "body"])
        for labeled_doc in labeled_data:
            label = labeled_doc.label
            document = labeled_doc.jeeves_document
            writer.writerow([document.document_id, label, document.header_text, document.body_text])

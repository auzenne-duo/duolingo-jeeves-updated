"""
This script allows you to re-annotate someone else's dataset that was annotated using the generate_sentiment_dataset
script. It will create a folder with the new annotations and a dataset summary.
"""
import datetime
import os

import click

from jeeves.scripts.gpt_search.generate_sentiment_dataset import (
    annotate_dataset,
    deserialize_labeled_data_to_json,
    serialize_labeled_data_to_json,
)
from jeeves.util.sentiment_dataset_summarizer import summarize_dataset


@click.command()
@click.option("--file", help="Path to a dataset file")
def main(file: str):
    if file is None:
        raise ValueError("Must specify a file with --file")
    annotated_data = deserialize_labeled_data_to_json(file)
    unannotated_data = [labeled_doc.jeeves_document for labeled_doc in annotated_data]
    new_annotations = annotate_dataset(unannotated_data)

    dir_path = f"annotations_{datetime.datetime.utcnow()}"  # Rename this folder to something more descriptive
    os.mkdir(dir_path)
    serialize_labeled_data_to_json(f"{dir_path}/dataset.json", new_annotations)
    summarize_dataset(f"{dir_path}/dataset_summary.tsv", new_annotations)


if __name__ == "__main__":
    # pylint: disable=no-value-for-parameter
    main()

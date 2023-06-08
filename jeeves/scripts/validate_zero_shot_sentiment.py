"""
Script for validating zero-shot sentiment classification on all Jeeves data
"""

from jeeves import registry as app_registry
from jeeves.dal.ai_completions_dal import AICompletionsDAL
from jeeves.model.zero_shot_classifier import NEGATIVE_TARGET_STRING, POSITIVE_TARGET_STRING
from jeeves.scripts.generate_sentiment_dataset import deserialize_labeled_data_to_json
from jeeves.util.polarity_calculator import calc_polarity

if __name__ == "__main__":
    labeled_train = deserialize_labeled_data_to_json("annotations/train_data.json")
    pos_embedding = app_registry(AICompletionsDAL).request_embedding(POSITIVE_TARGET_STRING)
    neg_embedding = app_registry(AICompletionsDAL).request_embedding(NEGATIVE_TARGET_STRING)

    confusion_matrix = {"tp": 0, "fp": 0, "fn": 0, "tn": 0}  # Dictionary of confusion matrix values

    for annotated_doc in labeled_train:
        document = annotated_doc.jeeves_document
        label = annotated_doc.label
        doc_embedding = document.embeddings["GPT_text-embedding-ada-002"]
        """
        # Experimental document embeddings
        doc_embedding = app_registry(AICompletionsDAL).request_embedding(
            f"{document.header_text}. {document.body_text}. {document.data_source}. {document.course}. {document.attachments}. {document.date_time}"
        )
        """
        polarity = calc_polarity(doc_embedding, pos_embedding, neg_embedding)
        if label == "positive" and polarity > 0:
            confusion_matrix["tp"] += 1
        elif label == "positive" and polarity < 0:
            confusion_matrix["fn"] += 1
        elif label == "negative" and polarity > 0:
            confusion_matrix["fp"] += 1
        elif label == "negative" and polarity < 0:
            confusion_matrix["tn"] += 1

    total = sum(confusion_matrix.values())
    print(f'Accuracy: {(confusion_matrix["tn"] + confusion_matrix["tp"]) / total:.3f}')
    print(
        f'\nPositive Class\nPrecision: {(confusion_matrix["tp"] / (confusion_matrix["tp"] + confusion_matrix["fp"])):.3f}'
    )
    print(
        f'Recall: {confusion_matrix["tp"] / (confusion_matrix["tp"] + confusion_matrix["fn"]):.3f}'
    )
    print(
        f'\nNegative Class\nPrecision: {(confusion_matrix["tn"] / (confusion_matrix["tn"] + confusion_matrix["fn"])):.3f}'
    )
    print(
        f'Recall: {confusion_matrix["tn"] / (confusion_matrix["tn"] + confusion_matrix["fp"]):.3f}'
    )

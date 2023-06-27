"""
A sentiment classifier that creates an anchor embedding for sentiment analysis.

For each class, we create an anchor embedding by averaging the embeddings of training documents in that class.
We classify a document as being in the class with the closest anchor embedding.
"""
from typing import List, Tuple

import attr
import numpy as np
import numpy.typing as npt

from jeeves.config.config import GPT_EMBEDDING_MODEL
from jeeves.model.annotated_document import AnnotatedDocument, SentimentScoredDocument
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.sentiment_analysis_classifier import (
    NEGATIVE_CLASS,
    POSITIVE_CLASS,
    SentimentAnalysisClassifier,
)


@attr.s(kw_only=True)
class AnchorSentimentClassifier(SentimentAnalysisClassifier):
    positive_anchor_embedding: npt.ArrayLike = attr.ib()
    negative_anchor_embedding: npt.ArrayLike = attr.ib()

    @classmethod
    def model_from_dataset(
        cls,
        dataset: List[AnnotatedDocument],
        positive_class: str = POSITIVE_CLASS,
        negative_class: str = NEGATIVE_CLASS,
    ):
        """
        Create an instance of AnchorSentimentClassifier from a dataset.
        Construct the anchor embeddings for each class by averaging the embeddings of dataset documents in that class.
        """
        embedding_shape = np.array(dataset[0].jeeves_document.embeddings[GPT_EMBEDDING_MODEL]).shape
        embedding_dict = {
            positive_class: np.zeros(embedding_shape),
            negative_class: np.zeros(embedding_shape),
        }
        count_dict = {positive_class: 0, negative_class: 0}

        for labeled_doc in dataset:
            if (
                labeled_doc.label not in [positive_class, negative_class]
                or GPT_EMBEDDING_MODEL not in labeled_doc.jeeves_document.embeddings.keys()
            ):
                continue
            embedding_dict[labeled_doc.label] += np.array(
                labeled_doc.jeeves_document.embeddings[GPT_EMBEDDING_MODEL]
            )
            count_dict[labeled_doc.label] += 1

        positive_anchor_embedding = embedding_dict[positive_class] / count_dict[positive_class]
        negative_anchor_embedding = embedding_dict[negative_class] / count_dict[negative_class]

        return AnchorSentimentClassifier(
            positive_anchor_embedding=positive_anchor_embedding,
            negative_anchor_embedding=negative_anchor_embedding,
            positive_class=positive_class,
            negative_class=negative_class,
        )

    def classify(self, document: JeevesDocument) -> Tuple[str, float]:
        """
        Classify a single document as positive or negative based on the closest anchor embedding.

        Here the sentiment score is the inverse of the distance to the anchor embedding multiplied by the sign of the
        class because higher scores correspond to more positive sentiment and lower scores correspond to more negative
        sentiment.
        """
        positive_distance = np.linalg.norm(
            np.array(document.embeddings[GPT_EMBEDDING_MODEL]) - self.positive_anchor_embedding
        )
        negative_distance = np.linalg.norm(
            np.array(document.embeddings[GPT_EMBEDDING_MODEL]) - self.negative_anchor_embedding
        )

        if positive_distance <= negative_distance:
            return self.positive_class, 1 / positive_distance
        else:
            return self.negative_class, -1 / negative_distance

    def classify_batch(self, document_list: List[JeevesDocument]) -> List[SentimentScoredDocument]:
        """
        Classify a batch of documents as positive or negative based on the closest anchor embedding.
        """
        return [
            SentimentScoredDocument(
                jeeves_document=document, label=label, sentiment_score=inverse_distance
            )
            for document in document_list
            for label, inverse_distance in [self.classify(document)]
        ]

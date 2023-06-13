"""
Our model for a general abstract sentiment analysis classifier
"""

from abc import ABC, abstractmethod
from ctypes import Array
from dataclasses import dataclass
from typing import List, Tuple

import attr
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    f1_score,
    precision_score,
    recall_score,
)

from jeeves.model.annotated_document import AnnotatedDocument
from jeeves.model.jeeves_document import JeevesDocument

POSITIVE_CLASS = "positive"
NEGATIVE_CLASS = "negative"
NEUTRAL_CLASS = "none"


@dataclass
class SentimentLabelResults:
    """
    Class to hold metrics about a single label of a sentiment analysis classifier
    """

    precision: float
    recall: float
    f1_score: float


@dataclass
class SentimentClassifierResults:
    """
    Class to hold metrics about a sentiment analysis classifier
    """

    confusion_matrix: Array
    accuracy: float
    weighted_f1_score: float
    positive_metrics: SentimentLabelResults
    negative_metrics: SentimentLabelResults


@attr.s(kw_only=True)
class SentimentAnalysisClassifier(ABC):

    positive_class: str = attr.ib(default=POSITIVE_CLASS)
    negative_class: str = attr.ib(default=NEGATIVE_CLASS)
    neutral_class: str = attr.ib(default=NEUTRAL_CLASS)

    @abstractmethod
    def classify(self, document: JeevesDocument) -> Tuple[str, float]:
        """
        Takes in a JeevesDocument and returns the predicted sentiment label and the polarity
        """
        return NotImplementedError

    def evaluate_classifier(
        self, labeled_data: List[AnnotatedDocument]
    ) -> SentimentClassifierResults:
        """
        Utility function to evaluate a sentiment analysis model. Returns the accuracy for the model
        and the precision, recall, and f1 score for each label
        """

        gt = []
        predicted = []
        results = {}

        labels_list = [self.positive_class, self.negative_class]

        for labeled_document in labeled_data:
            label = labeled_document.label
            document = labeled_document.jeeves_document

            if label in labels_list:
                gt.append(label)
                predicted.append(self.classify(document)[0])

        for label in labels_list:
            results[label] = SentimentLabelResults(
                precision_score(gt, predicted, labels=[label], average=None)[0],
                recall_score(gt, predicted, labels=[label], average=None)[0],
                f1_score(gt, predicted, labels=[label], average=None)[0],
            )

        return SentimentClassifierResults(
            confusion_matrix(gt, predicted, labels=labels_list),
            accuracy_score(gt, predicted),
            f1_score(gt, predicted, labels=labels_list, average="weighted"),
            positive_metrics=(results[POSITIVE_CLASS]),
            negative_metrics=(results[NEGATIVE_CLASS]),
        )

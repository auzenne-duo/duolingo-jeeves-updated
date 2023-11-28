"""
Creates an ensemble sentiment classifier for AppFigures documents.
It uses the actual app store rating AND an SVM classifier trained only on AppFigures data

1-2 stars is negative, 3 stars is neutral, 4-5 stars is positive
"""
from typing import List, Tuple

import attr

from jeeves.model.annotated_document import SentimentScoredDocument
from jeeves.model.appfigures_document import AppfiguresDocument
from jeeves.model.sentiment_analysis_classifier import SentimentAnalysisClassifier
from jeeves.model.svm_sentiment_classifier import SVMSentimentClassifier

STAR_WEIGHT = 0.1
SVM_WEIGHT = 0.7


@attr.s(kw_only=True)
class AppFiguresSentimentClassifier(SentimentAnalysisClassifier):
    svm_classifier: SVMSentimentClassifier = attr.ib()
    star_weight: float = attr.ib(default=STAR_WEIGHT)
    svm_weight: float = attr.ib(default=SVM_WEIGHT)

    @classmethod
    def model_from_dataset(cls, dataset, star_weight=STAR_WEIGHT, svm_weight=SVM_WEIGHT):
        svm_classifier = SVMSentimentClassifier.model_from_dataset(dataset)
        return cls(svm_classifier=svm_classifier, star_weight=star_weight, svm_weight=svm_weight)

    @classmethod
    def map_score(cls, score):
        """
        Map the number of stars from the app store review to a score between -1 and 1
        """
        min_mapped = -1
        max_mapped = 1

        min_original = 1
        max_original = 5
        return (score - min_original) * (max_mapped - min_mapped) / (
            max_original - min_original
        ) + min_mapped

    def star_classify(self, document: AppfiguresDocument) -> Tuple[str, float]:
        """
        Classify a document as positive, negative, or neutral based on its app store rating
        """
        label = "neutral"
        if document.stars <= 2:
            label = "negative"
        elif document.stars >= 4:
            label = "positive"
        sentiment_score = self.map_score(document.stars)
        return label, sentiment_score

    def classify(self, document: AppfiguresDocument) -> Tuple[str, float]:
        """
        Classify a document as positive, negative, or neutral based on its app store rating and a svm classifier
        """
        star_score = self.star_classify(document)[1]
        svm_score = self.svm_classifier.classify(document)[1]
        score = ((star_score * self.star_weight) + (svm_score * self.svm_weight)) / 2
        max_possible_score = self.star_weight + self.svm_weight
        min_possible_score = -max_possible_score
        scaled_score = (score - min_possible_score) * 2 / (
            max_possible_score - min_possible_score
        ) - 1  # Rescale score to be between -1 and 1 again

        label = self.positive_class if scaled_score > 0 else self.negative_class
        return label, scaled_score

    def classify_batch(
        self, document_list: List[AppfiguresDocument]
    ) -> List[SentimentScoredDocument]:
        """
        Takes in a list of AppFiguresDocuments and classifies the sentiment with a label and sentiment score.
        Here the sentiment score is the number of stars rescaled to be between -1 and 1.
        """
        return [
            SentimentScoredDocument(jeeves_document=document, label=label, sentiment_score=score)
            for document in document_list
            for label, score in [self.classify(document)]
        ]

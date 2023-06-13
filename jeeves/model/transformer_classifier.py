"""
Our model for transformer-based sentiment analysis
"""

from typing import Tuple

import attr
from transformers import pipeline

from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.sentiment_analysis_classifier import SentimentAnalysisClassifier


@attr.s(kw_only=True)
class TransformerClassifier(SentimentAnalysisClassifier):

    classifier = attr.ib(default=pipeline(model="distilbert-base-uncased-finetuned-sst-2-english"))

    def classify(self, document: JeevesDocument) -> Tuple[str, float]:
        """
        Takes in a JeevesDocument and returns the predicted sentiment label and the confidence
        """

        label_mapper = {
            "POSITIVE": self.positive_class,
            "NEGATIVE": self.negative_class,
            "NEUTRAL": self.neutral_class,
        }
        result = self.classifier(f"{document.header_text}. {document.body_text}")[0]
        return (label_mapper[result["label"]], result["score"])

"""
Our model for transformer-based sentiment analysis
"""

from typing import List, Tuple

import attr
from transformers import pipeline

from jeeves.model.annotated_document import SentimentScoredDocument
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.sentiment_analysis_classifier import SentimentAnalysisClassifier


@attr.s(kw_only=True)
class TransformerClassifier(SentimentAnalysisClassifier):
    classifier = attr.ib(default=pipeline(model="distilbert-base-uncased-finetuned-sst-2-english"))
    label_mapper = attr.ib(init=False)

    @label_mapper.default
    def get_label_mapper(self):
        return {
            "POSITIVE": self.positive_class,
            "NEGATIVE": self.negative_class,
            "NEUTRAL": self.neutral_class,
        }

    def classify(self, document: JeevesDocument) -> Tuple[str, float]:
        """
        Takes in a JeevesDocument and returns the predicted sentiment label and the confidence.
        """
        result = self.classifier(f"{document.header_text}. {document.body_text}")[0]
        return self.label_mapper[result["label"]], result["score"]

    def classify_batch(self, document_list: List[JeevesDocument]) -> List[SentimentScoredDocument]:
        """
        Takes in a list of JeevesDocuments and classifies the sentiment with a label and sentiment score.
        Here the sentiment score is the confidence.
        """
        results = self.classifier(
            [f"{document.header_text}. {document.body_text}" for document in document_list]
        )
        return [
            SentimentScoredDocument(
                jeeves_document=document_list[i],
                label=self.label_mapper[results[i]["label"]],
                sentiment_score=results[i]["score"],
            )
            for i in range(len(document_list))
        ]

"""
Our model for zero-shot sentiment analysis
"""

from typing import List, Tuple

import attr

from jeeves import registry as app_registry
from jeeves.config.config import GPT_EMBEDDING_MODEL
from jeeves.dal.ai_completions_dal import AICompletionsDAL
from jeeves.model.annotated_document import SentimentScoredDocument
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.sentiment_analysis_classifier import SentimentAnalysisClassifier
from jeeves.util.polarity_calculator import calc_polarity

POSITIVE_TARGET_STRING = "positive"
NEGATIVE_TARGET_STRING = "negative"


@attr.s(kw_only=True)
class ZeroShotClassifier(SentimentAnalysisClassifier):

    positive_target_embedding: List[float] = attr.ib(
        default=app_registry(AICompletionsDAL).request_embedding(POSITIVE_TARGET_STRING)
    )
    negative_target_embedding: List[float] = attr.ib(
        default=app_registry(AICompletionsDAL).request_embedding(NEGATIVE_TARGET_STRING)
    )

    def classify(self, document: JeevesDocument) -> Tuple[str, float]:
        """
        Takes in a JeevesDocument and returns the predicted sentiment label and the polarity.
        """
        polarity = calc_polarity(
            document.embeddings[GPT_EMBEDDING_MODEL],
            self.positive_target_embedding,
            self.negative_target_embedding,
        )
        return self.positive_class if polarity > 0 else self.negative_class, polarity

    def classify_batch(self, document_list: List[JeevesDocument]) -> List[SentimentScoredDocument]:
        """
        Takes in a list of JeevesDocuments and classifies the sentiment with a label and sentiment score.
        Here the sentiment score is the polarity.
        """
        return [
            SentimentScoredDocument(jeeves_document=document, label=label, sentiment_score=polarity)
            for document in document_list
            for label, polarity in [self.classify(document)]
        ]

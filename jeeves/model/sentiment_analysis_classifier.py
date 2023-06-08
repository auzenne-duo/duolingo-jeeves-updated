"""
Our model for a general abstract sentiment analysis classifier
"""

from abc import ABC, abstractmethod
from typing import Tuple

import attr

from jeeves.model.jeeves_document import JeevesDocument

POSITIVE_CLASS = "positive"
NEGATIVE_CLASS = "negative"
NEUTRAL_CLASS = "none"


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

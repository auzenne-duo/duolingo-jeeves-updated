"""
Our model for sentiment analysis using a SVM
"""

from typing import Dict, List, Tuple

import attr
import numpy as np
from sklearn.svm import SVC

from jeeves.config.config import GPT_EMBEDDING_MODEL
from jeeves.model.annotated_document import AnnotatedDocument
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.sentiment_analysis_classifier import (
    NEGATIVE_CLASS,
    NEUTRAL_CLASS,
    POSITIVE_CLASS,
    SentimentAnalysisClassifier,
)


@attr.s(kw_only=True)
class SVMSentimentClassifier(SentimentAnalysisClassifier):

    label_to_num: Dict = attr.ib()
    num_to_label: Dict = attr.ib()
    model: SVC = attr.ib()

    @classmethod
    def model_from_dataset(
        cls,
        labeled_train: List[AnnotatedDocument],
        positive_class: str = POSITIVE_CLASS,
        negative_class: str = NEGATIVE_CLASS,
        neutral_class: str = NEUTRAL_CLASS,
    ):
        """
        Train a model using labeled_train and use it to create an instance of SVMSentimentClassifier
        """
        label_to_num = {positive_class: 2, negative_class: 0, neutral_class: 1}
        num_to_label = {2: positive_class, 0: negative_class, 1: neutral_class}

        embeddings = np.array(
            [
                labeled_doc.jeeves_document.embeddings[GPT_EMBEDDING_MODEL]
                for labeled_doc in labeled_train
            ]
        )
        labels = np.array([label_to_num[labeled_doc.label] for labeled_doc in labeled_train])

        svm_classifier = SVC(kernel="rbf", probability=True)
        svm_classifier.fit(embeddings, labels)

        return SVMSentimentClassifier(
            label_to_num=label_to_num, num_to_label=num_to_label, model=svm_classifier
        )

    def classify(self, document: JeevesDocument) -> Tuple[str, float]:
        """
        Takes in a JeevesDocument and returns the predicted sentiment label and the polarity
        """
        embedding_vector = np.array(document.embeddings[GPT_EMBEDDING_MODEL]).reshape(1, -1)
        class_probs = self.model.predict_proba(embedding_vector)
        label = class_probs.argmax()
        prob = class_probs.max()
        return self.num_to_label[label], prob

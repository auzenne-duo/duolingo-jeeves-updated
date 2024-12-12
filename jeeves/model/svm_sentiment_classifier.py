"""
Our model for sentiment analysis using a SVM
"""

import pickle
from typing import Dict, List, Tuple

import attr
import numpy as np
from sklearn.svm import SVC

from jeeves.config.config import GPT_EMBEDDING_MODEL
from jeeves.model.annotated_document import AnnotatedDocument, SentimentScoredDocument
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
    def model_from_model(
        cls,
        svm_classifier: SVC,
        positive_class: str = POSITIVE_CLASS,
        negative_class: str = NEGATIVE_CLASS,
        neutral_class: str = NEUTRAL_CLASS,
    ):
        """
        Create an instance of SVMSentimentClassifier from a trained model
        """
        label_to_num = {positive_class: 2, negative_class: 0, neutral_class: 1}
        num_to_label = {2: positive_class, 0: negative_class, 1: neutral_class}
        return SVMSentimentClassifier(
            label_to_num=label_to_num, num_to_label=num_to_label, model=svm_classifier
        )

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

    def serialize_model(self, path: str) -> None:
        """
        Serialize the model as a pickle file at path. This allows us to avoid retraining the model.
        """
        with open(path, "wb") as f:
            pickle.dump(self.model, f)

    @classmethod
    def deserialize_model(cls, path: str) -> SVC:
        """
        Deserialize the model from a pickle file at path. This allows us to avoid retraining the model.
        """
        with open(path, "rb") as f:
            model = pickle.load(f)
        return model

    def classify(self, document: JeevesDocument) -> Tuple[str, float]:
        """
        Takes in a JeevesDocument and returns the predicted sentiment label and the sentiment score.
        """
        embedding_vector = np.array(document.embeddings[GPT_EMBEDDING_MODEL]).reshape(1, -1)
        class_probs = self.model.predict_proba(embedding_vector)
        label = class_probs.argmax()
        return self.num_to_label[label], class_probs[0][2] - class_probs[0][0]

    def classify_batch(self, document_list: List[JeevesDocument]) -> List[SentimentScoredDocument]:
        """
        Takes in a batch of JeevesDocuments and returns the predicted sentiment label and the sentiment score.
        Here the sentiment score is equal to the difference between the probability of the document being positive
        and the probability of the document being negative.
        """
        embedding_vectors = np.array(
            [document.embeddings[GPT_EMBEDDING_MODEL] for document in document_list]
        )
        class_probs = self.model.predict_proba(embedding_vectors)
        return [
            SentimentScoredDocument(
                jeeves_document=document_list[i],
                label=self.num_to_label[class_probs[i].argmax()],
                sentiment_score=class_probs[i][2] - class_probs[i][0],
            )
            for i in range(len(document_list))
        ]

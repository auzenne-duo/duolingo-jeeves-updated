"""
DAL for retrieving a trained sentiment classifier from s3
"""

import pickle
from enum import Enum, auto

from duolingo_base.dal.s3 import S3Client

from jeeves.model.ensemble_sentiment_classifier import EnsembleSentimentClassifier
from jeeves.model.svm_sentiment_classifier import SVMSentimentClassifier
from jeeves.util.s3_client_and_bucket import get_s3_client_and_bucket

_SVM_MODEL_PATH = "sentiment_classifier_model/svm_model.pkl"
_ENSEMBLE_MODEL_PATH = "sentiment_classifier_model/ensemble_model.pkl"


class SentimentClassifierType(Enum):
    ZEROSHOT = auto()
    TRANSFORMER = auto()
    SVM = auto()
    GPT_BASED = auto()
    ANCHOR = auto()
    ENSEMBLE = auto()


class SentimentClassifierDAL:
    def __init__(self):
        self.sentiment_classifier: SVMSentimentClassifier = None
        self.model_type: SentimentClassifierType = None

        s3_client, s3_bucket_name = get_s3_client_and_bucket()
        self.s3_client: S3Client = s3_client
        self.s3_bucket_name: str = s3_bucket_name

    def get_svm_sentiment_classifier(self) -> SVMSentimentClassifier:
        if self.model_type != SentimentClassifierType.SVM or self.sentiment_classifier is None:
            model_pickle = self.s3_client.download(self.s3_bucket_name, _SVM_MODEL_PATH)
            self.model_type = SentimentClassifierType.SVM
            self.sentiment_classifier = SVMSentimentClassifier.model_from_model(
                pickle.loads(model_pickle)
            )
        return self.sentiment_classifier

    def get_ensemble_classifier(self) -> EnsembleSentimentClassifier:
        if self.model_type != SentimentClassifierType.ENSEMBLE or self.sentiment_classifier is None:
            model_pickle = self.s3_client.download(self.s3_bucket_name, _ENSEMBLE_MODEL_PATH)
            self.model_type = SentimentClassifierType.ENSEMBLE
            self.sentiment_classifier = pickle.loads(model_pickle)
        return self.sentiment_classifier

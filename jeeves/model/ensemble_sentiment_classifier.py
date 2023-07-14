"""
Creates an ensemble classifier that uses a different sentiment classifier depending on the data source of the document
"""
import pickle
from enum import Enum
from typing import Dict, List, Tuple

import attr

from jeeves.model.anchor_sentiment_classifier import AnchorSentimentClassifier
from jeeves.model.annotated_document import AnnotatedDocument, SentimentScoredDocument
from jeeves.model.appfigures_document import AppfiguresDocument
from jeeves.model.appfigures_sentiment_classifier import AppFiguresSentimentClassifier
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.jira_document import JiraDocument
from jeeves.model.reddit_document import RedditDocument
from jeeves.model.sentiment_analysis_classifier import SentimentAnalysisClassifier
from jeeves.model.svm_sentiment_classifier import SVMSentimentClassifier
from jeeves.model.zendesk_document import ZendeskDocument


class DataSource(Enum):
    """
    Enum for the different data sources
    """

    JIRA = JiraDocument.get_data_source_identifier()
    REDDIT = RedditDocument.get_data_source_identifier()
    ZENDESK = ZendeskDocument.get_data_source_identifier()
    APPFIGURES = AppfiguresDocument.get_data_source_identifier()
    GENERAL = "GENERAL"  # Catch-all for documents that are from a different data source


@attr.s(kw_only=True)
class EnsembleSentimentClassifier(SentimentAnalysisClassifier):
    """
    An ensemble classifier that uses a different sentiment classifier depending on the datasource of the document

    Data sources and their corresponding sentiment classifiers:
    - Reddit: AnchorSentimentClassifier
    - Zendesk: SVMSentimentClassifier
    - AppFigures: SVMSentimentClassifier
    - General: SVMSentimentClassifier
    """

    sentiment_classifier_dict: Dict = attr.ib()

    @classmethod
    def get_model_from_datasets(
        cls,
        appfigures_dataset: List[AnnotatedDocument],
        reddit_dataset: List[AnnotatedDocument],
        zendesk_dataset: List[AnnotatedDocument],
        general_dataset: List[AnnotatedDocument],
    ):
        """
        Create an instance of EnsembleSentimentClassifier from a dataset.
        """
        return EnsembleSentimentClassifier(
            sentiment_classifier_dict={
                DataSource.REDDIT.value: AnchorSentimentClassifier.model_from_dataset(
                    reddit_dataset
                ),
                DataSource.ZENDESK.value: SVMSentimentClassifier.model_from_dataset(
                    zendesk_dataset
                ),
                DataSource.APPFIGURES.value: AppFiguresSentimentClassifier.model_from_dataset(
                    appfigures_dataset
                ),
                DataSource.GENERAL.value: SVMSentimentClassifier.model_from_dataset(
                    general_dataset
                ),
            }
        )

    def serialize_model(self, path: str) -> None:
        """
        Serialize the model as a pickle file at path. This allows us to avoid retraining the model.
        """
        with open(path, "wb") as f:
            pickle.dump(self, f)

    @classmethod
    def deserialize_model(cls, path: str) -> "EnsembleSentimentClassifier":
        """
        Deserialize the model from a pickle file at path. This allows us to avoid retraining the model.
        """
        with open(path, "rb") as f:
            classifier = pickle.load(f)
        return classifier

    def classify(self, document: JeevesDocument) -> Tuple[str, float]:
        """
        Classify a document using the appropriate sentiment classifier for its data source.
        """
        if document.data_source not in self.sentiment_classifier_dict.keys():
            return self.sentiment_classifier_dict[DataSource.GENERAL.value].classify(document)
        return self.sentiment_classifier_dict[document.data_source].classify(document)

    def classify_batch(self, document_list: List[JeevesDocument]) -> List[SentimentScoredDocument]:
        """
        Classify a list of documents using the appropriate sentiment classifier for the document's data source
        """
        document_datasource_dict = {origin.value: [] for origin in DataSource}
        for document in document_list:
            document_datasource_dict[
                DataSource.GENERAL.value
                if document.data_source not in self.sentiment_classifier_dict.keys()
                else document.data_source
            ].append(document)
        sentiment_scored_documents = []
        for origin, document_list in document_datasource_dict.items():
            if len(document_list) == 0:
                continue
            sentiment_scored_documents.extend(
                self.sentiment_classifier_dict[origin].classify_batch(document_list)
            )
        return sentiment_scored_documents

    def classify_batch_using_origin(self, document_list: List[JeevesDocument], origin: DataSource):
        """
        Classify a list of documents that all come from the same origin
        """
        return self.sentiment_classifier_dict[origin].classify_batch(document_list)

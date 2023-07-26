"""
A manager for the Jeeves sentiment analysis functionality.
"""


import datetime
import logging
from dataclasses import asdict, dataclass
from enum import Enum
from typing import Dict, List

from duolingo_base.util import registry

from jeeves.dal.ai_completions_dal import AICompletionsDAL
from jeeves.dal.opensearch_interface import OpenSearchDAL
from jeeves.dal.sentiment_classifier_dal import SentimentClassifierDAL
from jeeves.manager.query_helper import DSLQueryResponse, QueryHelper
from jeeves.manager.topic_similarity_manager import TopicSimilarityManager
from jeeves.model.annotated_document import SentimentScoredDocument
from jeeves.model.search_result import DocumentContent, SearchResult, SearchResults
from jeeves.model.sentiment_analysis_classifier import NEGATIVE_CLASS, POSITIVE_CLASS

LOG = logging.getLogger(__name__)

MAX_SEARCH_RESULTS = 10000
MIN_DOC_PER_DAY = 1


class BucketWindow(Enum):
    """
    The window of time to use for each bucket in the sentiment time series
    """

    DAY = "day"
    WEEK = "week"  # Assumes the first day of the week is Monday
    MONTH = "month"


@dataclass
class SentimentSearchResult(SearchResult):
    """
    A JeevesDocument that matches the user's filters, is related to the target topic, and has been scored by the sentiment classifier
    """

    @classmethod
    def from_sentiment_scored_document(
        cls, scored_doc: SentimentScoredDocument
    ) -> "SentimentSearchResult":
        document = scored_doc.jeeves_document
        sentiment_score = scored_doc.sentiment_score
        origin = SearchResult.get_origin(document)

        text = DocumentContent(
            body=document.body_text,
            title=document.header_text,
        )

        return cls(
            document.date_time.isoformat(),
            origin,
            text,
            sentiment_score,
            document.jeeves_uid,
            None,
        )


@dataclass
class SentimentBucket:
    """
    Object representing a bucket of sentiment data
    """

    average_sentiment_score: float
    num_documents: int

    def to_dict(self):
        return asdict(self)


@dataclass
class SentimentSearchResults(SearchResults):
    """
    The object we will return to the user from /api/3/sentiment_time_series
    """

    positive_bucket: Dict[str, SentimentBucket]
    negative_bucket: Dict[str, SentimentBucket]


@registry.bind(
    ai_completions_dal=registry.reference(AICompletionsDAL),
    sentiment_classifier_dal=registry.reference(SentimentClassifierDAL),
    opensearch_dal=registry.reference(OpenSearchDAL),
    query_helper=registry.reference(QueryHelper),
    topic_similarity_manager=registry.reference(TopicSimilarityManager),
)
class SentimentSearchManager:
    def __init__(
        self,
        ai_completions_dal: AICompletionsDAL,
        sentiment_classifier_dal: SentimentClassifierDAL,
        opensearch_dal: OpenSearchDAL,
        query_helper: QueryHelper,
        topic_similarity_manager: TopicSimilarityManager,
    ) -> None:
        LOG.debug("Initializing SentimentSearchManager...")
        self.ai_completions_dal = ai_completions_dal
        self.sentiment_classifier_dal = sentiment_classifier_dal
        self.opensearch_dal = opensearch_dal
        self.query_helper = query_helper
        self.topic_similarity_manager = topic_similarity_manager

    def sentiment_search(
        self,
        query: str,
        num_results: int = MAX_SEARCH_RESULTS,
        max_search_depth: int = MAX_SEARCH_RESULTS,
    ) -> SentimentSearchResults:
        """
        This function performs sentiment search using the given natural language query.
        """
        LOG.debug("Starting sentiment search...")
        dsl_response: DSLQueryResponse = self.query_helper.get_dsl_query_and_topics(query)
        LOG.debug("Got DSL query and topics...")

        topic_embedding = self.ai_completions_dal.request_embedding(dsl_response.target_topic)
        LOG.debug("Got topic embedding...")

        hits = self.opensearch_dal.perform_knn_search(
            dsl_response.dsl_query,
            topic_embedding,
            num_results,
            max_search_depth,
            threshold=0.5,
        )
        LOG.debug("Performed knn search...")

        related_docs = self.topic_similarity_manager.filter_documents_using_topic(
            hits.values(), dsl_response.target_topic
        )
        LOG.debug("Found related documents...")

        scored_docs = self.sentiment_classifier_dal.get_svm_sentiment_classifier().classify_batch(
            related_docs
        )
        LOG.debug("Classified sentiment of docs...")

        results = [SentimentSearchResult.from_sentiment_scored_document(doc) for doc in scored_docs]

        buckets = self.aggregate_sentiment_data(scored_docs, bucket_window=BucketWindow.DAY)
        LOG.debug("Bucketed sentiment data... Search complete!")

        return SentimentSearchResults(
            lucene_query=dsl_response.lucene_query,
            query=query,
            positive_bucket=buckets[POSITIVE_CLASS],
            negative_bucket=buckets[NEGATIVE_CLASS],
            results=results,
        )

    @classmethod
    def aggregate_sentiment_data(
        cls,
        documents_list: List[SentimentScoredDocument],
        bucket_window: BucketWindow = BucketWindow.DAY,
    ) -> Dict[str, Dict[str, SentimentBucket]]:
        """
        Calculates per-day average sentiment scores for positive and negative documents separately.

        Returns two dictionaries, one for positive documents and one for negative documents.
        Each dictionary contains a string representing a date. Each date has a float representing the average sentiment
        score and the number of documents for that date.
        """
        score_dict = {POSITIVE_CLASS: {}, NEGATIVE_CLASS: {}}
        count_dict = {POSITIVE_CLASS: {}, NEGATIVE_CLASS: {}}
        average_dict = {POSITIVE_CLASS: {}, NEGATIVE_CLASS: {}}
        for doc in documents_list:
            date = doc.jeeves_document.date_time
            if bucket_window == BucketWindow.DAY:
                date = doc.jeeves_document.date_time
            elif bucket_window == BucketWindow.WEEK:
                date = date - datetime.timedelta(days=date.weekday())
            elif bucket_window == BucketWindow.MONTH:
                date = date.replace(day=1)
            date = date.date().isoformat()
            if date not in score_dict[doc.label]:
                score_dict[doc.label][date] = 0
                count_dict[doc.label][date] = 0
            score_dict[doc.label][date] += doc.sentiment_score
            count_dict[doc.label][date] += 1

        for label in [POSITIVE_CLASS, NEGATIVE_CLASS]:
            for date in score_dict[label]:
                if count_dict[label][date] >= MIN_DOC_PER_DAY:
                    score = score_dict[label][date] / count_dict[label][date]
                    average_dict[label][date] = SentimentBucket(
                        average_sentiment_score=score, num_documents=count_dict[label][date]
                    )

        return average_dict

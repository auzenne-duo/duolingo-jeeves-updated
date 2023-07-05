"""
A manager for the Jeeves sentiment analysis functionality.
"""


from typing import List

from duolingo_base.util import registry

from jeeves.dal.ai_completions_dal import AICompletionsDAL
from jeeves.dal.opensearch_interface import OpenSearchDAL
from jeeves.dal.sentiment_classifier_dal import SentimentClassifierDAL
from jeeves.manager.query_helper import DSLQueryResponse, QueryHelper
from jeeves.manager.topic_similarity_manager import TopicSimilarityManager
from jeeves.model.annotated_document import SentimentScoredDocument

MAX_SEARCH_RESULTS = 10000


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
    ) -> List[SentimentScoredDocument]:

        dsl_response: DSLQueryResponse = self.query_helper.get_dsl_query_and_topics(query)

        topic_embedding = self.ai_completions_dal.request_embedding(dsl_response.target_topic)

        hits = self.opensearch_dal.perform_knn_search(
            dsl_response.dsl_query,
            topic_embedding,
            num_results,
            max_search_depth,
            threshold=0.5,
        )

        related_docs = self.topic_similarity_manager.filter_documents_using_topic(
            hits.values(), dsl_response.target_topic
        )

        return self.sentiment_classifier_dal.get_svm_sentiment_classifier().classify_batch(
            related_docs
        )

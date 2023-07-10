import unittest
from datetime import datetime
from unittest.mock import patch

import pytest

from jeeves.manager.sentiment_search_manager import SentimentSearchManager
from jeeves.model.annotated_document import SentimentScoredDocument
from jeeves.model.sentiment_analysis_classifier import NEGATIVE_CLASS, POSITIVE_CLASS
from tests.test_documents import _zendesk_document, get_mock_jeeves_documents

now = datetime.now()


def _sentiment_scored_document(
    jeeves_document=_zendesk_document(),
    label=POSITIVE_CLASS,
    sentiment_score=0.5,
):
    return SentimentScoredDocument(
        jeeves_document=jeeves_document,
        label=label,
        sentiment_score=sentiment_score,
    )


document_indices = [0, 2, 3, 5, 6, 7, 8]  # See these documents in tests/test_documents.py
complete_mock_document_list = get_mock_jeeves_documents()

mock_sentiment_scored_list = [
    _sentiment_scored_document(
        jeeves_document=complete_mock_document_list[0],
        label=NEGATIVE_CLASS,
        sentiment_score=-1,
    ),
    _sentiment_scored_document(
        jeeves_document=complete_mock_document_list[2],
        label=POSITIVE_CLASS,
        sentiment_score=0.6,
    ),
    _sentiment_scored_document(
        jeeves_document=complete_mock_document_list[3],
        label=NEGATIVE_CLASS,
        sentiment_score=-0.25,
    ),
    _sentiment_scored_document(
        jeeves_document=complete_mock_document_list[5],
        label=NEGATIVE_CLASS,
        sentiment_score=-0.6,
    ),
    _sentiment_scored_document(
        jeeves_document=complete_mock_document_list[6],
        label=POSITIVE_CLASS,
        sentiment_score=0.4,
    ),
    _sentiment_scored_document(
        jeeves_document=complete_mock_document_list[7],
        label=NEGATIVE_CLASS,
        sentiment_score=-0.25,
    ),
    _sentiment_scored_document(
        jeeves_document=complete_mock_document_list[8],
        label=POSITIVE_CLASS,
        sentiment_score=0.2,
    ),
]

aggregate_sentiment_data_test_cases = [
    (
        mock_sentiment_scored_list,
        {POSITIVE_CLASS: {"2022-01-18": 0.4}, NEGATIVE_CLASS: {"2023-05-01": -0.5}},
    )
]


@patch("jeeves.dal.ai_completions_dal.AICompletionsDAL")
@patch("jeeves.dal.sentiment_classifier_dal.SentimentClassifierDAL")
@patch("jeeves.dal.opensearch_interface.OpenSearchDAL")
@patch("jeeves.manager.query_helper.QueryHelper")
@patch("jeeves.manager.topic_similarity_manager.TopicSimilarityManager")
@pytest.mark.parametrize(
    "sentiment_scored_list, expected_buckets", aggregate_sentiment_data_test_cases
)
def test_aggregate_sentiment_data(
    mock_ai_completions_dal,
    mock_sentiment_classifier_dal,
    mock_opensearch_dal,
    mock_query_helper,
    mock_topic_similarity_manager,
    sentiment_scored_list,
    expected_buckets,
):
    """
    Tests that aggregate_sentiment_data correctly buckets the average sentiment scores by date
    """
    sentiment_search_manager = SentimentSearchManager(
        mock_ai_completions_dal,
        mock_sentiment_classifier_dal,
        mock_opensearch_dal,
        mock_query_helper,
        mock_topic_similarity_manager,
    )
    buckets = sentiment_search_manager.aggregate_sentiment_data(sentiment_scored_list)

    case = unittest.TestCase()
    case.assertCountEqual(expected_buckets.keys(), buckets.keys())
    for label in expected_buckets.keys():
        case.assertCountEqual(expected_buckets[label].keys(), buckets[label].keys())
        for date in expected_buckets[label].keys():
            case.assertAlmostEqual(expected_buckets[label][date], buckets[label][date], places=3)

import unittest
from typing import Dict, List
from unittest.mock import patch

import numpy as np
import pytest

from jeeves.manager.topic_similarity_manager import SimilarityCategory, TopicSimilarityManager
from jeeves.model.jeeves_document import JeevesDocument
from jeeves.model.matching_document import MatchingDocument
from tests.test_documents import _zendesk_document, get_mock_jeeves_documents


def _matching_document(
    doc=_zendesk_document(),
    score=0.5,
):
    return MatchingDocument(
        doc=doc,
        score=score,
    )


mock_document_list = get_mock_jeeves_documents()[
    0:5
]  # See these documents in tests/test_documents.py

mock_matching_document_list_leaderboards = [
    _matching_document(doc, score)
    for doc, score in zip(mock_document_list, [0.9, 0.5, 0.83, 0.85, 0.81])
]

mock_matching_document_list_swahili = [
    _matching_document(doc, score)
    for doc, score in zip(mock_document_list, [0.3, 0.9, 0.4, 0.5, 0.78])
]

LEADERBOARDS = "leaderboards"
SWAHILI = "swahili"
STREAK = "streaks"

filter_documents_using_topic_test_cases = [
    (
        mock_matching_document_list_leaderboards,
        LEADERBOARDS,
        np.array([0.5, 0.5, 0.5]),
        {SimilarityCategory.RELATED: [], SimilarityCategory.UNRELATED: []},
        [
            mock_document_list[0],
            mock_document_list[2],
            mock_document_list[3],
            mock_document_list[4],
        ],
    ),
    (
        mock_matching_document_list_swahili,
        SWAHILI,
        np.array([10001, 201, 0.00022]),
        {SimilarityCategory.UNRELATED: [], SimilarityCategory.RELATED: []},
        [mock_document_list[1]],
    ),
]

sort_documents_using_cosine_similarity_test_cases = [
    (
        mock_matching_document_list_leaderboards,
        {
            SimilarityCategory.SIMILAR: [mock_document_list[4]],
            SimilarityCategory.DISSIMILAR: [],
            SimilarityCategory.STRONGLY_SIMILAR: [
                mock_document_list[0],
                mock_document_list[3],
                mock_document_list[2],
            ],
            SimilarityCategory.STRONGLY_DISSIMILAR: [mock_document_list[1]],
        },
    ),
    (
        mock_matching_document_list_swahili,
        {
            SimilarityCategory.SIMILAR: [],
            SimilarityCategory.DISSIMILAR: [mock_document_list[4]],
            SimilarityCategory.STRONGLY_SIMILAR: [mock_document_list[1]],
            SimilarityCategory.STRONGLY_DISSIMILAR: [
                mock_document_list[0],
                mock_document_list[2],
                mock_document_list[3],
            ],
        },
    ),
]

verify_topic_using_gpt_test_cases = [
    (
        mock_document_list,
        LEADERBOARDS,
        f'{{"related ids": ["uid2","uid4","uid0", "uid3"],"unrelated ids": ["uid1"]}}',
        {
            SimilarityCategory.RELATED: [
                mock_document_list[2],
                mock_document_list[4],
                mock_document_list[0],
                mock_document_list[3],
            ],
            SimilarityCategory.UNRELATED: [mock_document_list[1]],
        },
    ),
    (
        mock_document_list,
        SWAHILI,
        f'{{"unrelated ids": ["uid2","uid4","uid0","uid3"],"related ids": ["uid1"]}}',
        {
            SimilarityCategory.UNRELATED: [
                mock_document_list[2],
                mock_document_list[4],
                mock_document_list[0],
                mock_document_list[3],
            ],
            SimilarityCategory.RELATED: [mock_document_list[1]],
        },
    ),
    (
        mock_document_list,
        STREAK,
        f'{{"unrelated ids": ["uid2","uid4","uid0","uid3","uid1"],"related ids": []}}',
        {
            SimilarityCategory.UNRELATED: [
                mock_document_list[2],
                mock_document_list[4],
                mock_document_list[0],
                mock_document_list[3],
                mock_document_list[1],
            ],
            SimilarityCategory.RELATED: [],
        },
    ),
]


@patch("jeeves.dal.ai_completions_dal.AICompletionsDAL")
@pytest.mark.parametrize(
    "document_list,target_topic,target_embedding,verify_topic_using_gpt_response,expected_filtered_list",
    filter_documents_using_topic_test_cases,
)
def test_filter_documents_using_topic(
    mock_ai_completions_dal,
    document_list,
    target_topic,
    target_embedding,
    verify_topic_using_gpt_response,
    expected_filtered_list,
):
    """
    Tests that documents irrelevant to the target topic will be filtered out
    """

    topic_similarity_manager = TopicSimilarityManager(
        ai_completions_dal=mock_ai_completions_dal,
    )
    mock_ai_completions_dal.request_embedding.side_effect = lambda x: {
        target_topic: target_embedding,
        SimilarityCategory.UNRELATED.value: [-10, -10, -10],
    }[x]

    def mock_verify_topic_using_gpt(
        document_list: List[JeevesDocument], target_topic: str
    ) -> Dict[str, List[JeevesDocument]]:
        return verify_topic_using_gpt_response

    with patch.object(
        topic_similarity_manager, "verify_topic_using_gpt", side_effect=mock_verify_topic_using_gpt
    ):
        filtered_list = topic_similarity_manager.filter_documents_using_topic(
            document_list, target_topic
        )

    case = unittest.TestCase()
    case.assertCountEqual(expected_filtered_list, filtered_list)


@patch("jeeves.dal.ai_completions_dal.AICompletionsDAL")
@pytest.mark.parametrize(
    "document_list, expected_sorted_dict",
    sort_documents_using_cosine_similarity_test_cases,
)
def test_sort_documents_using_cosine_similarity(
    mock_ai_completions_dal, document_list, expected_sorted_dict
):
    """
    Tests that documents are correctly bucketed using cosine similarity
    """

    topic_similarity_manager = TopicSimilarityManager(mock_ai_completions_dal)
    sorted_dict = topic_similarity_manager.sort_documents_using_cosine_similarity(document_list)

    case = unittest.TestCase()
    for category in [
        SimilarityCategory.STRONGLY_SIMILAR,
        SimilarityCategory.SIMILAR,
        SimilarityCategory.DISSIMILAR,
        SimilarityCategory.STRONGLY_DISSIMILAR,
    ]:
        case.assertCountEqual(expected_sorted_dict[category], sorted_dict[category])


@patch("jeeves.dal.ai_completions_dal.AICompletionsDAL")
@pytest.mark.parametrize(
    "document_list, target_topic,ai_completions_response,expected_filtered_dict",
    verify_topic_using_gpt_test_cases,
)
def test_verify_topic_using_gpt(
    mock_ai_completions_dal,
    document_list,
    target_topic,
    ai_completions_response,
    expected_filtered_dict,
):
    """
    Tests that verify_topic_using_gpt correctly processes the output from ai_completions_backend
    """

    topic_similarity_manger = TopicSimilarityManager(mock_ai_completions_dal)
    mock_ai_completions_dal.ask.return_value = ai_completions_response
    filtered_dict = topic_similarity_manger.verify_topic_using_gpt(document_list, target_topic)

    case = unittest.TestCase()
    for category in [
        SimilarityCategory.RELATED,
        SimilarityCategory.UNRELATED,
    ]:
        case.assertCountEqual(expected_filtered_dict[category], filtered_dict[category])

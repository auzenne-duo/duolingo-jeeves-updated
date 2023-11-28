import unittest
from typing import Dict, List, Tuple
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
FORMATTED_DOCS_OUTPUT_LIST = [
    "id:0 header:Leaderboards are broken body:@Duolingo when I click on the leaderboard tab the app crashes!",
    "id:1 header:Please add swahili body:I really want to use Duolingo to learn swahili",
    "id:2 header:Leagues are so much fun body:I finally got first in the diamond league!",
    "id:3 header:How do I see my friends on the leaderboard? body:I want to be in a league with my friends!",
    "id:4 header:Duolingo is so competitive body:Duolingo makes me feel like I'm competing with my swahili friends",
]
ID_MAPPER = {"uid0": "0", "uid1": "1", "uid2": "2", "uid3": "3", "uid4": "4", "uid5": "5"}
mock_leaderboards_document_list = [
    mock_document_list[2],
    mock_document_list[4],
    mock_document_list[0],
    mock_document_list[3],
]
mock_swahili_document_list = [mock_document_list[1]]
verify_topic_using_gpt_test_cases = [
    (
        mock_leaderboards_document_list,
        mock_swahili_document_list,
        LEADERBOARDS,
        '{"related ids": ["2","4","0","3"],"unrelated ids": ["1"]}',
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
        mock_swahili_document_list,
        mock_leaderboards_document_list,
        SWAHILI,
        '{"unrelated ids": ["2","4","0","3"],"related ids": ["1"]}',
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
        [],
        mock_document_list,
        STREAK,
        '{"unrelated ids": ["2","4","0","3","1"],"related ids": []}',
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
        likely_related_docs: List[JeevesDocument],
        likely_unrelated_docs: List[JeevesDocument],
        target_topic: str,
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
    "likely_related_docs,likely_unrelated_docs,target_topic,ai_completions_response,expected_filtered_dict",
    verify_topic_using_gpt_test_cases,
)
def test_verify_topic_using_gpt(
    mock_ai_completions_dal,
    likely_related_docs,
    likely_unrelated_docs,
    target_topic,
    ai_completions_response,
    expected_filtered_dict,
):
    """
    Tests that verify_topic_using_gpt correctly processes the output from ai_completions_backend
    """
    topic_similarity_manger = TopicSimilarityManager(mock_ai_completions_dal)
    mock_ai_completions_dal.ask.return_value = ai_completions_response

    def mocked_get_max_docs_under_content_length_limit(
        self, docs: List[JeevesDocument]
    ) -> Tuple[List[str], Dict[int, str]]:
        return FORMATTED_DOCS_OUTPUT_LIST, ID_MAPPER

    with patch.object(
        TopicSimilarityManager,
        "get_max_docs_under_content_length_limit",
        new=mocked_get_max_docs_under_content_length_limit,
    ):
        filtered_dict = topic_similarity_manger.verify_topic_using_gpt(
            likely_related_docs, likely_unrelated_docs, target_topic
        )

    case = unittest.TestCase()
    for category in [
        SimilarityCategory.RELATED,
        SimilarityCategory.UNRELATED,
    ]:
        case.assertCountEqual(expected_filtered_dict[category], filtered_dict[category])

import unittest
from datetime import datetime
from unittest.mock import patch

import numpy as np
import pytest

from jeeves.config.config import GPT_EMBEDDING_MODEL
from jeeves.manager.topic_similarity_manager import SimilarityCategory, TopicSimilarityManager
from jeeves.model.matching_document import MatchingDocument
from jeeves.model.shake_to_report_category import ShakeToReportCategory
from jeeves.model.zendesk_document import ZendeskDocument

now = datetime.now()


def _zendesk_document(
    document_id="default_doc",
    jeeves_uid="default_uid",
    header="I am a header",
    body="I am body text",
    embeddings=np.array([0, 0, 0]),
):
    doc = ZendeskDocument(
        data_source="Zendesk",
        document_id=document_id,
        jeeves_uid=jeeves_uid,
        date_time=now,
        header_text=header,
        body_text=body,
        language="en",
        links=[],
        shake_to_report_category=ShakeToReportCategory.EXTERNAL,
        attachments=[],
        duolingo_metadata={},
        app_version="",
        course="",
        fullstory_url="",
        os_version="",
        platform="",
        screen_size="",
        screen_content="",
        ui_language="",
        username="",
        embeddings=embeddings,
        email="",
        product="LA",
        priority="urgent",
        via={
            "channel": "api",
            "source": {
                "from": {},
                "rel": None,
                "to": {},
            },
        },
        tags=[],
        requester_id="requester1",
        metadata="",
        experiment_conditions={},
    )
    return doc


mock_jeeves_document_1 = _zendesk_document(
    document_id="1",
    jeeves_uid="uid1",
    header="Leaderboards are broken",
    body="@Duolingo when I click on the leaderboard tab the app crashes!",
    embeddings={GPT_EMBEDDING_MODEL: np.array([0.5, 0.5, 0.6])},
)
mock_jeeves_document_2 = _zendesk_document(
    document_id="2",
    jeeves_uid="uid2",
    header="Please add swahili",
    body="I really want to use Duolingo to learn swahili",
    embeddings={GPT_EMBEDDING_MODEL: np.array([10000, 200, 0.00002])},
)
mock_jeeves_document_3 = _zendesk_document(
    document_id="3",
    jeeves_uid="uid3",
    header="Leagues are so much fun",
    body="I finally got first in the diamond league!",
    embeddings={GPT_EMBEDDING_MODEL: np.array([0.5, 0.5, 0.7])},
)
mock_jeeves_document_4 = _zendesk_document(
    document_id="4",
    jeeves_uid="uid4",
    header="How do I see my friends on the leaderboard?",
    body="I want to be in a league with my friends!",
    embeddings={GPT_EMBEDDING_MODEL: np.array([0.5, 0.5, 0.55])},
)
mock_jeeves_document_5 = _zendesk_document(
    document_id="5",
    jeeves_uid="uid5",
    header="Duolingo is so competitive",
    body="Duolingo makes me feel like I'm competing with my swahili friends",
    embeddings={GPT_EMBEDDING_MODEL: np.array([0.5, 0.51, 0.55])},
)


def _matching_document(
    doc=_zendesk_document(),
    score=0.5,
):
    return MatchingDocument(
        doc=doc,
        score=score,
    )


mock_document_list = [
    mock_jeeves_document_1,
    mock_jeeves_document_2,
    mock_jeeves_document_3,
    mock_jeeves_document_4,
    mock_jeeves_document_5,
]

mock_matching_document_list_leaderboards = [
    _matching_document(mock_jeeves_document_1, 0.9),
    _matching_document(mock_jeeves_document_2, 0.5),
    _matching_document(mock_jeeves_document_3, 0.8),
    _matching_document(mock_jeeves_document_4, 0.85),
    _matching_document(mock_jeeves_document_5, 0.81),
]

mock_matching_document_list_swahili = [
    _matching_document(mock_jeeves_document_1, 0.3),
    _matching_document(mock_jeeves_document_2, 0.9),
    _matching_document(mock_jeeves_document_3, 0.4),
    _matching_document(mock_jeeves_document_4, 0.5),
    _matching_document(mock_jeeves_document_5, 0.78),
]

LEADERBOARDS = "leaderboards"
LEADERBOARDS_TOPIC_DEF = "leaderboards are a feature where users can compete in leagues"
SWAHILI = "swahili"
SWAHILI_TOPIC_DEF = "swahili is a language course on Duolingo"

filter_documents_using_topic_test_cases = [
    (
        mock_matching_document_list_leaderboards,
        LEADERBOARDS,
        LEADERBOARDS_TOPIC_DEF,
        np.array([0.5, 0.5, 0.5]),
        [
            mock_jeeves_document_1,
            mock_jeeves_document_3,
            mock_jeeves_document_4,
            mock_jeeves_document_5,
        ],
    ),
    (
        mock_matching_document_list_swahili,
        SWAHILI,
        SWAHILI_TOPIC_DEF,
        np.array([10001, 201, 0.00022]),
        [mock_jeeves_document_2],
    ),
]

sort_documents_using_cosine_similarity_test_cases = [
    (
        mock_matching_document_list_leaderboards,
        {
            SimilarityCategory.SIMILAR: [mock_jeeves_document_5],
            SimilarityCategory.DISSIMILAR: [],
            SimilarityCategory.STRONGLY_SIMILAR: [mock_jeeves_document_1, mock_jeeves_document_4],
            SimilarityCategory.STRONGLY_DISSIMILAR: [mock_jeeves_document_2],
        },
    ),
    (
        mock_matching_document_list_swahili,
        {
            SimilarityCategory.SIMILAR: [],
            SimilarityCategory.DISSIMILAR: [mock_jeeves_document_5],
            SimilarityCategory.STRONGLY_SIMILAR: [mock_jeeves_document_2],
            SimilarityCategory.STRONGLY_DISSIMILAR: [
                mock_jeeves_document_1,
                mock_jeeves_document_3,
                mock_jeeves_document_4,
            ],
        },
    ),
]

verify_topic_using_gpt_test_cases = [
    (
        mock_document_list,
        LEADERBOARDS_TOPIC_DEF,
        True,
        "id: uid1, uid3, uid4, uid5",
        [
            mock_jeeves_document_3,
            mock_jeeves_document_5,
            mock_jeeves_document_1,
            mock_jeeves_document_4,
        ],
    ),
    (mock_document_list, LEADERBOARDS_TOPIC_DEF, False, "id: uid2", [mock_jeeves_document_2]),
    (
        mock_document_list,
        SWAHILI_TOPIC_DEF,
        False,
        "id: uid1, uid3, uid4, uid5",
        [
            mock_jeeves_document_5,
            mock_jeeves_document_1,
            mock_jeeves_document_3,
            mock_jeeves_document_4,
        ],
    ),
    (mock_document_list, SWAHILI_TOPIC_DEF, True, "id: uid2", [mock_jeeves_document_2]),
]


@patch("jeeves.dal.ai_completions_dal.AICompletionsDAL")
@patch("jeeves.manager.topic_definition_manager.TopicDefinitionManager")
@pytest.mark.parametrize(
    "document_list,target_topic,target_topic_def,target_embedding,expected_filtered_list",
    filter_documents_using_topic_test_cases,
)
def test_filter_documents_using_topic(
    mock_ai_completions_dal,
    mock_topic_definition_manager,
    document_list,
    target_topic,
    target_topic_def,
    target_embedding,
    expected_filtered_list,
):
    """
    Tests that documents irrelevant to the target topic will be filtered out
    """

    topic_similarity_manager = TopicSimilarityManager(
        mock_ai_completions_dal, mock_topic_definition_manager
    )
    mock_ai_completions_dal.request_embedding.return_value = target_embedding
    mock_topic_definition_manager.get_topic_description.return_value = target_topic_def
    filtered_list = topic_similarity_manager.filter_documents_using_topic(
        document_list, target_topic
    )

    case = unittest.TestCase()
    case.assertCountEqual(expected_filtered_list, filtered_list)


@patch("jeeves.dal.ai_completions_dal.AICompletionsDAL")
@patch("jeeves.manager.topic_definition_manager.TopicDefinitionManager")
@pytest.mark.parametrize(
    "document_list, expected_sorted_dict",
    sort_documents_using_cosine_similarity_test_cases,
)
def test_sort_documents_using_cosine_similarity(
    mock_ai_completions_dal, mock_topic_definition_manager, document_list, expected_sorted_dict
):
    """
    Tests that documents are correctly bucketed using cosine similarity
    """

    topic_similarity_manager = TopicSimilarityManager(
        mock_ai_completions_dal, mock_topic_definition_manager
    )
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
@patch("jeeves.manager.topic_definition_manager.TopicDefinitionManager")
@pytest.mark.parametrize(
    "document_list,target_topic_def,get_similar,ai_completions_response,expected_filtered_list",
    verify_topic_using_gpt_test_cases,
)
def test_verify_topic_using_gpt(
    mock_ai_completions_dal,
    mock_topic_definition_manager,
    document_list,
    target_topic_def,
    get_similar,
    ai_completions_response,
    expected_filtered_list,
):
    """
    Tests that verify_topic_using_gpt correctly processes the output from ai_completions_backend
    """

    topic_similarity_manger = TopicSimilarityManager(
        mock_ai_completions_dal, mock_topic_definition_manager
    )
    mock_ai_completions_dal.ask.return_value = ai_completions_response
    filtered_list = topic_similarity_manger.verify_topic_using_gpt(
        document_list, target_topic_def, get_similar
    )

    case = unittest.TestCase()
    case.assertCountEqual(expected_filtered_list, filtered_list)

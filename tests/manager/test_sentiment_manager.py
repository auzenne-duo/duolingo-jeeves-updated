from datetime import datetime
from unittest.mock import patch

import numpy as np
import pytest

from jeeves.config.config import GPT_EMBEDDING_MODEL
from jeeves.manager.sentiment_manager import SentimentManager
from jeeves.model.shake_to_report_category import ShakeToReportCategory
from jeeves.model.zendesk_document import ZendeskDocument

now = datetime.now()


def _zendesk_document(
    document_id="default_doc",
    header="I am a header",
    body="I am body text",
    embeddings=np.array([0, 0, 0]),
):
    doc = ZendeskDocument(
        data_source="Zendesk",
        document_id=document_id,
        jeeves_uid="uid1",
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
    header="Leaderboards are broken",
    body="@Duolingo when I click on the leaderboard tab the app crashes!",
    embeddings={GPT_EMBEDDING_MODEL: np.array([0.5, 0.5, 0.6])},
)
mock_jeeves_document_2 = _zendesk_document(
    document_id="2",
    header="Please add swahili",
    body="I really want to use Duolingo to learn swahili",
    embeddings={GPT_EMBEDDING_MODEL: np.array([10000, 200, 0.00002])},
)
mock_jeeves_document_3 = _zendesk_document(
    document_id="3",
    header="Leagues are so much fun",
    body="I finally got first in the diamond league!",
    embeddings={GPT_EMBEDDING_MODEL: np.array([0.5, 0.5, 0.7])},
)
mock_jeeves_document_4 = _zendesk_document(
    document_id="4",
    header="How do I see my friends on the leaderboard?",
    body="I want to be in a league with my friends!",
    embeddings={GPT_EMBEDDING_MODEL: np.array([0.5, 0.5, 0.55])},
)
mock_document_list = [
    mock_jeeves_document_1,
    mock_jeeves_document_2,
    mock_jeeves_document_3,
    mock_jeeves_document_4,
]

filter_documents_using_topic_test_cases = [
    (
        mock_document_list,
        "leaderboards",
        np.array([0.5, 0.5, 0.5]),
        [mock_jeeves_document_1, mock_jeeves_document_3, mock_jeeves_document_4],
    ),
    (mock_document_list, "swahili", np.array([10001, 201, 0.00022]), [mock_jeeves_document_2]),
]


@patch("jeeves.dal.ai_completions_dal.AICompletionsDAL")
@patch("jeeves.dal.opensearch_interface.OpenSearchDAL")
@patch("jeeves.dal.sentiment_classifier_dal.SentimentClassifierDAL")
def test_get_query_parameters(
    mock_ai_completions_dal, mock_opensearch_dal, mock_sentiment_classifier_dal
):
    """
    Tests that the get_query_parameters function correctly processes the output from ai_completions_backend
    """
    mock_ai_completions_dal.ask.return_value = (
        "Filters: data_source: Twitter, platform: Android, date_time: ["
        "now-1M TO now]\nTarget topic: Leaderboards"
    )
    user_prompt = "What do people on Twitter think about leaderboards on Android in the last month?"
    sentiment_manager = SentimentManager(
        mock_ai_completions_dal, mock_opensearch_dal, mock_sentiment_classifier_dal
    )
    response = sentiment_manager.get_query_parameters(user_prompt).convert_to_dict()
    assert response["filters"] == {
        "data_source": "Twitter",
        "platform": "Android",
        "date_time": "[now-1M TO now]",
    }
    assert response["topic"] == "Leaderboards"

    # Test an error
    mock_ai_completions_dal.ask.return_value = None

    response = sentiment_manager.get_query_parameters(user_prompt)

    assert response["filters"] == {}
    assert response["topic"] == "anything"


@patch("jeeves.dal.ai_completions_dal.AICompletionsDAL")
@patch("jeeves.dal.opensearch_interface.OpenSearchDAL")
@patch("jeeves.dal.sentiment_classifier_dal.SentimentClassifierDAL")
@pytest.mark.parametrize(
    "document_list,target_topic,target_embedding,expected_filtered_list",
    filter_documents_using_topic_test_cases,
)
def test_filter_documents_using_topic(
    mock_ai_completions_dal,
    mock_opensearch_dal,
    mock_sentiment_classifier_dal,
    document_list,
    target_topic,
    target_embedding,
    expected_filtered_list,
):
    """
    Tests that documents irrelevant to the target topic will be filtered out
    """
    sentiment_manager = SentimentManager(
        mock_ai_completions_dal, mock_opensearch_dal, mock_sentiment_classifier_dal
    )
    mock_ai_completions_dal.request_embedding.return_value = target_embedding
    actual_filtered_list = sentiment_manager.filter_documents_using_topic(
        document_list, target_topic
    )
    assert len(expected_filtered_list) == len(actual_filtered_list)
    assert all(
        [
            doc_a.document_id == doc_b.document_id
            for doc_a, doc_b in zip(actual_filtered_list, expected_filtered_list)
        ]
    )

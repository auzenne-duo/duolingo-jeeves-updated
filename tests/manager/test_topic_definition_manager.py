from unittest.mock import patch

from jeeves.manager.topic_definition_manager import TopicDefinitionManager


@patch("jeeves.dal.ai_completions_dal.AICompletionsDAL")
def test_get_topic_description(mock_ai_completions_dal):
    """
    Tests that the get_topic_description function correctly processes the output from ai_completions_backend
    """
    topic_definition_manager = TopicDefinitionManager(mock_ai_completions_dal)
    mock_ai_completions_dal.ask.return_value = (
        "description: leaderboards are a feature where users can compete in leagues"
    )
    target_topic_input = "leaderboards"
    assert (
        topic_definition_manager.get_topic_description(target_topic_input).lower()
        == "leaderboards are a feature where users can compete in leagues"
    )

    mock_ai_completions_dal.ask.return_value = None
    target_topic_input = "leaderboards"
    assert (
        topic_definition_manager.get_topic_description(target_topic_input).lower() == "leaderboards"
    )

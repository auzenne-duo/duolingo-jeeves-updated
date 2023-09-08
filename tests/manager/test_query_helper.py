import json
from datetime import datetime
from unittest.mock import patch

from jeeves.manager.query_helper import DSLQueryResponse, QueryHelper

now = datetime.now()


@patch("jeeves.dal.ai_completions_dal.AICompletionsDAL")
@patch("jeeves.dal.opensearch_interface.OpenSearchDAL")
@patch("jeeves.dal.sentiment_classifier_dal.SentimentClassifierDAL")
def test_get_dsl_query_and_topics(
    mock_ai_completions_dal, mock_opensearch_dal, mock_sentiment_classifier_dal
):
    """
    Tests that the get_dsl_query_and_topics function correctly processes the output from ai_completions_backend
    """
    resp_dict = {
        "query": {
            "bool": {
                "must": [
                    {"match": {"data_source": "Zendesk"}},
                    {"match": {"via.channel": "Twitter"}},
                    {
                        "range": {
                            "date_time": {
                                "gte": "2023-05-01T00:00:00",
                                "lte": "2023-05-31T23:59:59",
                            }
                        }
                    },
                ]
            }
        },
        "lucene_filters": {
            "data_source": "Zendesk",
            "via.channel": "Twitter",
            "date_time": "[2023-05-01T00:00:00 TO 2023-05-31T23:59:59]",
        },
        "topic": "Leaderboards",
    }
    mock_ai_completions_dal.ask.return_value = json.dumps(resp_dict)

    user_prompt = "What do people on Twitter think about leaderboards on Android in the last month?"
    query_helper = QueryHelper(
        mock_ai_completions_dal, mock_opensearch_dal, mock_sentiment_classifier_dal
    )
    response: DSLQueryResponse = query_helper.get_dsl_query_and_topics(user_prompt)
    assert response.lucene_filters["data_source"] == "Zendesk"
    assert response.lucene_filters["via.channel"] == "Twitter"
    assert response.lucene_filters["date_time"] == "[2023-05-01T00:00:00 TO 2023-05-31T23:59:59]"
    assert response.dsl_query["bool"]["must"][0]["match"]["data_source"] == "Zendesk"
    assert response.dsl_query["bool"]["must"][1]["match"]["via.channel"] == "Twitter"
    assert (
        response.dsl_query["bool"]["must"][2]["range"]["date_time"]["gte"] == "2023-05-01T00:00:00"
    )
    assert (
        response.dsl_query["bool"]["must"][2]["range"]["date_time"]["lte"] == "2023-05-31T23:59:59"
    )
    assert response.target_topic == "Leaderboards"

    # Test an error
    mock_ai_completions_dal.ask.return_value = None

    try:
        response: DSLQueryResponse = query_helper.get_dsl_query_and_topics(user_prompt)
        assert False
    except TypeError:
        assert True

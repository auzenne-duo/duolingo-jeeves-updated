import json
import unittest
from copy import deepcopy
from datetime import datetime
from typing import Any, Dict
from unittest.mock import MagicMock, Mock, patch

import numpy as np

from jeeves.config.config import SENTENCE_TRANSFORMER_MODEL, get_config
from jeeves.dal.opensearch_interface import OpenSearchDAL
from jeeves.model.jira_document import JiraDocument
from jeeves.model.shake_to_report_category import ShakeToReportCategory
from jeeves.model.spike_categories import SpikeCategory

successful_response = {"_shards": {"total": 2, "successful": 2}}
failed_response = {"_shards": {"total": 2, "successful": 1}}

mock_opensearch = MagicMock()
mock_search = MagicMock()

data_version_identifier = get_config().get_nested(["opensearch", "data_version_identifier"])
spikename = f"jeeves_spikes_v_{data_version_identifier}"

now_datetime = datetime.now()
jira_doc_templ = JiraDocument(
    data_source="JIRA",
    date_time=datetime(2022, 1, 1),
    lemmatized_terms=["example", "hello"],
    embeddings={
        SENTENCE_TRANSFORMER_MODEL: [1, 2, 3],
    },
    document_id="doc1",
    jeeves_uid="uid1",
    header_text="header",
    body_text="I am body text",
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
    issue_key="DLAI-1234",
    issue_links=[],
    issue_type="Bug",
    project="DLAI",
    linked_duplicate_keys=[],
    creation_date=now_datetime,
    updated_date=now_datetime,
    resolution_date=now_datetime,
    status="To Do",
    resolution="",
    components=[],
    feature_url="https://duolingo.atlassian.net/rest/api/3/customFieldOption/1",
    feature="feature",
    priority="High",
    reporter="",
    reporter_email="",
    assignee="",
    comments=[],
    labels=[],
    experiment_conditions={},
    jira_attachments=[],
    parent_issue=None,
    child_issues=[],
    is_dev_related=False,
    area="",
    team="",
    codebase="",
)


def create_mock_hit(mock_doc: Dict[str, Any], score: float) -> Dict[str, Any]:
    jira_doc: Dict[str, Any] = JiraDocument.serialize_to_json(jira_doc_templ)
    for key, value in mock_doc["_source"].items():
        jira_doc[key] = value

    return {"_id": mock_doc["_id"], "_score": score, "_source": jira_doc}


class TestOpenSearchInterface(unittest.TestCase):
    @patch("jeeves.dal.opensearch_interface.OpenSearch", Mock(return_value=mock_opensearch))
    def __init__(self, method_name: str) -> None:
        super(TestOpenSearchInterface, self).__init__(method_name)
        self.opensearch = mock_opensearch
        self.dal = OpenSearchDAL()

        self.mock_hits = [
            {"key_as_string": "2022-01-01", "key": 1648440000000, "doc_count": 1},
            {"key_as_string": "2022-01-02", "key": 1648526400000, "doc_count": 0},
            {"key_as_string": "2022-01-03", "key": 1648612800000, "doc_count": 3},
        ]

        self.mock_doc_1 = {
            "_id": 1,
            "_source": {
                "data_source": "JIRA",
                "date_time": datetime(2022, 1, 2),
                "embeddings": {
                    SENTENCE_TRANSFORMER_MODEL: [1, 2, 3],
                },
                "issue_key": "DLAI-1234",
                "lemmatized_terms": ["example", "hello"],
                "project": "DLAI",
            },
        }
        self.mock_doc_2 = {
            "_id": 2,
            "_source": {
                "data_source": "JIRA",
                "date_time": datetime(2022, 1, 4),
                "embeddings": {
                    SENTENCE_TRANSFORMER_MODEL: [1, 2, 3],
                },
                "issue_key": "DLAW-2345",
                "lemmatized_terms": ["example", "hello"],
                "project": "DLAW",
            },
        }
        self.mock_doc_3 = {
            "_id": 3,
            "_source": {
                "data_source": "JIRA",
                "date_time": datetime(2022, 1, 4),
                "embeddings": {
                    SENTENCE_TRANSFORMER_MODEL: [9, 8, 7],
                },
                "issue_key": "DLAI-3456",
                "lemmatized_terms": ["hello"],
                "project": "DLAI",
            },
        }
        self.mock_doc_4 = {
            "_id": 4,
            "_source": {
                "data_source": "JIRA",
                "date_time": datetime(2022, 1, 4),
                "embeddings": {
                    SENTENCE_TRANSFORMER_MODEL: [1, 3, 3],
                },
                "issue_key": "DLAI-4567",
                "lemmatized_terms": ["hello", "rare"],
                "project": "DLAI",
            },
        }
        self.mock_doc_5 = {
            "_id": 5,
            "_source": {
                "data_source": "JIRA",
                "date_time": datetime(2022, 1, 6),
                "embeddings": {
                    SENTENCE_TRANSFORMER_MODEL: [1, 2, 2],
                },
                "issue_key": "DLAI-5678",
                "lemmatized_terms": ["hello", "there"],
                "project": "DLAI",
            },
        }
        self.expected_index = f"jeeves_tickets_v_{data_version_identifier}"

    @patch("jeeves.dal.opensearch_interface.Search", Mock(return_value=mock_search))
    @patch(
        "jeeves.dal.opensearch_interface.OpenSearchDAL.get_min_and_max_document_dates",
        Mock(return_value={"min": "2022-01-01", "max": "2022-02-01"}),
    )
    def test_get_num_tickets_by_day(self) -> None:
        mock_search.filter().filter().execute().aggregations.doc_count_by_day.buckets = (
            self.mock_hits
        )

        result = self.dal.get_num_tickets_by_day(
            datetime(2022, 3, 1), SpikeCategory.ALL_SPIKES, "en"
        )
        expected = {"2022-01-01": 1, "2022-01-02": 0, "2022-01-03": 3}
        self.assertEqual(expected, result)

        mock_search.filter.assert_called_with("term", language="en")
        mock_search.filter().filter.assert_called_with(
            "range", date_time={"gte": "2022-01-01T00:00:00Z", "lte": "2022-03-02T00:00:00Z"}
        )

    @patch("jeeves.dal.opensearch_interface.Search", Mock(return_value=mock_search))
    @patch(
        "jeeves.dal.opensearch_interface.OpenSearchDAL.get_min_and_max_document_dates",
        Mock(return_value={"min": "2022-01-01", "max": "2022-02-01"}),
    )
    def test_get_num_tickets_by_day_start_date(self) -> None:
        mock_response = [
            {"key_as_string": "2022-01-01", "key": 1648440000000, "doc_count": 1},
            {"key_as_string": "2022-01-02", "key": 1648526400000, "doc_count": 0},
            {"key_as_string": "2022-01-03", "key": 1648612800000, "doc_count": 3},
        ]
        mock_search.filter().filter().execute().aggregations.doc_count_by_day.buckets = (
            mock_response
        )

        result = self.dal.get_num_tickets_by_day(
            datetime(2022, 3, 1), SpikeCategory.ALL_SPIKES, "en", start_date=datetime(2021, 1, 2)
        )
        expected = {"2022-01-01": 1, "2022-01-02": 0, "2022-01-03": 3}
        self.assertEqual(expected, result)

        mock_search.filter.assert_called_with("term", language="en")
        mock_search.filter().filter.assert_called_with(
            "range", date_time={"gte": "2021-01-02T00:00:00Z", "lte": "2022-03-02T00:00:00Z"}
        )

    @patch("jeeves.dal.opensearch_interface.MIN_SAMPLES_THRESHOLD", 2)
    @patch(
        "jeeves.dal.opensearch_interface.datetime",
        MagicMock(today=MagicMock(return_value=datetime(2022, 1, 4))),
    )
    def test_generate_term_stats(self) -> None:
        self.opensearch.scroll.side_effect = [
            {
                "_scroll_id": 10,
                "hits": {
                    "hits": [
                        json.loads(json.dumps(self.mock_doc_3, default=str)),
                        json.loads(json.dumps(self.mock_doc_4, default=str)),
                    ]
                },
            },
            {"_scroll_id": 10, "hits": {"hits": []}},
        ]
        self.opensearch.search.return_value = {
            "_scroll_id": 10,
            "hits": {
                "hits": [
                    # Convert datetime type to string
                    json.loads(str(json.dumps(self.mock_doc_1, default=str))),
                    json.loads(str(json.dumps(self.mock_doc_2, default=str))),
                ]
            },
        }

        start_date = datetime.strptime("2022-01-01", "%Y-%m-%d")
        result = self.dal.generate_term_stats(start_date)

        expected_query = {
            "size": 1000,
            "query": {
                "bool": {
                    "filter": [
                        {"range": {"date_time": {"gt": "2022-01-01T00:00:00Z"}}},
                        {"term": {"language": "en"}},
                    ]
                }
            },
        }
        self.opensearch.search.assert_any_call(
            index=self.expected_index,
            body=expected_query,
            scroll="2s",
        )

        self.opensearch.scroll.assert_called_with(scroll_id=10, scroll="2s")

        expected = {
            "avg_docs_per_day": 2.0,
            "words": {
                "hello": {"mean": np.mean([3, 1, 0, 0]), "std": np.std([3, 1, 0, 0])},
                "example": {"mean": np.mean([1, 1, 0, 0]), "std": np.std([1, 1, 0, 0])},
            },
        }
        self.assertEqual(result, expected)

    @patch(
        "jeeves.dal.opensearch_interface.OpenSearchDAL._ensure_specific_jira_issue",
        Mock(return_value=jira_doc_templ),
    )
    def test_find_potential_jira_duplicates(self) -> None:
        depth = 30

        hit_1 = create_mock_hit(self.mock_doc_1, 0.9)  # Second-best match
        hit_2 = create_mock_hit(
            # In different project -- should be filtered out
            self.mock_doc_2,
            0.95,
        )
        hit_3 = create_mock_hit(self.mock_doc_3, 0.7)  # Score too low -- should be filtered out
        hit_4 = create_mock_hit(self.mock_doc_4, 0.95)  # Top match
        hit_5 = create_mock_hit(self.mock_doc_5, 1.0)  # Duplicate key -- should be filtered out

        # TODO: Test that issues linked together in JIRA are not returned as duplicates

        self.opensearch.search.return_value = {
            "hits": {
                "hits": [
                    hit_1,
                    hit_2,
                    hit_3,
                    hit_4,
                    hit_5,
                ]
            },
        }

        result_dups = self.dal.find_potential_jira_duplicates(
            issue_key="DLAI-1234",
            max_search_depth=depth,
            num_results=1,
            should_filter_project=True,
        )

        expected_query = {
            "size": depth,
            "query": {
                "bool": {
                    "filter": {
                        "bool": {
                            "must": [
                                {
                                    # 30 days before target doc
                                    "range": {"date_time": {"gte": datetime(2021, 12, 2)}}
                                }
                            ]
                        }
                    },
                    "must": [
                        {
                            "knn": {
                                f"embeddings.{SENTENCE_TRANSFORMER_MODEL}": {
                                    "k": depth,
                                    "vector": [1, 2, 3],
                                }
                            }
                        }
                    ],
                }
            },
        }

        self.opensearch.search.assert_any_call(
            index=self.expected_index,
            body=expected_query,
        )

        jira_doc_4 = deepcopy(jira_doc_templ)
        for key, value in self.mock_doc_4["_source"].items():
            setattr(jira_doc_4, key, value)

        self.maxDiff = None
        expected_dups = [jira_doc_4]
        self.assertEqual(len(expected_dups), len(result_dups))
        for expected, result in zip(expected_dups, result_dups):
            self.assertEqual(expected.__dict__, result.__dict__)

    def test_filter_text(self) -> None:
        text = (
            "(@DailyWelshWords). In :right_arrow: (theory), @duolingo-hq *I* "
            "https://duolingo.squarespace.com/tips can't bob@gmail.com read 💁👌🎍😍"
        )
        expected = "In theory I cant read"
        result = self.dal.filter_text(text)
        self.assertEqual(result, expected)

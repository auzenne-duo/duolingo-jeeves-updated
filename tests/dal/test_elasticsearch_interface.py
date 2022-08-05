# from elasticsearch_dsl import A, Mapping, Q, Search
import unittest
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import numpy as np

from jeeves.config.config import DATA_VERSION_IDENTIFIER
from jeeves.dal.elasticsearch_interface import ElasticsearchDAL
from jeeves.model.spike_categories import SpikeCategory

successful_response = {"_shards": {"total": 2, "successful": 2}}
failed_response = {"_shards": {"total": 2, "successful": 1}}

mock_es = MagicMock()
mock_search = MagicMock()
spikename = f"jeeves_spikes_v_{DATA_VERSION_IDENTIFIER}"


class TestElasticSearchInterface(unittest.TestCase):
    @patch("jeeves.dal.elasticsearch_interface.Elasticsearch", Mock(return_value=mock_es))
    def __init__(self, *args, **kwargs):
        super(TestElasticSearchInterface, self).__init__(*args, **kwargs)
        self.es = mock_es
        self.dal = ElasticsearchDAL()

        self.mock_hit_1 = MagicMock(date_time="2022-01-02T12:00:00+00:00")
        self.mock_hit_2 = MagicMock(date_time="2022-01-10T00:00:00+00:00")
        self.mock_doc_1 = {
            "_id": 1,
            "_source": {"date_time": "2022-01-02"},
            "term_vectors": {"body_text": {"terms": {"example", "hello", "gr8"}}},
        }
        self.mock_doc_2 = {
            "_id": 2,
            "_source": {"date_time": "2022-01-04"},
            "term_vectors": {"body_text": {"terms": {"example", "hello"}}},
        }
        self.mock_doc_3 = {
            "_id": 3,
            "_source": {"date_time": "2022-01-04"},
            "term_vectors": {"body_text": {"terms": {"hello", "gr8"}}},
        }
        self.mock_doc_4 = {
            "_id": 4,
            "_source": {"date_time": "2022-01-4"},
            "term_vectors": {"body_text": {"terms": {"hello", "rare"}}},
        }
        self.mock_scan = MagicMock(return_value=[self.mock_hit_2, self.mock_hit_1])
        self.expected_index = f"jeeves_tickets_v_{DATA_VERSION_IDENTIFIER}"

    @patch("jeeves.dal.elasticsearch_interface.Search", Mock(return_value=mock_search))
    @patch(
        "jeeves.dal.elasticsearch_interface.ElasticsearchDAL.get_min_and_max_document_dates",
        Mock(return_value={"min": "2022-01-01", "max": "2022-02-01"}),
    )
    def test_get_average_num_tickets_per_day(self):
        mock_search.filter().filter().scan = self.mock_scan

        self.assertEqual(
            self.dal.get_average_num_tickets_per_day(SpikeCategory.ALL_SPIKES, "en"), 2 / 7.5
        )

        mock_search.filter.assert_called_with("range", date_time={"gt": "2022-01-01T00:00:00Z"})
        mock_search.filter().filter.assert_called_with("term", language="en")

    @patch("jeeves.dal.elasticsearch_interface.Search", Mock(return_value=mock_search))
    @patch(
        "jeeves.dal.elasticsearch_interface.ElasticsearchDAL.get_min_and_max_document_dates",
        Mock(return_value={"min": "2020-01-01", "max": "2022-01-12"}),
    )
    @patch("jeeves.dal.elasticsearch_interface.HISTORY_WINDOW_SIZE", 10)
    def test_get_average_num_tickets_per_day_early_min(self):
        mock_search.filter().filter().scan = self.mock_scan

        self.assertEqual(
            self.dal.get_average_num_tickets_per_day(SpikeCategory.ALL_SPIKES, "en"), 2 / 7.5
        )

        mock_search.filter.assert_called_with("range", date_time={"gt": "2022-01-02T00:00:00Z"})
        mock_search.filter().filter.assert_called_with("term", language="en")

    @patch("jeeves.dal.elasticsearch_interface.MIN_SAMPLES_THRESHOLD", 2)
    @patch(
        "jeeves.dal.elasticsearch_interface.datetime",
        MagicMock(today=MagicMock(return_value=datetime(2022, 1, 4))),
    )
    def test_generate_term_stats(self):
        self.es.search.return_value = {
            "_scroll_id": 10,
            "hits": {"hits": [self.mock_doc_1, self.mock_doc_2]},
        }
        self.es.scroll.side_effect = [
            {"_scroll_id": 10, "hits": {"hits": [self.mock_doc_3, self.mock_doc_4]}},
            {"_scroll_id": 10, "hits": {"hits": []}},
        ]
        self.es.mtermvectors.side_effect = [
            {"docs": [self.mock_doc_1, self.mock_doc_2]},
            {"docs": [self.mock_doc_3, self.mock_doc_4]},
        ]

        start_date = datetime.strptime("2022-01-01", "%Y-%m-%d")
        result = self.dal.generate_term_stats(start_date, "en")

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
        self.es.search.assert_called_with(
            index=self.expected_index,
            body=expected_query,
            scroll="2s",
        )

        self.es.scroll.assert_called_with(scroll_id=10, scroll="2s")

        self.es.mtermvectors.assert_any_call(
            body={"ids": [1, 2], "parameters": {"fields": ["body_text"]}}, index=self.expected_index
        )
        self.es.mtermvectors.assert_any_call(
            body={"ids": [3, 4], "parameters": {"fields": ["body_text"]}}, index=self.expected_index
        )

        expected = {
            "avg_docs_per_day": 2,
            "words": {
                "hello": {"mean": np.mean([3, 1, 0, 0]), "std": np.std([3, 1, 0, 0])},
                "example": {"mean": np.mean([1, 1, 0, 0]), "std": np.std([1, 1, 0, 0])},
            },
        }
        self.assertEqual(result, expected)

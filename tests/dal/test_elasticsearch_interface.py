# from elasticsearch_dsl import A, Mapping, Q, Search
import unittest
from datetime import datetime
from unittest.mock import MagicMock, Mock, patch

import numpy as np
from duolingo_base.config import Config

from jeeves.dal.elasticsearch_interface import ElasticsearchDAL
from jeeves.model.spike_categories import SpikeCategory

successful_response = {"_shards": {"total": 2, "successful": 2}}
failed_response = {"_shards": {"total": 2, "successful": 1}}

mock_es = MagicMock()
mock_search = MagicMock()

_config = Config.load_config()

data_version_identifier = _config.get_nested(["elasticsearch", "data_version_identifier"])
spikename = f"jeeves_spikes_v_{data_version_identifier}"


class TestElasticSearchInterface(unittest.TestCase):
    @patch("jeeves.dal.elasticsearch_interface.OpenSearch", Mock(return_value=mock_es))
    def __init__(self, *args, **kwargs):
        super(TestElasticSearchInterface, self).__init__(*args, **kwargs)
        self.es = mock_es
        self.dal = ElasticsearchDAL()

        self.mock_hits = [
            {"key_as_string": "2022-01-01", "key": 1648440000000, "doc_count": 1},
            {"key_as_string": "2022-01-02", "key": 1648526400000, "doc_count": 0},
            {"key_as_string": "2022-01-03", "key": 1648612800000, "doc_count": 3},
        ]

        self.mock_doc_1 = {
            "_id": 1,
            "_source": {"date_time": "2022-01-02", "lemmatized_terms": ["example", "hello"]},
        }
        self.mock_doc_2 = {
            "_id": 2,
            "_source": {"date_time": "2022-01-04", "lemmatized_terms": ["example", "hello"]},
        }
        self.mock_doc_3 = {
            "_id": 3,
            "_source": {"date_time": "2022-01-04", "lemmatized_terms": ["hello"]},
        }
        self.mock_doc_4 = {
            "_id": 4,
            "_source": {"date_time": "2022-01-4", "lemmatized_terms": ["hello", "rare"]},
        }
        self.expected_index = f"jeeves_tickets_v_{data_version_identifier}"

    @patch("jeeves.dal.elasticsearch_interface.Search", Mock(return_value=mock_search))
    @patch(
        "jeeves.dal.elasticsearch_interface.ElasticsearchDAL.get_min_and_max_document_dates",
        Mock(return_value={"min": "2022-01-01", "max": "2022-02-01"}),
    )
    def test_get_num_tickets_by_day(self):
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

    @patch("jeeves.dal.elasticsearch_interface.Search", Mock(return_value=mock_search))
    @patch(
        "jeeves.dal.elasticsearch_interface.ElasticsearchDAL.get_min_and_max_document_dates",
        Mock(return_value={"min": "2022-01-01", "max": "2022-02-01"}),
    )
    def test_get_num_tickets_by_day_start_date(self):
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

    @patch("jeeves.dal.elasticsearch_interface.MIN_SAMPLES_THRESHOLD", 2)
    @patch(
        "jeeves.dal.elasticsearch_interface.datetime",
        MagicMock(today=MagicMock(return_value=datetime(2022, 1, 4))),
    )
    def test_generate_term_stats(self):
        self.es.scroll.side_effect = [
            {"_scroll_id": 10, "hits": {"hits": [self.mock_doc_3, self.mock_doc_4]}},
            {"_scroll_id": 10, "hits": {"hits": []}},
        ]
        self.es.search.return_value = {
            "_scroll_id": 10,
            "hits": {"hits": [self.mock_doc_1, self.mock_doc_2]},
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
        self.es.search.assert_any_call(
            index=self.expected_index,
            body=expected_query,
            scroll="2s",
        )

        self.es.scroll.assert_called_with(scroll_id=10, scroll="2s")

        expected = {
            "avg_docs_per_day": 2.0,
            "words": {
                "hello": {"mean": np.mean([3, 1, 0, 0]), "std": np.std([3, 1, 0, 0])},
                "example": {"mean": np.mean([1, 1, 0, 0]), "std": np.std([1, 1, 0, 0])},
            },
        }
        self.assertEqual(result, expected)

    def test_filter_text(self):
        text = "(@DailyWelshWords). In :right_arrow: (theory), @duolingo-hq *I* https://duolingo.squarespace.com/tips can't bob@gmail.com read 💁👌🎍😍"
        expected = "In theory I cant read"
        result = self.dal.filter_text(text)
        self.assertEqual(result, expected)

import unittest
from unittest.mock import MagicMock, Mock, patch

from duolingo_base.config import Config

from jeeves.dal.spike_index_interface import SpikeIndexDAL
from jeeves.model.spike_categories import SpikeCategory

successful_response = {"_shards": {"total": 2, "successful": 2}}
failed_response = {"_shards": {"total": 2, "successful": 1}}

mock_es = MagicMock()
mock_search = MagicMock()

_config = Config.load_config()
spikename = f"jeeves_spikes_v_{_config.get_nested(['opensearch', 'data_version_identifier'])}"

mock_doc_1 = MagicMock(word="doubling", date="2022-08-28", confirmed=False)
mock_doc_2 = MagicMock(word="double", date="2022-08-29", confirmed=True)
mock_doc_3 = MagicMock(word="doubled", date="2022-09-10", confirmed=True)
mock_doc_4 = MagicMock(word="doubled", date="2022-09-11", confirmed=True)
mock_doc_5 = MagicMock(word="crash", date="2022-08-10", confirmed=False)
mock_doc_6 = MagicMock(word="crashing", date="2022-09-10", confirmed=False)
mock_doc_7 = MagicMock(word="crashed", date="2022-08-20", confirmed=False)
mock_doc_8 = MagicMock(word="bubble", date="2022-08-20", confirmed=True)


class TestSpikeIndexInterface(unittest.TestCase):
    @patch("jeeves.dal.spike_index_interface.OpenSearch", Mock(return_value=mock_es))
    def __init__(self, *args, **kwargs):
        super(TestSpikeIndexInterface, self).__init__(*args, **kwargs)
        self.es = mock_es
        self.dal = SpikeIndexDAL()

    def test_set_spike_confirm_to_true(self):
        self.es.update = MagicMock(return_value=successful_response)
        self.dal.set_spike_confirm_setting("13", True, 10)
        self.es.update.assert_called_with(
            index=spikename,
            id="13",
            body={"doc": {"confirmed": True, "confirmed_user_id": 10}},
            refresh=True,
        )

    def test_set_spike_confirm_to_false(self):
        self.es.update = MagicMock(return_value=successful_response)
        self.dal.set_spike_confirm_setting("13-id", False, 10)
        self.es.update.assert_called_with(
            index=spikename,
            id="13-id",
            body={"doc": {"confirmed": False, "confirmed_user_id": 10}},
            refresh=True,
        )

    def test_set_spike_confirm_failed(self):
        self.es.update = MagicMock(return_value=failed_response)
        self.assertRaises(Exception, self.dal.set_spike_confirm_setting, "13", True, 10)
        self.es.update.assert_called_with(
            index=spikename,
            id="13",
            body={"doc": {"confirmed": True, "confirmed_user_id": 10}},
            refresh=True,
        )

    def test_set_spike_fixed_to_true(self):
        self.es.update = MagicMock(return_value=successful_response)
        self.dal.set_spike_fixed_setting("13", True, 10)
        self.es.update.assert_called_with(
            index=spikename,
            id="13",
            body={"doc": {"fixed": True, "fixed_user_id": 10}},
            refresh=True,
        )

    def test_set_spike_fixed_to_false(self):
        self.es.update = MagicMock(return_value=successful_response)
        self.dal.set_spike_fixed_setting("13", False, 10)
        self.es.update.assert_called_with(
            index=spikename,
            id="13",
            body={"doc": {"fixed": False, "fixed_user_id": 10}},
            refresh=True,
        )

    def test_set_spike_fixed_failed(self):
        self.es.update = MagicMock(return_value=failed_response)
        self.assertRaises(Exception, self.dal.set_spike_fixed_setting, "13", True, 10)
        self.es.update.assert_called_with(
            index=spikename,
            id="13",
            body={"doc": {"fixed": True, "fixed_user_id": 10}},
            refresh=True,
        )

    def test_set_spike_email_sent(self):
        self.es.update = MagicMock(return_value=successful_response)
        self.dal.set_spike_email_sent("13", 123, "2000-01-01")
        self.es.update.assert_called_with(
            index=spikename,
            id="13",
            body={"doc": {"email_user_id": 123, "email_sent_date": "2000-01-01"}},
            refresh=True,
        )

    def test_set_spike_email_sent_failed(self):
        self.es.update = MagicMock(return_value=failed_response)
        self.assertRaises(Exception, self.dal.set_spike_email_sent, "13", 123, "2000-01-01")
        self.es.update.assert_called_with(
            index=spikename,
            id="13",
            body={"doc": {"email_user_id": 123, "email_sent_date": "2000-01-01"}},
            refresh=True,
        )

    @patch("jeeves.dal.spike_index_interface.Search", Mock(return_value=mock_search))
    def test_calculate_spike_stats(self):
        mock_search.filter().filter().scan = MagicMock(
            return_value=[
                mock_doc_1,
                mock_doc_2,
                mock_doc_3,
                mock_doc_4,
                mock_doc_5,
                mock_doc_6,
                mock_doc_7,
                mock_doc_8,
            ]
        )
        self.es.search = MagicMock(
            return_value={
                "aggregations": {
                    "spikes_by_month": {
                        "buckets": [
                            {
                                "confirm_status": {
                                    "buckets": [
                                        {"key": True, "doc_count": 1},
                                        {"key": False, "doc_count": 2},
                                    ]
                                },
                                "doc_count": 3,
                                "key_as_string": "2022-08-01",
                            },
                            {
                                "confirm_status": {
                                    "buckets": [
                                        {"key": True, "doc_count": 1},
                                        {"key": False, "doc_count": 1},
                                    ]
                                },
                                "doc_count": 2,
                                "key_as_string": "2022-09-01",
                            },
                        ]
                    }
                }
            }
        )

        result = self.dal.calculate_spike_stats("en", SpikeCategory.ALL_SPIKES, 3)
        expected = {
            "month_count": [
                {"date_str": "2022-08-01", "confirmed": 1, "total": 3},
                {"date_str": "2022-09-01", "confirmed": 1, "total": 2},
            ],
            "word_count": [
                {
                    "stem": "doubl",
                    "dates": ["2022-08-28", "2022-09-10"],
                    "num_confirmed": 2,
                    "total": 2,
                    "terms": ["double", "doubled", "doubling"],
                },
                {
                    "stem": "crash",
                    "dates": ["2022-08-10", "2022-08-20", "2022-09-10"],
                    "num_confirmed": 0,
                    "total": 3,
                    "terms": ["crash", "crashed", "crashing"],
                },
                {
                    "stem": "bubbl",
                    "dates": ["2022-08-20"],
                    "num_confirmed": 1,
                    "total": 1,
                    "terms": ["bubble"],
                },
            ],
        }
        for word_stats in result["word_count"]:
            word_stats["terms"].sort()
        self.assertEqual(result, expected)

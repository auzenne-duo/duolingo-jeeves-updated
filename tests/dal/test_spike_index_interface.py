import unittest
from unittest.mock import MagicMock, Mock, patch

from jeeves.config.config import DATA_VERSION_IDENTIFIER
from jeeves.dal.spike_index_interface import SpikeIndexDAL

successful_response = {"_shards": {"total": 2, "successful": 2}}
failed_response = {"_shards": {"total": 2, "successful": 1}}

mock_es = MagicMock()
spikename = f"jeeves_spikes_v_{DATA_VERSION_IDENTIFIER}"


class TestSpikeIndexInterface(unittest.TestCase):
    @patch("jeeves.dal.spike_index_interface.Elasticsearch", Mock(return_value=mock_es))
    def __init__(self, *args, **kwargs):
        super(TestSpikeIndexInterface, self).__init__(*args, **kwargs)
        self.es = mock_es
        self.dal = SpikeIndexDAL()

    def test_set_spike_confirm_to_true(self):
        self.es.update = MagicMock(return_value=successful_response)
        self.dal.set_spike_confirm_setting("13", True, 10)
        self.es.update.assert_called_with(
            index=spikename, id="13", body={"doc": {"confirmed": True, "user_id": 10}}
        )

    def test_set_spike_confirm_to_false(self):
        self.es.update = MagicMock(return_value=successful_response)
        self.dal.set_spike_confirm_setting("13-id", False, 10)
        self.es.update.assert_called_with(
            index=spikename, id="13-id", body={"doc": {"confirmed": False, "user_id": 10}}
        )

    def test_set_spike_confirm_failed(self):
        self.es.update = MagicMock(return_value=failed_response)
        self.assertRaises(Exception, self.dal.set_spike_confirm_setting, "13", True, 10)
        self.es.update.assert_called_with(
            index=spikename, id="13", body={"doc": {"confirmed": True, "user_id": 10}}
        )

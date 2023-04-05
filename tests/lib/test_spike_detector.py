import datetime
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from jeeves.lib.spike_detector import (
    _calculate_combined_mean_std,
    _calculate_spike_score,
    _get_num_unique_users,
)
from jeeves.model.appfigures_document import AppfiguresDocument
from jeeves.model.jira_document import JiraDocument
from jeeves.model.spike_categories import SpikeCategory
from jeeves.model.zendesk_document import ZendeskDocument


def create_jeeves_doc(doc_type, user_id=None, username=None, **kwargs):
    doc = MagicMock()
    doc.get_data_source_identifier.return_value = doc_type
    doc.user_id = user_id
    doc.username = username
    for kwarg in kwargs:
        setattr(doc, kwarg, kwargs[kwarg])
    return doc


@patch("jeeves.lib.spike_detector.app_registry", MagicMock())
class TestSpikeDetector(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super(TestSpikeDetector, self).__init__(*args, **kwargs)

    def test_calculate_spike_score(self):
        result = _calculate_spike_score(
            {"2022-01-02": 2, "2022-01-04": 6, "2022-02-01": 7},
            datetime.date(2022, 1, 4),
            4,
            "bug",
            10,
            "en",
            {"words": {}},
            SpikeCategory.ALL_SPIKES,
        )

        count_history = [0, 2, 0, 6]
        expected = (6 - np.mean(count_history)) / (np.std(count_history))
        self.assertEqual(expected, result)

    def test_calculate_spike_score_first_instance_of_word(self):
        result = _calculate_spike_score(
            {"2022-01-04": 6, "2022-02-01": 7},
            datetime.date(2022, 1, 4),
            4,
            "bug",
            10,
            "en",
            {"words": {}},
            SpikeCategory.ALL_SPIKES,
        )

        expected = -1
        self.assertEqual(expected, result)

    def test_calculate_spike_score_second_instance_of_word(self):
        result = _calculate_spike_score(
            {"2022-01-03": 6, "2022-01-04": 6, "2022-02-01": 7},
            datetime.date(2022, 1, 4),
            4,
            "bug",
            10,
            "en",
            {"words": {}},
            SpikeCategory.ALL_SPIKES,
        )

        count_history = [0, 0, 6, 6]
        expected = (6 - np.mean(count_history)) / (np.std(count_history))
        self.assertEqual(expected, result)

    def test_calculate_combined_mean_std(self):
        dist_1 = [0, 0, 1]
        dist_2 = [10, 1]
        dist_all = dist_1 + dist_2

        mean, std = _calculate_combined_mean_std(
            len(dist_1),
            np.mean(dist_1),
            np.std(dist_1),
            len(dist_2),
            np.mean(dist_2),
            np.std(dist_2),
        )
        expected_mean, expected_std = np.mean(dist_all), np.std(dist_all)
        self.assertAlmostEqual(expected_mean, mean)
        self.assertAlmostEqual(expected_std, std)

    def test_get_num_unique_users(self):
        docs = [
            create_jeeves_doc(JiraDocument.get_data_source_identifier(), reporter="a"),
            create_jeeves_doc(JiraDocument.get_data_source_identifier(), reporter="b"),
            create_jeeves_doc(JiraDocument.get_data_source_identifier(), reporter="a"),
        ]
        self.assertEqual(2, _get_num_unique_users(docs))

    def test_get_num_unique_users_different_types(self):
        docs = [
            create_jeeves_doc(JiraDocument.get_data_source_identifier(), reporter="a"),
            create_jeeves_doc(
                ZendeskDocument.get_data_source_identifier(), requester_id="b", user_id=123
            ),
            create_jeeves_doc(
                AppfiguresDocument.get_data_source_identifier(), author="b", username="duo"
            ),
        ]
        self.assertEqual(3, _get_num_unique_users(docs))

    def test_get_num_unique_users_different_types_overlap(self):
        # Even though two documents have the same user id, for simplicity we only count users as the same if they have all the same attributes
        docs = [
            create_jeeves_doc(JiraDocument.get_data_source_identifier(), reporter="a"),
            create_jeeves_doc(
                ZendeskDocument.get_data_source_identifier(), requester_id="b", user_id=123
            ),
            create_jeeves_doc(JiraDocument.get_data_source_identifier(), reporter="b", user_id=123),
        ]
        self.assertEqual(3, _get_num_unique_users(docs))

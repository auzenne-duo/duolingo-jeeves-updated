import datetime
import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from jeeves.lib.spike_detector import _calculate_combined_mean_std, _calculate_spike_score


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

import unittest
from datetime import datetime

from jeeves.model.quality_score_params import PriorityValue, QualityScoreParams, Resolution


class TestQualityScoreParams(unittest.TestCase):
    def test_init_from_jira_data(self):
        params = QualityScoreParams.init_from_jira_data(
            datetime(2000, 1, 20), "High", datetime(2000, 1, 25), [], "Done"
        )
        expected = QualityScoreParams(
            True,
            PriorityValue.HIGH_HIGHEST,
            Resolution.FIXED_WITHIN_ONE_WEEK,
            100,
            "High Fixed within one week",
        )
        self.assertEqual(params, expected)

        params = QualityScoreParams.init_from_jira_data(
            datetime(2000, 1, 20), "High", None, [], "Unresolved"
        )
        expected = QualityScoreParams(
            False, PriorityValue.HIGH_HIGHEST, Resolution.OPEN, 100, "High Open"
        )

        params = QualityScoreParams.init_from_jira_data(
            datetime(2000, 1, 20), "Low", datetime(2000, 1, 30), [], "Closed as duplicate"
        )
        expected = QualityScoreParams(
            True, PriorityValue.LOW_LOWEST, Resolution.CLOSED_UNFIXED, 1, "Low Closed"
        )
        self.assertEqual(params, expected)

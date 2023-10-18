import unittest
from datetime import datetime

from jeeves.model.quality_score_params import PriorityValue, QualityScoreParams, Resolution


class TestQualityScoreParams(unittest.TestCase):
    def test_init_from_jira_data(self):
        params = QualityScoreParams.init_from_jira_data(
            datetime(2000, 1, 20), "High", datetime(2000, 1, 25), 7, [], "Done"
        )
        expected = QualityScoreParams(
            True,
            PriorityValue.HIGH_HIGHEST,
            Resolution.FIXED_WITHIN_ONE_WEEK,
            107,  # 100 base points + 7 duplicate points
            "High Fixed within one week (7 duplicates)",
        )
        self.assertEqual(params, expected)

        params = QualityScoreParams.init_from_jira_data(
            datetime(2000, 1, 20), "High", None, 1, [], "Unresolved"
        )
        expected = QualityScoreParams(
            False,
            PriorityValue.HIGH_HIGHEST,
            Resolution.OPEN,
            100,  # 100 base points + 0 duplicate points (duplicates don't count for open issues)
            "High Open (1 duplicate)",
        )

        params = QualityScoreParams.init_from_jira_data(
            datetime(2000, 1, 20), "Low", datetime(2000, 1, 30), 3, [], "Closed as duplicate"
        )
        expected = QualityScoreParams(
            True,
            PriorityValue.LOW_LOWEST,
            Resolution.CLOSED_UNFIXED,
            4,  # 1 base point + 3 duplicate points
            "Low Closed (3 duplicates)",
        )
        self.assertEqual(params, expected)

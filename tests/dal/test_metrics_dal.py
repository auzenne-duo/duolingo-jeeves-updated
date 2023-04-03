import unittest
from unittest.mock import MagicMock, patch

from jeeves.dal.metrics_dal import MetricsDAL

mock_requests = MagicMock()
mock_experiments = [
    {
        "name": "experiment1",
        "conditions": ["control", "condition1"],
        "selector": {"weights": [1, 1]},
    },
    {
        "name": "experiment2",
        "conditions": ["control", "condition1", "condition2", "condition3"],
        "selector": {"weights": [1, 7, 1, 1]},
    },
]
mock_get_experiments = MagicMock(return_value=mock_experiments)
mock_duolingo_api_client = MagicMock()


@patch("jeeves.dal.metrics_dal.requests", mock_requests)
@patch("jeeves.dal.metrics_dal.MIN_SHARED_USERS", 3)
@patch("jeeves.dal.metrics_dal.STANDARD_DEVIATION_THRESHOLD", 3)
class TestMetricsDAL(unittest.TestCase):
    @patch("jeeves.dal.metrics_dal.MetricsDAL._get_experiments", mock_get_experiments)
    def __init__(self, *args, **kwargs):
        super(TestMetricsDAL, self).__init__(*args, **kwargs)
        self.dal = MetricsDAL(mock_duolingo_api_client)

    def test_get_shared_conditions(self):
        """
        Of the mock conditions, only the first should be returned
        2. has the control condition
        3. has too low of a spikiness, 1.13
        4. has a rollout of 0, so the p will be 0
        5. has a num_shared below the threshold of 3
        """
        mock_duolingo_api_client.get.return_value.json.return_value = {
            "conditions": [
                {
                    "condition": "condition1",
                    "experiment": "experiment1",
                    "num_shared": 3,
                    "rollout": 0.1,
                },
                {
                    "condition": "control",
                    "experiment": "experiment1",
                    "num_shared": 1,
                    "rollout": 0.0,
                },
                {
                    "condition": "condition1",
                    "experiment": "experiment2",
                    "num_shared": 3,
                    "rollout": 1,
                },
                {
                    "condition": "condition2",
                    "experiment": "experiment2",
                    "num_shared": 3,
                    "rollout": 0.0,
                },
                {
                    "condition": "condition3",
                    "experiment": "experiment2",
                    "num_shared": 2,
                    "rollout": 0.1,
                },
            ]
        }

        result = self.dal.get_shared_conditions([1, 2, 3])

        # p of condition1 should be .05, so mean of .15, std of sqrt(0.1425) ~ 0.377, so spikiness of 2.85/(sqrt(0.1425)) ~ 7.6
        expected = {("experiment1"): 2.85 / (0.1425**0.5)}
        self.assertEqual(result.keys(), expected.keys())
        self.assertAlmostEqual(result[("experiment1")], expected[("experiment1")])

    def test_get_shared_conditions_no_rollout(self):
        mock_duolingo_api_client.get.return_value.json.return_value = {
            "conditions": [
                {
                    "condition": "condition1",
                    "experiment": "experiment1",
                    "num_shared": 3,
                    "rollout": 0.1,
                },
                {
                    "condition": "control",
                    "experiment": "experiment1",
                    "num_shared": 1,
                    "rollout": 0.0,
                },
                {
                    "condition": "condition2",
                    "experiment": "experiment2",
                    "num_shared": 3,
                    "rollout": 0.1,
                },
            ]
        }
        result = self.dal.get_shared_conditions([100, 200, 300, 400], use_rollout=False)
        # p of experiment2.condition2 should be .1, so mean of .4, std of sqrt(.36) ~ .6, so spikiness of 2.6/(.6) ~ 4.33
        expected = {("experiment2"): 2.6 / 0.6}
        self.assertEqual(result.keys(), expected.keys())
        self.assertAlmostEqual(result[("experiment2")], expected[("experiment2")])

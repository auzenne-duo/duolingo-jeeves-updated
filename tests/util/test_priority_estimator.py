import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from jeeves.util.priority_estimator import PriorityEstimator

mock_model = MagicMock()
mock_model.return_value.logits.cpu.return_value.numpy.return_value = np.array([1, 0.5, -0.6])


@patch("jeeves.util.priority_estimator.PriorityEstimator.model", mock_model)
class Test(unittest.TestCase):
    def test_estimate_priority(self):
        result = PriorityEstimator.estimate_priority(
            "Example sentence", "WeChat", "caleb@duolingo.com"
        )
        expected = "Low"
        self.assertEqual(result, expected)

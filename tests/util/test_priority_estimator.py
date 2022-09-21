import unittest
from unittest.mock import MagicMock, patch

import numpy as np

from jeeves.util.priority_estimator import PriorityEstimator

mock_bert = MagicMock()
mock_bert.from_pretrained.return_value.return_value.logits.cpu.return_value.numpy.return_value = (
    np.array([1, 0.5, -0.6])
)


@patch("jeeves.util.priority_estimator.BertTokenizer", MagicMock())
@patch("jeeves.util.priority_estimator.BertForSequenceClassification", mock_bert)
@patch("jeeves.util.priority_estimator.torch", MagicMock())
class Test(unittest.TestCase):
    def test_estimate_priority(self):
        result = PriorityEstimator.estimate_priority("Example sentence", "WeChat", "c")
        expected = "Low"
        self.assertEqual(result, expected)

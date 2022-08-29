import unittest

from jeeves.util.priority_estimator import PriorityEstimator


class Test(unittest.TestCase):
    def test_estimate_priority(self):
        for text, expected in [
            ("Site crashed", "Medium"),
            ("Site crashed and typo", "Low"),
            ("Site crashed font typos", "Low"),
            ("site exists", "Low"),
        ]:
            result = PriorityEstimator.estimate_priority(text)
            self.assertEqual(result, expected)

    def test_estimate_priority_with_dupes(self):
        for args, expected in [
            (("Site crashed", 3), "High"),
            (("Site crashed", 2), "High"),
            (("Site crashed and typo", 3), "High"),
            (("Site crashed and typo", 1), "Medium"),
            (("Many typos", 3), "Medium"),
            (("Still typos", 1), "Low"),
        ]:
            result = PriorityEstimator.estimate_priority(*args)
            self.assertEqual(result, expected)

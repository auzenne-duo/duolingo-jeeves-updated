import unittest

from jeeves.util.priority_estimator import PriorityEstimator


class Test(unittest.TestCase):
    def test_estimate_priority(self):
        for text, expected in [
            ("Stuck here", ("High", ["stuck"])),
            ("Site crashed", ("High", ["crash"])),
            ("Site crashed and typo", ("High", ["crash"])),
            ("Site crashed font typos", ("High", ["crash"])),
            ("site exists", ("Medium", [])),
            ("site has font", ("Low", ["font"])),
        ]:
            result = PriorityEstimator.estimate_priority(text)
            result[1].sort()
            expected[1].sort()
            self.assertEqual(result, expected)

    def test_estimate_priority_with_dupes(self):
        for args, expected in [
            (("Site crashed", 3), ("High", ["crash"])),
            (("Site crashed", 2), ("High", ["crash"])),
            (("Site crashed and typo", 3), ("High", ["crash"])),
            (("Site crashed and typo", 1), ("High", ["crash"])),
            (("Many typos", 3), ("Medium", ["typo"])),
            (("Still typos", 1), ("Low", ["typo"])),
        ]:
            result = PriorityEstimator.estimate_priority(*args)
            result[1].sort()
            expected[1].sort()
            self.assertEqual(result, expected)

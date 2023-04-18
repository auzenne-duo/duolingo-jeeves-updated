import unittest

from jeeves.model.issue_score_parameters import IssueScoreParameters


class TestIssueScoreParameters(unittest.TestCase):
    def test_serialize(self):
        priority = IssueScoreParameters("High")
        result = priority.serialize()
        expected = {
            "is_done": False,
            "priority": "High",
            "score": 100,
            "group": "HIGH_HIGHEST",
            "resolution": "OPEN",
            "time_to_fix": "NOT_WITHIN_ONE_WEEK",
        }
        self.assertEqual(result, expected)

    def test_deserialize(self):
        priority = IssueScoreParameters("High")
        result = IssueScoreParameters.deserialize(priority.serialize())
        self.assertEqual(result, priority)

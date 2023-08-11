import unittest

from jeeves.util.quality_report_util import is_jira_issue_resolved


class TestQualityReportUtil(unittest.TestCase):
    def test_is_jira_issue_resolved(self):
        self.assertFalse(is_jira_issue_resolved("Unresolved"))
        self.assertFalse(is_jira_issue_resolved(""))
        self.assertTrue(is_jira_issue_resolved("Resolved"))
        self.assertTrue(is_jira_issue_resolved("Done"))

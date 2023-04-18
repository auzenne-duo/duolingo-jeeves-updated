import json
import unittest
from unittest.mock import MagicMock, patch

from jeeves.model.jira_document import JiraDocument
from jeeves.util.quality_report_util import get_past_quality_issue_data, is_jira_issue_resolved


class TestQualityReportUtil(unittest.TestCase):
    def test_is_jira_issue_resolved(self):
        issue = JiraDocument.__new__(JiraDocument)
        issue.resolution = "Unresolved"
        self.assertFalse(is_jira_issue_resolved(issue))
        issue.resolution = ""
        self.assertFalse(is_jira_issue_resolved(issue))
        issue.resolution = "Resolved"
        self.assertTrue(is_jira_issue_resolved(issue))
        issue.resolution = "Done"
        self.assertTrue(is_jira_issue_resolved(issue))

    @patch("jeeves.util.quality_report_util.get_s3_client_and_bucket")
    def test_get_past_quality_issue_data(self, mock_s3):
        data = [
            {"date": "2021-09-09", "title": "Path", "issues": {"DLAA-1000": {"status": "Closed"}}}
        ]
        mock_client = MagicMock(download=MagicMock(return_value=json.dumps(data)))
        mock_s3.return_value = (mock_client, MagicMock())
        result = get_past_quality_issue_data("test")
        self.assertEqual(result, data)

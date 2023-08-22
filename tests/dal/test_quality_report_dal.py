import json
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytz

from jeeves.dal.quality_report_dal import QualityReportDAL
from jeeves.model.quality_report import QualityReportIssueDataset
from tests.testutil.test_util_quality_report import REPORT_ISSUE_1, REPORT_ISSUE_11, REPORT_ISSUE_12

mock_duplicate_graph_resolver = MagicMock()
mock_jira_manager = MagicMock()
mock_opensearch = MagicMock()
quality_report_dal = QualityReportDAL(
    mock_duplicate_graph_resolver, mock_jira_manager, mock_opensearch
)


class TestQualityReport(unittest.TestCase):
    @patch("jeeves.dal.quality_report_dal.download_from_jeeves_s3")
    def test_get_past_quality_issue_data(self, mock_s3):
        title = "Path"
        data = json.dumps([{"date": "2021-09-09", "title": title, "issues": []}])
        mock_s3.return_value = data
        result = quality_report_dal.get_past_quality_issue_datasets("test")
        expected = [
            QualityReportIssueDataset(
                date=datetime(2021, 9, 9, tzinfo=pytz.utc),
                title=title,
                issues=[],
                max_dupes_issue_keys=[],
                max_priority_issue_keys=[],
            )
        ]
        self.assertEqual(result, expected)

    def test_filter_dev_issues(self):
        mock_jira_manager.reset_mock()
        mock_jira_manager.download_bulk_issues_with_features.return_value = [REPORT_ISSUE_12]
        mock_jira_manager.download_bulk_issues_with_features.called_once_with(["DLAI-2012"])
        result = quality_report_dal.filter_dev_related_issues(
            [REPORT_ISSUE_1, REPORT_ISSUE_11],
            {
                "DLAI-2001": REPORT_ISSUE_1,
                "DLAI-2011": REPORT_ISSUE_11,
            },
        )
        expected = [REPORT_ISSUE_1]
        self.assertEqual(result, expected)

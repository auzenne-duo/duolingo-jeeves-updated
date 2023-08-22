import unittest
from datetime import datetime
from unittest.mock import MagicMock, call, patch

from jeeves.manager.quality_report_manager import QualityReportManager, QualityReportOverview
from jeeves.model.quality_report import QualityReportArea
from jeeves.util.quality_report_util import QUALITY_REPORT_OVERALL_KEY

mock_quality_report_dal = MagicMock()
quality_report_manager = QualityReportManager(mock_quality_report_dal)

mock_area_name = "Growth"


class TestQualityReportManager(unittest.TestCase):
    @patch("jeeves.manager.quality_report_manager.JIRA_FEATURES", {mock_area_name: {}})
    def test_get_area_quality_overviews(self):
        past_scores = {QUALITY_REPORT_OVERALL_KEY: [("2020-03-14", 45), ("2020-04-18", 48)]}
        mock_quality_report_dal.get_past_quality_scores.return_value = past_scores
        result = quality_report_manager.get_area_quality_overviews()
        expected = [QualityReportOverview(48, past_scores, mock_area_name)]
        self.assertEqual(result, expected)

    @patch("jeeves.manager.quality_report_manager.send_email")
    def test_save_report_data(self, mock_send_email):
        area_report = QualityReportArea.__new__(QualityReportArea)
        non_area_report = MagicMock()
        mock_reports = [non_area_report, area_report]
        quality_report_manager.save_report_data(mock_reports, datetime(2022, 3, 6))
        mock_send_email.assert_has_calls([call(non_area_report), call(area_report)])

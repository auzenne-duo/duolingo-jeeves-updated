import json
import unittest
from datetime import datetime
from unittest.mock import MagicMock, call, patch

from jeeves.manager.quality_report_manager import QualityReportManager, QualityReportOverview
from jeeves.model.quality_report import QualityReportArea
from jeeves.util.date_util import str_to_date
from jeeves.util.quality_report_util import QUALITY_REPORT_OVERALL_KEY

mock_quality_report_dal = MagicMock()
quality_report_manager = QualityReportManager(mock_quality_report_dal)

mock_area_name = "Growth"

fake_quality_report = {
    "scores": {
        "DLAA": [
            ["2024-07-23", 58],
            ["2024-07-30", 34],
            ["2024-08-06", 24],
            ["2024-08-13", 35],
            ["2024-08-20", 38],
            ["2024-08-27", 37],
            ["2024-09-03", 39],
            ["2024-09-10", 28],
            ["2024-09-17", 37],
            ["2024-09-24", 42],
            ["2024-10-01", 29],
            ["2024-10-08", 49],
            ["2024-10-14", 72],
        ],
        "DLAI": [
            ["2024-07-23", 74],
            ["2024-07-30", 74],
            ["2024-08-06", 66],
            ["2024-08-13", 79],
            ["2024-08-20", 74],
            ["2024-08-27", 78],
            ["2024-09-03", 72],
            ["2024-09-10", 68],
            ["2024-09-17", 68],
            ["2024-09-24", 66],
            ["2024-10-01", 48],
            ["2024-10-08", 29],
            ["2024-10-14", 30],
        ],
        "DLAW": [
            ["2024-07-23", 55],
            ["2024-07-30", 59],
            ["2024-08-06", 57],
            ["2024-08-13", 98],
            ["2024-08-20", 100],
            ["2024-08-27", 100],
            ["2024-09-03", 91],
            ["2024-09-10", 91],
            ["2024-09-17", 87],
            ["2024-09-24", 87],
            ["2024-10-01", 78],
            ["2024-10-08", 84],
            ["2024-10-14", 73],
        ],
        "Overall": [
            ["2024-07-23", 69],
            ["2024-07-30", 64],
            ["2024-08-06", 57],
            ["2024-08-13", 73],
            ["2024-08-20", 68],
            ["2024-08-27", 71],
            ["2024-09-03", 67],
            ["2024-09-10", 59],
            ["2024-09-17", 60],
            ["2024-09-24", 61],
            ["2024-10-01", 45],
            ["2024-10-08", 38],
            ["2024-10-14", 43],
        ],
    },
    "start_date": "2024-07-22",
}

fake_quality_report_earlier = {
    "scores": {
        "DLAA": [
            ["2024-06-18", 49],
            ["2024-06-25", 66],
            ["2024-07-02", 63],
            ["2024-07-09", 60],
            ["2024-07-16", 27],
        ],
        "DLAI": [
            ["2024-06-18", 65],
            ["2024-06-25", 63],
            ["2024-07-02", 78],
            ["2024-07-09", 71],
            ["2024-07-16", 74],
        ],
        "DLAW": [
            ["2024-06-18", 30],
            ["2024-06-25", 30],
            ["2024-07-02", 85],
            ["2024-07-09", 34],
            ["2024-07-16", 57],
        ],
        "Overall": [
            ["2024-06-18", 61],
            ["2024-06-25", 63],
            ["2024-07-02", 76],
            ["2024-07-09", 65],
            ["2024-07-16", 61],
        ],
    },
    "start_date": "2024-06-17",
}


def mock_get_latest_serialized_quality_report(area, end_date):
    if area == mock_area_name and end_date == "2024-10-14":
        return json.dumps(fake_quality_report)
    if area == mock_area_name and end_date == "2024-07-22":
        return json.dumps(fake_quality_report_earlier)

    raise Exception("Not implemented area and end_date combination for testing")


class TestQualityReportManager(unittest.TestCase):
    @patch("jeeves.manager.quality_report_manager.JIRA_FEATURES", {mock_area_name: {}})
    def test_get_area_quality_overviews(self):
        past_scores = {QUALITY_REPORT_OVERALL_KEY: [("2020-03-14", 45), ("2020-04-18", 48)]}
        mock_quality_report_dal.get_past_quality_scores.return_value = past_scores
        result = quality_report_manager.get_area_quality_overviews("Growth")
        expected = []
        self.assertEqual(result, expected)

    @patch("jeeves.manager.quality_report_manager.send_email")
    def test_save_report_data(self, mock_send_email):
        area_report = QualityReportArea.__new__(QualityReportArea)
        non_area_report = MagicMock()
        mock_reports = [non_area_report, area_report]
        quality_report_manager.save_report_data(mock_reports, datetime(2022, 3, 6))
        mock_send_email.assert_has_calls([call(non_area_report), call(area_report)])

    def test_get_quality_scores_single_file(self):
        """Tests the base case where the quality report is stored in a single file"""
        # Arrange
        start_date = str_to_date("2024-07-23")
        end_date = str_to_date("2024-10-14")
        mock_quality_report_dal.get_latest_serialized_quality_report.side_effect = (
            mock_get_latest_serialized_quality_report
        )

        # Act
        scores = quality_report_manager.get_quality_scores(mock_area_name, start_date, end_date)

        # Assert
        self.assertEqual(scores["scores"], fake_quality_report["scores"])

    def test_get_quality_scores_single_file_cropped(self):
        """Tests the case where the quality report is stored in a single file but the requested date range is a section of the file"""
        # Arrange
        start_date = str_to_date("2024-09-30")
        end_date = str_to_date("2024-10-14")
        mock_quality_report_dal.get_latest_serialized_quality_report.side_effect = (
            mock_get_latest_serialized_quality_report
        )
        expected_scores = {
            "scores": {
                "DLAA": [
                    ["2024-10-01", 29],
                    ["2024-10-08", 49],
                    ["2024-10-14", 72],
                ],
                "DLAI": [
                    ["2024-10-01", 48],
                    ["2024-10-08", 29],
                    ["2024-10-14", 30],
                ],
                "DLAW": [
                    ["2024-10-01", 78],
                    ["2024-10-08", 84],
                    ["2024-10-14", 73],
                ],
                "Overall": [
                    ["2024-10-01", 45],
                    ["2024-10-08", 38],
                    ["2024-10-14", 43],
                ],
            }
        }

        # Act
        scores = quality_report_manager.get_quality_scores(mock_area_name, start_date, end_date)

        # Assert
        self.assertEqual(scores["scores"], expected_scores["scores"])

    def test_get_quality_scores_multiple_files_cropped(self):
        """Tests the case where the quality report is stored in multiple files but the requested date range is a section of the earlier file"""
        # Arrange
        start_date = str_to_date("2024-07-02")
        end_date = str_to_date("2024-10-14")
        mock_quality_report_dal.get_latest_serialized_quality_report.side_effect = (
            mock_get_latest_serialized_quality_report
        )
        expected_scores = {
            "scores": {
                "DLAA": [
                    ["2024-07-02", 63],
                    ["2024-07-09", 60],
                    ["2024-07-16", 27],
                    ["2024-07-23", 58],
                    ["2024-07-30", 34],
                    ["2024-08-06", 24],
                    ["2024-08-13", 35],
                    ["2024-08-20", 38],
                    ["2024-08-27", 37],
                    ["2024-09-03", 39],
                    ["2024-09-10", 28],
                    ["2024-09-17", 37],
                    ["2024-09-24", 42],
                    ["2024-10-01", 29],
                    ["2024-10-08", 49],
                    ["2024-10-14", 72],
                ],
                "DLAI": [
                    ["2024-07-02", 78],
                    ["2024-07-09", 71],
                    ["2024-07-16", 74],
                    ["2024-07-23", 74],
                    ["2024-07-30", 74],
                    ["2024-08-06", 66],
                    ["2024-08-13", 79],
                    ["2024-08-20", 74],
                    ["2024-08-27", 78],
                    ["2024-09-03", 72],
                    ["2024-09-10", 68],
                    ["2024-09-17", 68],
                    ["2024-09-24", 66],
                    ["2024-10-01", 48],
                    ["2024-10-08", 29],
                    ["2024-10-14", 30],
                ],
                "DLAW": [
                    ["2024-07-02", 85],
                    ["2024-07-09", 34],
                    ["2024-07-16", 57],
                    ["2024-07-23", 55],
                    ["2024-07-30", 59],
                    ["2024-08-06", 57],
                    ["2024-08-13", 98],
                    ["2024-08-20", 100],
                    ["2024-08-27", 100],
                    ["2024-09-03", 91],
                    ["2024-09-10", 91],
                    ["2024-09-17", 87],
                    ["2024-09-24", 87],
                    ["2024-10-01", 78],
                    ["2024-10-08", 84],
                    ["2024-10-14", 73],
                ],
                "Overall": [
                    ["2024-07-02", 76],
                    ["2024-07-09", 65],
                    ["2024-07-16", 61],
                    ["2024-07-23", 69],
                    ["2024-07-30", 64],
                    ["2024-08-06", 57],
                    ["2024-08-13", 73],
                    ["2024-08-20", 68],
                    ["2024-08-27", 71],
                    ["2024-09-03", 67],
                    ["2024-09-10", 59],
                    ["2024-09-17", 60],
                    ["2024-09-24", 61],
                    ["2024-10-01", 45],
                    ["2024-10-08", 38],
                    ["2024-10-14", 43],
                ],
            }
        }

        # Act
        scores = quality_report_manager.get_quality_scores(mock_area_name, start_date, end_date)

        # Assert
        self.assertEqual(scores["scores"], expected_scores["scores"])

    def test_get_quality_scores_large_date_range(self):
        """Tests the case where the quality report is stored in multiple files and the requested date range exceeds the first file"""
        # Arrange
        start_date = str_to_date("2021-07-02")
        end_date = str_to_date("2024-10-14")
        mock_quality_report_dal.get_latest_serialized_quality_report.side_effect = (
            mock_get_latest_serialized_quality_report
        )
        expected_scores = {
            "scores": {
                "DLAA": [
                    ["2024-06-18", 49],
                    ["2024-06-25", 66],
                    ["2024-07-02", 63],
                    ["2024-07-09", 60],
                    ["2024-07-16", 27],
                    ["2024-07-23", 58],
                    ["2024-07-30", 34],
                    ["2024-08-06", 24],
                    ["2024-08-13", 35],
                    ["2024-08-20", 38],
                    ["2024-08-27", 37],
                    ["2024-09-03", 39],
                    ["2024-09-10", 28],
                    ["2024-09-17", 37],
                    ["2024-09-24", 42],
                    ["2024-10-01", 29],
                    ["2024-10-08", 49],
                    ["2024-10-14", 72],
                ],
                "DLAI": [
                    ["2024-06-18", 65],
                    ["2024-06-25", 63],
                    ["2024-07-02", 78],
                    ["2024-07-09", 71],
                    ["2024-07-16", 74],
                    ["2024-07-23", 74],
                    ["2024-07-30", 74],
                    ["2024-08-06", 66],
                    ["2024-08-13", 79],
                    ["2024-08-20", 74],
                    ["2024-08-27", 78],
                    ["2024-09-03", 72],
                    ["2024-09-10", 68],
                    ["2024-09-17", 68],
                    ["2024-09-24", 66],
                    ["2024-10-01", 48],
                    ["2024-10-08", 29],
                    ["2024-10-14", 30],
                ],
                "DLAW": [
                    ["2024-06-18", 30],
                    ["2024-06-25", 30],
                    ["2024-07-02", 85],
                    ["2024-07-09", 34],
                    ["2024-07-16", 57],
                    ["2024-07-23", 55],
                    ["2024-07-30", 59],
                    ["2024-08-06", 57],
                    ["2024-08-13", 98],
                    ["2024-08-20", 100],
                    ["2024-08-27", 100],
                    ["2024-09-03", 91],
                    ["2024-09-10", 91],
                    ["2024-09-17", 87],
                    ["2024-09-24", 87],
                    ["2024-10-01", 78],
                    ["2024-10-08", 84],
                    ["2024-10-14", 73],
                ],
                "Overall": [
                    ["2024-06-18", 61],
                    ["2024-06-25", 63],
                    ["2024-07-02", 76],
                    ["2024-07-09", 65],
                    ["2024-07-16", 61],
                    ["2024-07-23", 69],
                    ["2024-07-30", 64],
                    ["2024-08-06", 57],
                    ["2024-08-13", 73],
                    ["2024-08-20", 68],
                    ["2024-08-27", 71],
                    ["2024-09-03", 67],
                    ["2024-09-10", 59],
                    ["2024-09-17", 60],
                    ["2024-09-24", 61],
                    ["2024-10-01", 45],
                    ["2024-10-08", 38],
                    ["2024-10-14", 43],
                ],
            }
        }

        # Act
        scores = quality_report_manager.get_quality_scores(mock_area_name, start_date, end_date)

        # Assert
        self.assertEqual(scores["scores"], expected_scores["scores"])

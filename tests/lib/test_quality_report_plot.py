import unittest
from datetime import datetime
from unittest.mock import MagicMock

from jeeves.lib.quality_report_plot import get_plot_date_range


class TestQualityReportPlot(unittest.TestCase):
    def test_get_plot_date_range_weekly(self):
        """
        2023-01-01 is a Sunday,
            the plot should start on the Saturday 3 weeks before: 2022-12-10
            the plot should end on the Tuesday after the monday before: 2022-12-27
        """
        report = MagicMock()
        report.end_date = datetime(2023, 1, 1)
        result = get_plot_date_range(report)
        expected = (datetime(2022, 12, 10), datetime(2022, 12, 27))
        self.assertEqual(result, expected)

    def test_get_plot_date_range_weekly_monday(self):
        """
        2023-01-02 is a Monday,
            the plot should start on the Saturday 3 weeks before: 2022-12-10
            the plot should end on the Tuesday after the monday before: 2023-01-03
        """
        report = MagicMock()
        report.end_date = datetime(2023, 1, 2)
        result = get_plot_date_range(report)
        expected = (datetime(2022, 12, 10), datetime(2023, 1, 3))
        self.assertEqual(result, expected)

    def test_get_plot_date_range_monthly(self):
        """
        2023-01-01 is a Sunday,
            the plot should start on the 26th of 4 months before: 2022-09-26
            the plot should end on the end of the current month: 2023-01-31
        """
        report = MagicMock()
        report.end_date = datetime(2023, 1, 1)
        result = get_plot_date_range(report, "monthly")
        expected = (datetime(2022, 9, 26), datetime(2023, 1, 31))
        print("result", result)
        self.assertEqual(result, expected)

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from jeeves.model.quality_report_project_section import QualityReportProjectSection
from tests.testutil.test_util_quality_report import (
    REPORT_ISSUE_1,
    REPORT_ISSUE_2,
    REPORT_ISSUE_3,
    REPORT_ISSUE_8,
    REPORT_ISSUE_9,
)


class TestQualityReportProjectSection(unittest.TestCase):
    @classmethod
    @patch(
        "jeeves.model.quality_report_project_section.create_plot",
        MagicMock(return_value=("plot", "external_path")),
    )
    def setUpClass(cls):
        jira_issues = [
            REPORT_ISSUE_1,
            REPORT_ISSUE_2,
            REPORT_ISSUE_3,
            REPORT_ISSUE_8,
            REPORT_ISSUE_9,
        ]
        key_to_issue = {issue.issue_key: issue for issue in jira_issues}
        score_history = [("2000-01-01", 50)]
        cls.report = QualityReportProjectSection(
            datetime(2022, 1, 1),
            "DLAI",
            ["Onboarding"],
            jira_issues,
            key_to_issue,
            score_history,
            datetime(2021, 10, 1),
            "China",
        )

    def test_project_filtering(self):
        expected = [REPORT_ISSUE_1, REPORT_ISSUE_2, REPORT_ISSUE_3]
        self.assertEqual(self.report.issues, expected)

    def test_calculate_screen_count(self):
        expected = [("VCActivity", 2), ("VCScreenName", 1)]
        self.assertEqual(self.report.calculate_screen_count(), expected)

    @patch(
        "jeeves.model.quality_report_project_section.create_plot",
        MagicMock(return_value=("plot", "external_path")),
    )
    def test_android_screen_count(self):
        jira_issues = [
            REPORT_ISSUE_1,
            REPORT_ISSUE_2,
            REPORT_ISSUE_3,
            REPORT_ISSUE_8,
            REPORT_ISSUE_9,
        ]
        key_to_issue = {issue.issue_key: issue for issue in jira_issues}
        score_history = [("2000-01-01", 50)]
        report = QualityReportProjectSection(
            datetime(2022, 1, 1),
            "DLAA",
            ["Onboarding"],
            jira_issues,
            key_to_issue,
            score_history,
            datetime(2021, 10, 1),
            "China",
        )
        expected = [("screen_name", 1)]
        self.assertEqual(report.calculate_screen_count(), expected)

    @patch(
        "jeeves.model.quality_report_project_section.create_plot",
        MagicMock(return_value=("plot", "external_path")),
    )
    def test_web_screen_count(self):
        jira_issues = [
            REPORT_ISSUE_1,
            REPORT_ISSUE_2,
            REPORT_ISSUE_3,
            REPORT_ISSUE_8,
            REPORT_ISSUE_9,
        ]
        key_to_issue = {issue.issue_key: issue for issue in jira_issues}
        score_history = [("2000-01-01", 50)]
        report = QualityReportProjectSection(
            datetime(2022, 1, 1),
            "DLAW",
            ["Onboarding"],
            jira_issues,
            key_to_issue,
            score_history,
            datetime(2021, 10, 1),
            "China",
        )
        expected = [("/learn", 1)]
        self.assertEqual(report.calculate_screen_count(), expected)

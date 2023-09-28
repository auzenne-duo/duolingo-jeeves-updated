import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytz

from jeeves.model.quality_report import QualityReportIssueDataset, QualityReportTeam, RecentChanges
from jeeves.util.quality_report_util import QUALITY_REPORT_OVERALL_KEY
from tests.testutil.test_util_quality_report import (
    REPORT_ISSUE_1,
    REPORT_ISSUE_2,
    REPORT_ISSUE_2_OPEN,
    REPORT_ISSUE_10,
)

mock_score_history = {QUALITY_REPORT_OVERALL_KEY: [], "DLAA": [], "DLAI": [], "DLAW": []}


class TestQualityReport(unittest.TestCase):
    @classmethod
    @patch("jeeves.model.quality_report.create_plot", MagicMock(return_value=("file", "external")))
    @patch(
        "jeeves.model.quality_report_project_section.create_plot",
        MagicMock(return_value=("file", "external")),
    )
    @patch("jeeves.model.quality_report.open", MagicMock())
    @patch("jeeves.model.quality_report.upload_to_public_static", MagicMock())
    def setUpClass(cls):
        issues = [REPORT_ISSUE_1, REPORT_ISSUE_2]
        cls.report = QualityReportTeam(
            datetime(2022, 1, 1, tzinfo=pytz.utc),
            issues,
            past_issue_datasets=[],
            project_to_scores=mock_score_history,
            start_date=datetime(2022, 1, 1, tzinfo=pytz.utc),
            team="Onboarding",
            area="Growth",
        )

    def test_find_issues_with_closed_parents(self):
        result = self.report.find_issues_with_closed_parents()
        expected = [REPORT_ISSUE_1]
        self.assertEqual(result, expected)

    def test_find_recent_changes(self):
        """
        old: 1 High open, 1 Low open
        old score: (0/105) = 0

        Resolved: 1 High open to 1 High closed
        score with newly resolved issue: (10/(15)) = 0.6666666666666666
        change in score due to newly resolved issues: 0.6666666666666666 - 0 = 0.6666666666666666

        Added: 1 Medium open
        score with newly included issue: (10/25) = 0.4
        change in score due to newly included issues: 0.4 - 0.666666 = -0.2666666666666667

        Removed: 1 Low open
        score with newly removed issue: (10/20) = 0.5
        change in score due to newly removed issues: 0.5 - 0.4 = 0.1
        """

        issue_data = [
            QualityReportIssueDataset(
                datetime(2021, 1, 1, tzinfo=pytz.utc),
                "Onboarding",
                [REPORT_ISSUE_2_OPEN, REPORT_ISSUE_10],
                [],
                [],
            )
        ]
        result = self.report.find_recent_changes(issue_data)
        expected = RecentChanges(
            change_due_to_included_issues=-26.66666666666667,
            change_due_to_removed_issues=10.0,
            change_due_to_resolved_issues=66.66666666666667,
            newly_included_issues={"DLAI-2001"},
            newly_removed_issues={"DLAI-2010"},
            newly_resolved_issues={"DLAI-2002"},
            previous_report_date_string="2021-01-01",
        )
        self.assertEqual(result, expected)

    def test_find_recent_changes_new_included_issue(self):
        """
        old: 1 High closed
        old score: (10/10) = 1

        Added: 1 Medium open
        score with newly included issue: (10/20) = 0.5
        change in score due to newly included issues: 0.5 - 1 = -0.5
        """
        issue_data = [
            QualityReportIssueDataset(
                datetime(2021, 1, 1, tzinfo=pytz.utc), "Onboarding", [REPORT_ISSUE_2], [], []
            )
        ]
        result = self.report.find_recent_changes(issue_data)
        expected = RecentChanges(
            change_due_to_included_issues=-50.0,
            change_due_to_removed_issues=0.0,
            change_due_to_resolved_issues=0.0,
            newly_included_issues={"DLAI-2001"},
            newly_removed_issues=set(),
            newly_resolved_issues=set(),
            previous_report_date_string="2021-01-01",
        )
        self.assertEqual(result, expected)

    def test_jeeves_link(self):
        result = self.report.jeeves_link
        expected = "https://jeeves.duolingo.com/en/quality-report?area=Growth&team=Onboarding"
        self.assertEqual(result, expected)

        issues = [REPORT_ISSUE_1, REPORT_ISSUE_2]
        test_report = QualityReportTeam(
            datetime(2022, 1, 1, tzinfo=pytz.utc),
            issues,
            past_issue_datasets=[],
            project_to_scores=mock_score_history,
            start_date=datetime(2022, 1, 1, tzinfo=pytz.utc),
            team="Personalized Sessions",
            area="Learning R&D",
        )
        result = test_report.jeeves_link
        expected = "https://jeeves.duolingo.com/en/quality-report?area=Learning%20R%26D&team=Personalized%20Sessions"
        self.assertEqual(result, expected)

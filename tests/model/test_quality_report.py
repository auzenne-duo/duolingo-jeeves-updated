import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
import pytz

from jeeves.model.quality_report import QualityReportIssueDataset, QualityReportTeam, RecentChanges
from jeeves.util.quality_report_util import QUALITY_REPORT_OVERALL_KEY
from tests.testutil.test_util_quality_report import (
    REPORT_ISSUE_1,
    REPORT_ISSUE_2,
    REPORT_ISSUE_2_OPEN,
    REPORT_ISSUE_10,
)

mock_score_history = {
    QUALITY_REPORT_OVERALL_KEY: [],
    "DLAA": [],
    "DLAI": [],
    "DLAW": [],
    "VCCF": [],
    "VCBF": [],
    "EXAI": [],
    "VCS": [],
    "VCG": [],
}


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
            team="Re-Onboarding",
            area="International Growth",
            pillar="Growth",
        )

    def test_find_issues_with_closed_parents(self):
        result = self.report.find_issues_with_closed_parents()
        expected = [REPORT_ISSUE_1]
        self.assertEqual(result, expected)

    def test_find_recent_changes(self):
        """
        old: 1 High (1 duplicate) open, 1 Low open
        old score: (0/105) = 0

        Resolved: 1 High open to 1 High closed (+1 duplicate)
        score with newly resolved issue: (11/(16)) = 0.6875
        change in score due to newly resolved issues: 0.6875 - 0 = 0.6875

        Added: 1 Medium open
        score with newly included issue: (11/26) = 0.4230769230769231
        change in score due to newly included issues: 0.4230769230769231 - 0.6875 = -0.2644230769230769

        Removed: 1 Low open
        score with newly removed issue: (11/21) = 0.5238095238095238
        change in score due to newly removed issues: 0.5238095238095238 - 0.4230769230769231 = 0.10073260073260076
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
            change_due_to_included_issues=pytest.approx(-26.442307692307693),
            change_due_to_removed_issues=pytest.approx(10.073260073260073),
            change_due_to_resolved_issues=pytest.approx(68.75),
            newly_included_issues={"DLAI-2001"},
            newly_removed_issues={"DLAI-2010"},
            newly_resolved_issues={"DLAI-2002"},
            previous_report_date_string="2021-01-01",
        )
        self.assertEqual(result, expected)

    def test_find_recent_changes_new_included_issue(self):
        """
        old: 1 High closed (1 duplicate)
        old score: (11/11) = 1

        Added: 1 Medium open
        score with newly included issue: (11/21) = 0.5238095238095238
        change in score due to newly included issues: 0.5238095238095238 - 1 = -0.47619047619047616
        """
        issue_data = [
            QualityReportIssueDataset(
                datetime(2021, 1, 1, tzinfo=pytz.utc), "Onboarding", [REPORT_ISSUE_2], [], []
            )
        ]
        result = self.report.find_recent_changes(issue_data)
        expected = RecentChanges(
            change_due_to_included_issues=pytest.approx(-47.61904761904762),
            change_due_to_removed_issues=pytest.approx(0.0),
            change_due_to_resolved_issues=pytest.approx(0.0),
            newly_included_issues={"DLAI-2001"},
            newly_removed_issues=set(),
            newly_resolved_issues=set(),
            previous_report_date_string="2021-01-01",
        )
        self.assertEqual(result, expected)

    @patch("jeeves.model.quality_report.upload_to_public_static", MagicMock())
    def test_jeeves_link(self):
        result = self.report.jeeves_link
        expected = "https://jeeves.duolingo.com/en/quality-report?pillar=Growth&area=International%20Growth&team=Re-Onboarding"
        self.assertEqual(result, expected)

        issues = [REPORT_ISSUE_1, REPORT_ISSUE_2]
        test_report = QualityReportTeam(
            datetime(2022, 1, 1, tzinfo=pytz.utc),
            issues,
            past_issue_datasets=[],
            project_to_scores=mock_score_history,
            start_date=datetime(2022, 1, 1, tzinfo=pytz.utc),
            team="Intermediate English",
            area="Learning Experience",
            pillar="Language Learning",
        )
        result = test_report.jeeves_link
        expected = "https://jeeves.duolingo.com/en/quality-report?pillar=Language%20Learning&area=Learning%20Experience&team=Intermediate%20English"
        self.assertEqual(result, expected)

    def test_serialize_recent_changes(self):
        mock_recent_changes = RecentChanges(
            change_due_to_included_issues=1,
            change_due_to_removed_issues=18,
            change_due_to_resolved_issues=2022,
            newly_included_issues=["DLAI-997", "DLAI-998", "DLAI-999"],
            newly_removed_issues=["DLAI-1000", "DLAI-1001", "DLAI-1002", "DLAI-1003"],
            newly_resolved_issues=["DLAI-123", "DLAI-456"],
            previous_report_date_string="2024-05-01",
        )

        result = mock_recent_changes.serialize()

        expected = {
            "previous_report_date_string": "2024-05-01",
            "change_due_to_added_issues": 1,
            "change_due_to_resolved_issues": 2022,
            "resolved_issue_count": 2,
            "added_issue_count": 3,
            "added_issue_link": "https://duolingo.atlassian.net/issues/?jql=Key+in+%28DLAI-997%2C+DLAI-998%2C+DLAI-999%29",
            "resolved_issue_link": "https://duolingo.atlassian.net/issues/?jql=Key+in+%28DLAI-123%2C+DLAI-456%29",
        }

        self.assertEqual(result, expected)

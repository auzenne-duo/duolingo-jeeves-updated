import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from jeeves.model.quality_report import QualityReportTeam, RecentChanges
from tests.testutil.test_util_quality_report import REPORT_ISSUE_1, REPORT_ISSUE_2

mock_score_history = (
    '{"title":"Test", "score_history":{"Overall":[], "DLAA":[], "DLAI":[], "DLAW":[]}}'
)


def mock_s3(filepath):
    if "issue_data" in filepath:
        return '[{"title":"Test", "issue_data":[], "date":"2022-01-01"}]'
    return mock_score_history


class TestQualityReport(unittest.TestCase):
    @classmethod
    @patch("jeeves.model.quality_report.upload_to_jeeves_s3", MagicMock())
    @patch(
        "jeeves.model.quality_report.get_s3_client_and_bucket",
        MagicMock(
            return_value=(
                MagicMock(download=MagicMock(side_effect=mock_s3)),
                MagicMock(),
            )
        ),
    )
    @patch("jeeves.model.quality_report.create_plot", MagicMock(return_value=("file", "external")))
    @patch(
        "jeeves.model.quality_report_project_section.create_plot",
        MagicMock(return_value=("file", "external")),
    )
    @patch("jeeves.model.quality_report.open", MagicMock())
    @patch("jeeves.model.quality_report.upload_to_public_static", MagicMock())
    def setUpClass(cls):
        issues = [REPORT_ISSUE_1, REPORT_ISSUE_2]
        key_to_issue = {issue.issue_key: issue for issue in issues}
        cls.report = QualityReportTeam(
            datetime(2022, 1, 1),
            issues,
            key_to_issue,
            datetime(2022, 1, 1),
            "Onboarding",
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
            {
                "date": "2021-01-01",
                "issues": {
                    "DLAI-2003": {
                        "is_done": False,
                        "creation_date": "2021-01-01",
                        "is_fixed": False,
                        "score_params": {
                            "is_done": False,
                            "priority": "High",
                            "score": 5,
                            "group": "LOW_LOWEST",
                            "resolution": "OPEN",
                            "time_to_fix": "NOT_WITHIN_ONE_WEEK",
                        },
                        "fixed_within_one_week": False,
                    },
                    "DLAI-2002": {
                        "is_done": False,
                        "creation_date": "2021-01-01",
                        "is_fixed": False,
                        "score_params": {
                            "is_done": False,
                            "priority": "High",
                            "score": 100,
                            "group": "HIGH_HIGHEST",
                            "resolution": "OPEN",
                            "time_to_fix": "NOT_WITHIN_ONE_WEEK",
                        },
                        "fixed_within_one_week": False,
                    },
                },
            },
            {"date": "2022-01-06", "issues": {}},
        ]
        result = self.report.find_recent_changes(issue_data)
        expected = RecentChanges(
            change_due_to_included_issues=-26.66666666666667,
            change_due_to_removed_issues=10.0,
            change_due_to_resolved_issues=66.66666666666667,
            newly_included_issues={"DLAI-2001"},
            newly_removed_issues={"DLAI-2003"},
            newly_resolved_issues={"DLAI-2002"},
            previous_report_date="2021-01-01",
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
            {
                "date": "2021-01-01",
                "issues": {
                    "DLAI-2002": {
                        "is_done": True,
                        "creation_date": "2021-01-01",
                        "is_fixed": False,
                        "score_params": {
                            "is_done": True,
                            "priority": "High",
                            "score": 10,
                            "group": "HIGH_HIGHEST",
                            "resolution": "CLOSED_UNFIXED",
                            "time_to_fix": "NOT_WITHIN_ONE_WEEK",
                        },
                        "fixed_within_one_week": False,
                        "resolution_date": "2021-01-02",
                    }
                },
            },
            {"date": "2022-01-06", "issues": {}},
        ]
        result = self.report.find_recent_changes(issue_data)
        expected = RecentChanges(
            change_due_to_included_issues=-50.0,
            change_due_to_removed_issues=0.0,
            change_due_to_resolved_issues=0.0,
            newly_included_issues={"DLAI-2001"},
            newly_removed_issues=set(),
            newly_resolved_issues=set(),
            previous_report_date="2021-01-01",
        )
        self.assertEqual(result, expected)

import unittest
from datetime import date, datetime

from jeeves.model.quality_report_base import _QUOTE_ESCAPE_CHAR, QualityReportBase, ScoreTypeCount

# from jeeves.model.quality_score_params import QualityScoreParams
from tests.testutil.test_util_quality_report import (
    REPORT_ISSUE_1,
    REPORT_ISSUE_2,
    REPORT_ISSUE_3,
    REPORT_ISSUE_4,
    REPORT_ISSUE_5,
    REPORT_ISSUE_6,
)


class TestQualityReportBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        issues = [REPORT_ISSUE_1, REPORT_ISSUE_2, REPORT_ISSUE_3]
        cls.report = QualityReportBase(
            datetime(2022, 1, 1), None, issues, None, datetime(2021, 10, 1), ""
        )

    def test_calculate_scores(self):
        # 1 open medium priority bugs, 1 open high priority bug, 1 closed high priority bug, 1 fixed within 1 week high priority bug, 1 fixed after 1 week medium priority bug
        self.report.issues = [
            REPORT_ISSUE_1,
            REPORT_ISSUE_2,
            REPORT_ISSUE_3,
            REPORT_ISSUE_4,
            REPORT_ISSUE_5,
            REPORT_ISSUE_6,
        ]
        score_breakdown = self.report.calculate_scores(self.report.issues)
        self.assertEqual(score_breakdown.open_points, 110)  # Medium: 10 + High: 100
        self.assertEqual(
            score_breakdown.closed_points, 130
        )  # Medium fixed: 10*2 + High fixed within one week: 100 + high close: 10
        self.assertEqual(score_breakdown.overall_score, int(100 * 130 / 240))

        expected_quality_score_type_counts = [
            ScoreTypeCount(count=1, points=100, label="High Open"),
            ScoreTypeCount(count=1, points=100, label="High Fixed within one week"),
            ScoreTypeCount(count=1, points=10, label="High Closed"),
            ScoreTypeCount(count=1, points=10, label="Medium Open"),
            ScoreTypeCount(count=2, points=10, label="Medium Fixed"),
        ]
        self.assertEqual(
            score_breakdown.quality_score_type_counts, expected_quality_score_type_counts
        )

    def test_create_open_issues_link(self):
        self.report.features = None
        self.report.project = None
        result = self.report.create_open_issues_link()
        expected = "https://duolingo.atlassian.net/issues/?jql=resolution = Unresolved AND issueType = Bug AND updated >= 2021-10-01 ORDER BY updated DESC"
        self.assertEqual(result, expected)

        self.report.project = "DLAA"
        result = self.report.create_open_issues_link()
        expected = "https://duolingo.atlassian.net/issues/?jql=resolution = Unresolved AND issueType = Bug AND updated >= 2021-10-01 AND project=DLAA ORDER BY updated DESC"
        self.assertEqual(result, expected)

        self.report.features = {"WeChat"}
        result = self.report.create_open_issues_link()
        expected = f"https://duolingo.atlassian.net/issues/?jql=resolution = Unresolved AND issueType = Bug AND updated >= 2021-10-01 AND project=DLAA AND Feature[Dropdown] in ({_QUOTE_ESCAPE_CHAR}WeChat{_QUOTE_ESCAPE_CHAR}) ORDER BY updated DESC"
        self.assertEqual(result, expected)

    def test_calculate_monthly_scores(self):
        project_to_scores = {
            "DLAA": [
                ("2000-01-01", 50),
                ("2000-01-03", 100),
                ("2000-02-02", 65),
                ("2000-03-04", 50),
            ]
        }
        monthly_scores = self.report.calculate_aggregate_scores(project_to_scores)
        self.assertEqual(
            monthly_scores,
            {
                "DLAA": [
                    (date(2000, 1, 1), 75.0),
                    (date(2000, 2, 1), 65.0),
                    (date(2000, 3, 1), 50.0),
                ]
            },
        )

    def test_calculate_max_priority_issues(self):
        result = self.report.calculate_max_priority_issues([REPORT_ISSUE_1, REPORT_ISSUE_3])
        expected = [REPORT_ISSUE_3, REPORT_ISSUE_1]
        self.assertEqual(result, expected)

    def test_calculate_max_dupes_issues(self):
        result = self.report.calculate_max_dupes_issues([REPORT_ISSUE_1, REPORT_ISSUE_3])
        expected = [REPORT_ISSUE_1]
        self.assertEqual(result, expected)

import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from jeeves.model.quality_report import (
    _QUOTE_ESCAPE_CHAR,
    IssueStatus,
    QualityReportBase,
    QualityReportProjectSection,
    QualityReportTeam,
)
from jeeves.util.quality_report_priority import get_quality_report_priority
from tests.scripts.test_quality_report_script import create_jira_doc

JIRA_DOCUMENT_1 = create_jira_doc(
    "DLAI-2001", "Onboarding", "To Do", "Medium", ["DLAI-2002", "DLAI-2003"]
)
JIRA_DOCUMENT_1.is_done = False

JIRA_DOCUMENT_2 = create_jira_doc(
    "DLAI-2002", "Onboarding", "Done", "High", ["DLAI-2001"], labels=["parent_bug"]
)
JIRA_DOCUMENT_2.is_done = True

JIRA_DOCUMENT_3 = create_jira_doc("DLAI-2003", "Onboarding", "In Development", "High", [])
JIRA_DOCUMENT_3.is_done = False


class TestQualityReportBase(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        jira_issues = [JIRA_DOCUMENT_1, JIRA_DOCUMENT_2, JIRA_DOCUMENT_3]
        key_to_issue = {issue.issue_key: issue for issue in jira_issues}
        cls.report = QualityReportBase(
            datetime(2022, 1, 1), None, None, jira_issues, key_to_issue, ""
        )

    def test_create_status_priority_count(self):
        self.report.create_status_priority_count()
        expected = {
            IssueStatus.OPEN: {
                get_quality_report_priority("Medium"): 1,
                get_quality_report_priority("High"): 1,
            },
            IssueStatus.CLOSED: {get_quality_report_priority("High"): 1},
        }
        self.assertEqual(self.report.status_priority_count, expected)

    def test_calculate_scores(self):
        self.report.status_priority_count = {
            IssueStatus.OPEN: {get_quality_report_priority("High"): 1},
            IssueStatus.CLOSED: {
                get_quality_report_priority("Medium"): 5,
                get_quality_report_priority("High"): 2,
            },
        }
        self.report.calculate_scores()
        self.assertEqual(self.report.overall_score, 75)
        self.assertEqual(self.report.closed_score, 30)
        self.assertEqual(self.report.open_score, 10)

    def test_create_open_issues_link(self):
        self.report.features = None
        self.report.project = None
        self.report.create_open_issues_link()
        expected = "https://duolingo.atlassian.net/issues/?jql=status in (%22Confirmed%22, %22Considering%22, %22In Design%22, %22In Development%22, %22In Progress%22, %22In Code Review%22, %22In Review%22, %22In Testing%22, %22Ready for Design%22, %22To Do%22, %22Unconfirmed%22) ORDER BY updated DESC"
        self.assertEqual(self.report.open_issues_link, expected)

        self.report.project = "DLAA"
        self.report.create_open_issues_link()
        expected = "https://duolingo.atlassian.net/issues/?jql=status in (%22Confirmed%22, %22Considering%22, %22In Design%22, %22In Development%22, %22In Progress%22, %22In Code Review%22, %22In Review%22, %22In Testing%22, %22Ready for Design%22, %22To Do%22, %22Unconfirmed%22) AND project=DLAA ORDER BY updated DESC"
        self.assertEqual(self.report.open_issues_link, expected)

        self.report.features = {"WeChat"}
        self.report.create_open_issues_link()
        expected = f"https://duolingo.atlassian.net/issues/?jql=status in (%22Confirmed%22, %22Considering%22, %22In Design%22, %22In Development%22, %22In Progress%22, %22In Code Review%22, %22In Review%22, %22In Testing%22, %22Ready for Design%22, %22To Do%22, %22Unconfirmed%22) AND project=DLAA AND Feature[Dropdown] in ({_QUOTE_ESCAPE_CHAR}WeChat{_QUOTE_ESCAPE_CHAR}) ORDER BY updated DESC"
        self.assertEqual(self.report.open_issues_link, expected)


class TestQualityReportProjectSection(unittest.TestCase):
    @classmethod
    @patch("jeeves.model.quality_report.plt.savefig", MagicMock())
    def setUpClass(cls):
        jira_issues = [JIRA_DOCUMENT_1, JIRA_DOCUMENT_2, JIRA_DOCUMENT_3]
        key_to_issue = {issue.issue_key: issue for issue in jira_issues}
        score_history = [("2000-01-01", 50)]
        cls.report = QualityReportProjectSection(
            datetime(2022, 1, 1),
            "DLAI",
            ["Onboarding"],
            jira_issues,
            key_to_issue,
            score_history,
            "China",
        )

    def test_calculate_max_priority_issues(self):
        result = self.report.calculate_max_priority_issues()
        expected = [JIRA_DOCUMENT_3, JIRA_DOCUMENT_1]
        self.assertEqual(result, expected)

    def test_calculate_max_dupes_issues(self):
        result = self.report.calculate_max_dupes_issues()
        expected = [JIRA_DOCUMENT_1]
        self.assertEqual(result, expected)


mock_score_history = (
    '{"title":"Test", "score_history":{"Overall":[], "DLAA":[], "DLAI":[], "DLAW":[]}}'
)


class TestQualityReport(unittest.TestCase):
    @classmethod
    @patch("jeeves.model.quality_report.plt.savefig", MagicMock())
    @patch("jeeves.model.quality_report.upload_to_s3", MagicMock())
    @patch(
        "jeeves.model.quality_report.get_s3_client_and_bucket",
        MagicMock(
            return_value=(
                MagicMock(download=MagicMock(return_value=mock_score_history)),
                MagicMock(),
            )
        ),
    )
    def setUpClass(cls):
        jira_issues = [JIRA_DOCUMENT_1, JIRA_DOCUMENT_2]
        key_to_issue = {issue.issue_key: issue for issue in jira_issues}
        cls.report = QualityReportTeam(
            datetime(2022, 1, 1),
            jira_issues,
            key_to_issue,
            datetime(2022, 1, 1),
            "Onboarding",
        )

    def test_find_issues_with_closed_parents(self):
        result = self.report.find_issues_with_closed_parents()
        expected = [JIRA_DOCUMENT_1]
        self.assertEqual(result, expected)

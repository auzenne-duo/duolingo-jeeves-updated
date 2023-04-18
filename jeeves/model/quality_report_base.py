from collections import Counter, defaultdict
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from jeeves.config.config import JIRA_ISSUE_TYPE_BUG
from jeeves.model.issue_score_parameters import IssueScoreParameters
from jeeves.model.quality_report_issue import QualityReportIssue
from jeeves.util.date_util import date_to_str, str_to_date

_CLOSED_STATUS = "Closed"
# The maximum number of issues shown per "worst issues" category
_MAX_NUMBER_WORST_ISSUES = 5
_OPEN_STATUS = "Open"
_QUOTE_ESCAPE_CHAR = "%22"


class ScoreBreakdown:
    """
    Class for keeping track of quality score breakdown stats.

    Attributes:
        score_params_count: A dictionary mapping score params to the number of issues with that score params.
        status_priority_group_count: A dictionary mapping status to a dictionary mapping priority group to a
                                     dictionary mapping issue parameters to the number of issues with those score parameters.

                                     Example: {
                                        "Closed": {
                                            "Medium": {
                                                "IssueScoreParameters("Medium", is_fixed=True, fixed_within_one_week=True)": 6,
        status_score: A dictionary mapping status to the score for that status.
    """

    def __init__(
        self,
        open_score: int,
        closed_score: int,
        score_params_count: Dict[IssueScoreParameters, int],
    ) -> None:
        self.score_params_count = score_params_count
        self.status_priority_group_count = {}
        self.status_score = {_OPEN_STATUS: open_score, _CLOSED_STATUS: closed_score}
        sorted_priorities = sorted(score_params_count.keys(), key=lambda priority: -priority.score)
        for priority in sorted_priorities:
            count = score_params_count[priority]
            status = _CLOSED_STATUS if priority.is_done else _OPEN_STATUS
            self.status_priority_group_count.setdefault(status, {})
            self.status_priority_group_count[status].setdefault(priority.group.name, {})
            self.status_priority_group_count[status][priority.group.name][priority] = count


class QualityReportBase:
    def __init__(
        self,
        end_date: datetime,
        features: Optional[List[str]],
        issues: List[QualityReportIssue],
        key_to_issue: Dict[str, QualityReportIssue],
        project: Optional[str],
        start_date: datetime,
        title: str,
    ) -> None:
        """
        Base class for calculating quality scores. Initializes quality scores and stats

        Params:
            end_date: datetime for the end of the range of bugs (inclusive)
            features: list of Jira features used for the quality report or None
            issues: list of Quality Report issues to be used in making the report
            key_to_issue: mapping of issue key to QualityReportIssue for all of issues
            project: string for project such as "DLAA" or None
            start_date: datetime for the start of the range of bugs (inclusive)
            title: string for team/area such as "China"
        """
        self.end_date = end_date
        self.start_date = start_date
        self.features = features
        self.issues = issues
        self.key_to_issue = key_to_issue
        self.project = project
        self.title = title

        (
            self.overall_score,
            self.open_score,
            self.closed_score,
            self.score_breakdown,
        ) = self.calculate_scores(self.issues)
        self.open_issues = [issue for issue in self.issues if not issue.score_params.is_done]
        self.max_priority_issues = self.calculate_max_priority_issues(self.open_issues)
        self.max_dupes_issues = self.calculate_max_dupes_issues(self.open_issues)
        self.max_dupes_issues_no_overlap = [
            issue for issue in self.max_dupes_issues[:5] if issue not in self.max_priority_issues
        ]

        self.num_open = len(self.open_issues)
        self.num_closed = len(self.issues) - self.num_open
        self.open_issues_link = self.create_open_issues_link()

    def calculate_scores(
        self, issues: List[QualityReportIssue]
    ) -> Tuple[int, int, int, ScoreBreakdown]:
        """
        Calculates open and closed scores based on the priority score, resolution, and whether an issue was closed within
        one week

        Params:
            issues: list of QualityReportIssue documents to be used in calculating the score

        Returns:
            overall_score: the overall score for the quality report
            open_score: the score for open issues
            closed_score: the score for closed issues
            score_breakdown: a ScoreBreakdown object containing the score breakdown stats
        """
        score_params_count = Counter()
        open_score, closed_score = 0, 0
        for issue in issues:
            score_params_count[issue.score_params] += 1
            if issue.score_params.is_done:
                closed_score += issue.score_params.score
            else:
                open_score += issue.score_params.score

        if open_score + closed_score == 0:
            overall_score = 100
        else:
            overall_score = round(closed_score / (open_score + closed_score) * 100)

        return (
            overall_score,
            open_score,
            closed_score,
            ScoreBreakdown(open_score, closed_score, score_params_count),
        )

    def create_open_issues_link(self) -> None:
        """Initialize a Jira link for open tickets"""

        open_issues_link = f"https://duolingo.atlassian.net/issues/?jql=resolution = Unresolved AND issueType = {JIRA_ISSUE_TYPE_BUG}"
        open_issues_link += f" AND updated >= {date_to_str(self.start_date)}"
        if self.project:
            open_issues_link += f" AND project={self.project}"
        if self.features:
            features_string = {
                ", ".join(
                    f"{_QUOTE_ESCAPE_CHAR}{feature}{_QUOTE_ESCAPE_CHAR}"
                    for feature in self.features
                )
            }
            open_issues_link += f' AND Feature[Dropdown] in ({", ".join(features_string)})'
        open_issues_link += " ORDER BY updated DESC"
        return open_issues_link

    def calculate_aggregate_scores(
        self, project_to_scores: Dict[str, List[Tuple[str, int]]], monthly: bool = True
    ) -> Dict[str, List[Tuple[str, int]]]:
        """
        Given a list of date/score tuples calculates the aggregate scores (by month or week)

        params:
            project_to_scores: mapping from project str (eg "DLAA") to a list of date strings and score tuples
            monthly: boolean for whether to aggregate by month or week

        returns: mapping from project to a list of aggregate date strings and score tuples
        """
        project_to_aggregate_scores = {}
        for project, scores in project_to_scores.items():
            # find the average score per month
            aggregate_scores = defaultdict(list)

            for date_string, score in scores:
                date = str_to_date(date_string)
                if monthly:
                    date = date.replace(day=1)
                else:  # weekly
                    date = date - timedelta(days=date.weekday())
                aggregate_scores[date].append(score)

            project_to_aggregate_scores[project] = [
                (date, round(sum(scores) / len(scores), 1))
                for date, scores in aggregate_scores.items()
            ]
        return project_to_aggregate_scores

    def calculate_max_priority_issues(
        self, open_issues: List[QualityReportIssue]
    ) -> List[QualityReportIssue]:
        """
        Return the top _MAX_NUMBER_WORST_ISSUES maximum priority issues of the open issues as a list of issues with the highest priority
        (breaking ties by created date)
        """
        open_issues.sort(key=lambda issue: issue.creation_date, reverse=True)
        open_issues.sort(key=lambda issue: issue.score_params, reverse=True)
        return open_issues[:_MAX_NUMBER_WORST_ISSUES]

    def calculate_max_dupes_issues(
        self, open_issues: List[QualityReportIssue], min_dupes: int = 2
    ) -> List[QualityReportIssue]:
        """
        Return the top _MAX_NUMBER_WORST_ISSUES issues of the open issues with the most duplicates as a list of issues
        with the highest priority (breaking ties by priority)
        """
        issues_filtered = [
            issue for issue in open_issues if len(issue.linked_duplicate_keys) >= min_dupes
        ]
        issues_filtered.sort(key=lambda issue: issue.score_params, reverse=True)
        issues_filtered.sort(key=lambda issue: -len(issue.linked_duplicate_keys))
        return issues_filtered[:_MAX_NUMBER_WORST_ISSUES]

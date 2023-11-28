import urllib.parse
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from jeeves.model.jira_document import JiraDocument
from jeeves.model.quality_score_params import (
    PRIORITY_SORTING_ORDER,
    PriorityValue,
    QualityScoreParams,
    Resolution,
)
from jeeves.util.date_util import str_to_date

# The maximum number of issues shown per "worst issues" category
_MAX_NUMBER_WORST_ISSUES = 5

# The maximum number of issues we can query for using JQL at once
_MAX_NUMBER_URL_ISSUES = 200


@dataclass
class ScoreTypeCount:
    count: int
    points: int
    label: str

    duplicate_bonus_points: Optional[int] = None


@dataclass
class ScoreBreakdown:
    closed_points: int
    date: datetime
    quality_score_type_counts: List[ScoreTypeCount]
    num_issues: int
    open_points: int
    overall_score: int


class QualityReportBase:
    def __init__(
        self,
        end_date: datetime,
        features: Optional[List[str]],
        issues: List[JiraDocument],
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
        self.key_to_issue = {issue.issue_key: issue for issue in issues}
        self.project = project
        self.title = title

        self.score_breakdown = self.calculate_scores(self.end_date, self.issues)
        self.open_issues = [
            issue for issue in self.issues if not issue.quality_score_params.is_done
        ]
        self.max_priority_issues = self.calculate_max_priority_issues(self.open_issues)
        self.max_dupes_issues = self.calculate_max_dupes_issues(self.open_issues)
        self.max_dupes_issues_no_overlap = [
            issue for issue in self.max_dupes_issues[:5] if issue not in self.max_priority_issues
        ]

        self.num_open = len(self.open_issues)
        self.num_closed = len(self.issues) - self.num_open
        self.open_issues_link = self.create_open_issues_link()

    def calculate_scores(self, date: datetime, issues: List[JiraDocument]) -> ScoreBreakdown:
        """
        Calculates open and closed scores based on the priority score, resolution, and whether an issue was closed within
        one week

        Params:
            date: the date of the snapshot being calculated
            issues: list of QualityReportIssue documents to be used in calculating the score

        Returns:
            score_breakdown: a ScoreBreakdown object containing the score breakdown stats
        """
        quality_score_params_count: Dict[Tuple[PriorityValue, Resolution], int] = Counter(
            [
                (issue.quality_score_params.group, issue.quality_score_params.resolution)
                for issue in issues
            ]
        )
        quality_score_duplicate_bonuses: Dict[Tuple[PriorityValue, Resolution], int] = defaultdict(
            int
        )

        open_points, closed_points = 0, 0
        for issue in issues:
            if issue.quality_score_params.is_done:
                closed_points += issue.quality_score_params.score
                quality_score_duplicate_bonuses[
                    (issue.quality_score_params.group, issue.quality_score_params.resolution)
                ] += issue.quality_score_params.duplicates or 0
            else:
                open_points += issue.quality_score_params.score

        if open_points + closed_points == 0:
            overall_score = 100
        else:
            overall_score = round(closed_points / (open_points + closed_points) * 100)

        # We want to have the type counts sorted by priority and then score
        score_params_types = QualityScoreParams.get_all_possible_score_params()
        score_params_types.sort(
            key=lambda score_params: (
                PRIORITY_SORTING_ORDER[score_params.group],
                -score_params.score,
            )
        )
        quality_score_type_counts = [
            ScoreTypeCount(
                quality_score_params_count[(score_params.group, score_params.resolution)],
                score_params.score,
                score_params.text,
                quality_score_duplicate_bonuses[(score_params.group, score_params.resolution)]
                if quality_score_duplicate_bonuses[(score_params.group, score_params.resolution)]
                > 0
                else None,
            )
            for score_params in score_params_types
        ]

        return ScoreBreakdown(
            closed_points,
            date,
            quality_score_type_counts,
            len(issues),
            open_points,
            overall_score,
        )

    def create_open_issues_link(self) -> None:
        """Initialize a Jira link for open tickets"""
        issue_keys = [issue.issue_key for issue in self.open_issues[:_MAX_NUMBER_URL_ISSUES]]
        return f"https://duolingo.atlassian.net/issues/?jql=Key in ({urllib.parse.quote(', '.join(issue_keys))})"

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

    def calculate_max_priority_issues(self, open_issues: List[JiraDocument]) -> List[JiraDocument]:
        """
        Return the top _MAX_NUMBER_WORST_ISSUES maximum priority issues of the open issues as a list of issues with the highest priority
        (breaking ties by created date)
        """
        open_issues.sort(key=lambda issue: issue.creation_date, reverse=True)
        open_issues.sort(key=lambda issue: issue.quality_score_params.score, reverse=True)
        return open_issues[:_MAX_NUMBER_WORST_ISSUES]

    def calculate_max_dupes_issues(
        self, open_issues: List[JiraDocument], min_dupes: int = 2
    ) -> List[JiraDocument]:
        """
        Return the top _MAX_NUMBER_WORST_ISSUES issues of the open issues with the most duplicates as a list of issues
        with the highest priority (breaking ties by priority)
        """
        issues_filtered = [
            issue for issue in open_issues if len(issue.linked_duplicate_keys) >= min_dupes
        ]
        issues_filtered.sort(key=lambda issue: issue.quality_score_params.score, reverse=True)
        issues_filtered.sort(key=lambda issue: -len(issue.linked_duplicate_keys))
        return issues_filtered[:_MAX_NUMBER_WORST_ISSUES]

from __future__ import annotations

import abc
import urllib.parse
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta
from typing import Any, List, Optional, Tuple

from jeeves.config.config import JIRA_PROJECTS
from jeeves.config.jira_features import AREA_TO_FEATURES, TEAM_TO_FEATURES
from jeeves.lib.quality_report_plot import create_plot
from jeeves.model.custom_types import JSON
from jeeves.model.jira_document import JiraDocument
from jeeves.model.quality_report_base import QualityReportBase, ScoreBreakdown
from jeeves.model.quality_report_project_section import QualityReportProjectSection
from jeeves.util.date_util import date_to_str, parse_external_datetime
from jeeves.util.quality_report_util import QUALITY_REPORT_OVERALL_KEY
from jeeves.util.s3_client_and_bucket import upload_to_public_static

_JIRA_FIELDS_TO_FILTER = ["embeddings", "experiment_conditions", "comments"]
_NUM_WEEKS_IN_PAST_SCORE_BREAKDOWN = 4
_QUALITY_REPORT_PLOTS_EXTERNAL_DIRECTORY_PREFIX = "https://public-static.duolingo.com/"
_SCORE_CUTTOFF_DAYS = 90
_DESIGN_QUALITY_LABEL = "design-quality"

# Handle the Visual Polish -> Design Quality label change
_DESIGN_QUALITY_DEPRECATED_LABEL = "visual-polish"

QualityScoreHistory = List[Tuple[str, int]]


@dataclass
class RecentChanges:
    """
    This class helps organize the data collected when checking for what has changed since the last quality report.

    We store the numeric change that occured to the quality score based on issues that were included/removed/resolved
    We also store a list of the Jira keys for issues that were included/removed/resolved
    """

    change_due_to_included_issues: float
    change_due_to_removed_issues: float
    change_due_to_resolved_issues: float
    newly_included_issues: list[str]
    newly_removed_issues: list[str]
    newly_resolved_issues: list[str]
    previous_report_date_string: str


@dataclass
class SerializedQualityReportData:
    """
    A class to store main properties of a quality report for api responses
    """

    features: list[str]
    open_bugs_url: str
    open_bugs_count: int
    overall_score: int
    previous_overall_score: Optional[int]
    score_breakdowns: list[ScoreBreakdown]
    scores: dict[str, QualityScoreHistory]
    start_date: str
    end_date: str
    max_priority_issues: list[JSON]
    max_dupes_issues: list[JSON]
    design_quality_issues: list[JSON]
    title: str


@dataclass
class SerializedQualityReportDataArea(SerializedQualityReportData):
    """
    Same as parent class but with all the area's teams' data as well
    """

    @classmethod
    def from_instance(cls, instance):
        return cls(**asdict(instance))

    teams: Optional[list[SerializedQualityReportData]] = None


@dataclass
class QualityReportIssueDataset:
    """
    A collection of the issues used in a quality report to be used to find changes between reports
    """

    date: datetime
    title: str
    issues: list[JiraDocument]
    max_priority_issue_keys: list[str]
    max_dupes_issue_keys: list[str]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> QualityReportIssueDataset:
        return QualityReportIssueDataset(
            date=parse_external_datetime(data["date"]),
            title=data["title"],
            issues=[JiraDocument.deserialize_from_internal_json(issue) for issue in data["issues"]],
            max_priority_issue_keys=data.get("max_priority_issue_keys", []),
            max_dupes_issue_keys=data.get("max_dupes_issue_keys", []),
        )

    def serialize(self) -> dict[str, Any]:
        """
        Serializes QualityReportIssueDataset

        Doesn't serialize embeddings or experiment_conditions to save space as those fields are large and not used in the quality report
        """
        return {
            "date": self.date,
            "title": self.title,
            "issues": [
                JiraDocument.serialize_to_json(issue, _JIRA_FIELDS_TO_FILTER)
                for issue in self.issues
            ],
            "max_priority_issue_keys": self.max_priority_issue_keys,
            "max_dupes_issue_keys": self.max_dupes_issue_keys,
        }


class QualityReport(QualityReportBase, metaclass=abc.ABCMeta):
    def __init__(
        self,
        end_date: datetime,
        features: Optional[set[str]],
        issues: list[JiraDocument],
        past_issue_datasets: list[QualityReportIssueDataset],
        project_to_scores: dict[str, QualityScoreHistory],
        start_date: datetime,
        title: str,
        area: str,
        monthly: bool = True,
    ) -> None:
        """
        Calculates score and properties for a quality report for a specific area or team using given issues
        Initializes a QualityReportProjectSection for each project
        Creates and uploads plots to s3

        Params:
            See parent class
            monthly: whether to calculate monthly scores or weekly
        """
        super().__init__(end_date, features, issues, None, start_date, title)
        self.area = area
        self.issue_datasets = past_issue_datasets

        # Add current scores to the history of quality scores
        self.project_to_scores = project_to_scores
        # truncate past score to the past X days
        score_cutoff_date = self.end_date - timedelta(days=_SCORE_CUTTOFF_DAYS)
        for project, score_history in self.project_to_scores.items():
            self.project_to_scores[project] = [
                (date, score)
                for (date, score) in score_history
                if parse_external_datetime(date) > score_cutoff_date
            ]
        self.project_to_scores[QUALITY_REPORT_OVERALL_KEY].append(
            (date_to_str(self.end_date), self.score_breakdown.overall_score)
        )
        self.project_sections = []
        for project in JIRA_PROJECTS:
            section = QualityReportProjectSection(
                self.end_date,
                project,
                self.features,
                self.issues,
                project_to_scores[project],
                self.start_date,
                self.title,
            )
            if section.open_issues == 0:
                continue
            self.project_sections.append(section)
            self.project_to_scores[project].append(
                (date_to_str(self.end_date), section.score_breakdown.overall_score)
            )

        # Generate plots
        self.aggregate_scores = self.calculate_aggregate_scores(
            self.project_to_scores, monthly=monthly
        )
        self.previous_overall_score = None
        if len(self.aggregate_scores[QUALITY_REPORT_OVERALL_KEY]) > 1:
            self.previous_overall_score = self.aggregate_scores[QUALITY_REPORT_OVERALL_KEY][-2][1]
        self.overall_plot_filename, self.external_overall_plot_filename = create_plot(
            self,
            self.aggregate_scores,
            QUALITY_REPORT_OVERALL_KEY,
            legend=True,
        )
        self.external_overall_plot_path = (
            _QUALITY_REPORT_PLOTS_EXTERNAL_DIRECTORY_PREFIX + self.external_overall_plot_filename
        )
        # upload overall plot to s3 public static
        with open(self.overall_plot_filename, "rb") as f:
            upload_to_public_static(self.external_overall_plot_filename, f.read())

        design_quality_issues = [
            issue
            for issue in self.open_issues
            if _DESIGN_QUALITY_LABEL in issue.labels
            or _DESIGN_QUALITY_DEPRECATED_LABEL in issue.labels
        ]
        self.max_dupes_design_quality_issues = self.calculate_max_dupes_issues(
            design_quality_issues, min_dupes=0
        )

        self.issues_with_closed_parents = self.find_issues_with_closed_parents()
        self.recent_changes = self.find_recent_changes(self.issue_datasets)

        current_issues = QualityReportIssueDataset(
            self.end_date,
            self.title,
            self.issues,
            [issue.issue_key for issue in self.max_priority_issues],
            [issue.issue_key for issue in self.max_dupes_issues_no_overlap],
        )
        self.issue_datasets.append(current_issues)

        # Determine the past score breakdowns of recent weeks to create table of number of bugs by type by week
        self.past_score_breakdowns = [
            self.calculate_scores(issue_dataset.date, issue_dataset.issues)
            for issue_dataset in self.issue_datasets[-_NUM_WEEKS_IN_PAST_SCORE_BREAKDOWN:]
        ]

    def find_recent_changes(self, issue_datasets: list[QualityReportIssueDataset]) -> RecentChanges:
        """
        Finds issues that have been resolved or opened/updated since the last quality report
        This function simulates add/removing/resolving issues since the last quality report in order to
        determine the effect of recent changes on the quality score.
        Then we return a RecentChanges object storing the changed issues and impact on the quality score

        Returns:
            RecentChanges object
        """
        for i in range(len(issue_datasets) - 1, -1, -1):
            if issue_datasets[i].date <= self.end_date - timedelta(days=6):
                previous_report_date_string = date_to_str(issue_datasets[i].date)
                previous_key_to_issue = {
                    issue.issue_key: issue for issue in issue_datasets[i].issues
                }
                break
        else:
            return RecentChanges([], [], [], 0, 0, 0, "No previous quality report found")

        previous_score_breakdown = self.calculate_scores(
            self.end_date, previous_key_to_issue.values()
        )
        previous_closed_score = previous_score_breakdown.closed_points
        previous_open_score = previous_score_breakdown.open_points
        previous_overall_score = previous_score_breakdown.overall_score

        current_issues_keys = {issue.issue_key for issue in self.issues}
        newly_included_issues = current_issues_keys - previous_key_to_issue.keys()
        newly_removed_issues = previous_key_to_issue.keys() - current_issues_keys
        newly_resolved_issues = set()
        for issue in self.issues:
            if issue.quality_score_params.is_done:
                if issue.issue_key in previous_key_to_issue:
                    if not previous_key_to_issue[issue.issue_key].quality_score_params.is_done:
                        newly_resolved_issues.add(issue.issue_key)
                else:
                    newly_resolved_issues.add(issue.issue_key)
                    # only count issues in one set
                    newly_included_issues.remove(issue.issue_key)

        # calculate change in score due to newly resolved issues
        resolved_closed_score_delta = 0
        resolved_open_score_delta = 0
        for issue_key in newly_resolved_issues:
            resolved_closed_score_delta += self.key_to_issue[issue_key].quality_score_params.score
            if issue_key in previous_key_to_issue:
                resolved_open_score_delta -= previous_key_to_issue[
                    issue_key
                ].quality_score_params.score
        new_total = (
            previous_closed_score
            + previous_open_score
            + resolved_closed_score_delta
            + resolved_open_score_delta
        )
        new_closed_total = previous_closed_score + resolved_closed_score_delta
        if new_total:
            change_due_to_resolved_issues = (
                100 * new_closed_total / new_total - previous_overall_score
            )
        else:
            change_due_to_resolved_issues = "N/A"

        # calculate change in score due to newly included issues
        added_open_score_delta = 0
        for issue_key in newly_included_issues:
            assert not self.key_to_issue[issue_key].quality_score_params.is_done
            added_open_score_delta += self.key_to_issue[issue_key].quality_score_params.score
        new_total += added_open_score_delta
        if new_total:
            change_due_to_included_issues = 100 * new_closed_total / new_total - (
                previous_overall_score + change_due_to_resolved_issues
            )
        else:
            change_due_to_included_issues = "N/A"

        # calculate change in score due to newly removed issues
        removed_closed_score_delta = 0
        removed_open_score_delta = 0
        for issue_key in newly_removed_issues:
            if previous_key_to_issue[issue_key].quality_score_params.is_done:
                removed_closed_score_delta -= previous_key_to_issue[
                    issue_key
                ].quality_score_params.score
            else:
                removed_open_score_delta -= previous_key_to_issue[
                    issue_key
                ].quality_score_params.score
        new_total += removed_closed_score_delta + removed_open_score_delta
        new_closed_total += removed_closed_score_delta
        if new_total:
            change_due_to_removed_issues = 100 * new_closed_total / new_total - (
                previous_overall_score
                + change_due_to_resolved_issues
                + change_due_to_included_issues
            )
        else:
            change_due_to_removed_issues = "N/A"

        return RecentChanges(
            change_due_to_included_issues,
            change_due_to_removed_issues,
            change_due_to_resolved_issues,
            newly_included_issues,
            newly_removed_issues,
            newly_resolved_issues,
            previous_report_date_string,
        )

    def find_issues_with_closed_parents(self) -> list[JiraDocument]:
        """
        Returns a list of jira issues that have a closed parent
        """
        open_issues_with_closed_parent = []

        for issue in self.issues:
            if JiraDocument.is_group_parent(issue) and issue.quality_score_params.is_done:
                open_issues_with_closed_parent.extend(
                    [
                        self.key_to_issue[key]
                        for key in issue.linked_duplicate_keys
                        if key in self.key_to_issue
                        and not self.key_to_issue[key].quality_score_params.is_done
                    ]
                )
        return open_issues_with_closed_parent

    def serialize(self) -> SerializedQualityReportData:
        """
        returns a SerializedQualityReportData object representing the quality report object
        """
        max_priority_issues_json = [
            JiraDocument.serialize_to_json(issue, _JIRA_FIELDS_TO_FILTER)
            for issue in self.max_priority_issues
        ]
        max_dupes_issues_json = [
            JiraDocument.serialize_to_json(issue, _JIRA_FIELDS_TO_FILTER)
            for issue in self.max_dupes_issues
        ]
        design_quality_issues_json = [
            JiraDocument.serialize_to_json(issue, _JIRA_FIELDS_TO_FILTER)
            for issue in self.max_dupes_design_quality_issues
        ]
        return SerializedQualityReportData(
            end_date=date_to_str(self.end_date),
            features=list(self.features),
            open_bugs_url=self.open_issues_link,
            open_bugs_count=len(self.open_issues),
            overall_score=self.score_breakdown.overall_score,
            previous_overall_score=self.previous_overall_score,
            score_breakdowns=self.past_score_breakdowns,
            scores=self.project_to_scores,
            start_date=date_to_str(self.start_date),
            max_priority_issues=max_priority_issues_json,
            max_dupes_issues=max_dupes_issues_json,
            design_quality_issues=design_quality_issues_json,
            title=self.title,
        )


class QualityReportTeam(QualityReport):
    def __init__(
        self,
        end_date: datetime,
        issues: list[JiraDocument],
        past_issue_datasets: list[QualityReportIssueDataset],
        project_to_scores: dict[str, QualityScoreHistory],
        start_date: datetime,
        team: str,
        area: str,
    ) -> None:
        """
        See parent class
        team: string of team name
        """
        super().__init__(
            end_date,
            TEAM_TO_FEATURES.get(team),
            issues,
            past_issue_datasets,
            project_to_scores,
            start_date,
            team,
            area,
            monthly=False,
        )
        self.jeeves_link = f"https://jeeves.duolingo.com/en/quality-report?area={urllib.parse.quote(area)}&team={urllib.parse.quote(team)}"


class QualityReportArea(QualityReport):
    def __init__(
        self,
        end_date: datetime,
        issues: list[JiraDocument],
        past_issue_datasets: list[QualityReportIssueDataset],
        project_to_scores: dict[str, QualityScoreHistory],
        start_date: datetime,
        area: str,
        team_data: list[SerializedQualityReportData],
    ) -> None:
        """
        See parent class
        area: string of area name
        team_data: list of SerializedQualityReportData for each team in the area
        """
        super().__init__(
            end_date,
            AREA_TO_FEATURES.get(area),
            issues,
            past_issue_datasets,
            project_to_scores,
            start_date,
            area,
            area,
            monthly=False,
        )
        self.team_data = team_data
        self.jeeves_link = (
            f"https://jeeves.duolingo.com/en/quality-report?area={urllib.parse.quote(area)}"
        )

    def serialize(self) -> SerializedQualityReportDataArea:
        """
        See parent class. Also includes serialize quality report data for teams in the area
        """
        quality_report_data = SerializedQualityReportDataArea.from_instance(super().serialize())
        quality_report_data.teams = self.team_data
        return quality_report_data

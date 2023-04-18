import abc
import json
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple

from attr import dataclass
from jinja2 import Environment, FileSystemLoader

from jeeves.config.config import JIRA_PROJECTS
from jeeves.config.jira_features import JIRA_FEATURES
from jeeves.lib.quality_report_plot import create_plot
from jeeves.model.quality_report_base import QualityReportBase
from jeeves.model.quality_report_issue import QualityReportIssue
from jeeves.model.quality_report_project_section import QualityReportProjectSection
from jeeves.util.date_util import date_to_str, str_to_date
from jeeves.util.quality_report_util import get_past_quality_issue_data
from jeeves.util.s3_client_and_bucket import (
    get_s3_client_and_bucket,
    upload_to_jeeves_s3,
    upload_to_public_static,
)

# Maps from area/team name to a set of their features
_AREA_TO_FEATURES = {
    area: {feature for features in teams.values() for feature in features}
    for area, teams in JIRA_FEATURES.items()
}
_TEAM_TO_FEATURES = {
    team: {feature for feature in features.keys()}
    for teams in JIRA_FEATURES.values()
    for team, features in teams.items()
}

_QUALITY_REPORT_PLOTS_EXTERNAL_DIRECTORY_PREFIX = "https://public-static.duolingo.com/"
_S3_PATH = "quality_report_scores"
_TEMPLATE_DIRECTORY = "templates/quality_report/"
_VISUAL_POLISH_LABEL = "visual-polish"


@dataclass
class RecentChanges:
    """
    This class helps organize the data collected when checking for what's changed since the last quality report.
    """

    change_due_to_included_issues: float
    change_due_to_removed_issues: float
    change_due_to_resolved_issues: float
    newly_included_issues: List[QualityReportIssue]
    newly_removed_issues: List[QualityReportIssue]
    newly_resolved_issues: List[QualityReportIssue]
    previous_report_date: str


class QualityReport(QualityReportBase, metaclass=abc.ABCMeta):
    def __init__(
        self,
        end_date: datetime,
        features: Optional[Set[str]],
        issues: List[QualityReportIssue],
        key_to_issue: Dict[str, QualityReportIssue],
        start_date: datetime,
        title: str,
        monthly: bool = True,
        dry_run: bool = True,
    ) -> None:
        """
        Calculates, initializes, and uploads quality scores for a specific area or team using given bugs
        Initializes a QualityReportProjectSection for each project

        Params:
            See parent class
            monthly: whether to calculate monthly scores or weekly
            dry_run: whether to upload to S3 or not
        """
        if features:
            issues = [issue for issue in issues if issue.feature in features]
        super().__init__(end_date, features, issues, key_to_issue, None, start_date, title)
        self.start_date = start_date
        self.dry_run = dry_run

        project_to_scores = self.get_past_quality_scores()
        project_to_scores = {
            key: sorted(
                [
                    (date, score)
                    for date, score in history
                    if date != date_to_str(self.end_date) and not score is None
                ]
            )
            for key, history in project_to_scores.items()
        }

        project_to_scores["Overall"].append((date_to_str(self.end_date), self.overall_score))
        self.project_sections = []
        for project in JIRA_PROJECTS:
            section = QualityReportProjectSection(
                self.end_date,
                project,
                self.features,
                self.issues,
                self.key_to_issue,
                project_to_scores[project],
                self.start_date,
                self.title,
            )
            self.project_sections.append(section)
            project_to_scores[project].append((date_to_str(self.end_date), section.overall_score))

        self.upload_quality_scores_to_s3(project_to_scores)
        self.aggregate_scores = self.calculate_aggregate_scores(project_to_scores, monthly=monthly)
        self.aggregate_overall_score = self.aggregate_scores["Overall"][-1][1]
        if len(self.aggregate_scores["Overall"]) > 1:
            self.previous_aggregate_overall_score = self.aggregate_scores["Overall"][-2][1]
        self.overall_plot_filename, self.external_overall_plot_filename = create_plot(
            self,
            self.aggregate_scores,
            "Overall",
            legend=True,
        )
        self.external_overall_plot_path = (
            _QUALITY_REPORT_PLOTS_EXTERNAL_DIRECTORY_PREFIX + self.external_overall_plot_filename
        )
        # upload overall plot to s3 public static
        with open(self.overall_plot_filename, "rb") as f:
            upload_to_public_static(self.external_overall_plot_filename, f.read())

        visual_polish_issues = [
            issue for issue in self.open_issues if _VISUAL_POLISH_LABEL in issue.labels
        ]
        self.max_dupes_visual_polish_issues = self.calculate_max_dupes_issues(
            visual_polish_issues, min_dupes=0
        )

        self.issues_with_closed_parents = self.find_issues_with_closed_parents()

        current_issues = {issue.issue_key: issue.serialize() for issue in self.issues}
        issue_data = get_past_quality_issue_data(self.title)
        issue_data = [
            issue for issue in issue_data if issue["date"] != date_to_str(datetime(2023, 3, 30))
        ]
        issue_data.append(
            {
                "date": date_to_str(self.end_date),
                "title": self.title,
                "issues": current_issues,
                "max_priority_issues": [issue.issue_key for issue in self.max_priority_issues],
                "max_dupes_issues": [issue.issue_key for issue in self.max_dupes_issues_no_overlap],
            }
        )
        # upload new issue data
        self.upload_quality_issue_data_to_s3(issue_data)
        self.recent_changes = self.find_recent_changes(issue_data)

        self.environment = Environment(loader=FileSystemLoader(_TEMPLATE_DIRECTORY))
        self.compile_html()

    def upload_quality_scores_to_s3(self, score_history: Dict[str, Tuple[str, int]]):
        """
        Uploads quality report scores to s3

        Params:
            score_history: dictionary of the format {"DLAA": [("2000-01-01", 56) ...},  includes Overall, DLAA, DLAI, DLAW
        """
        score_data = {"title": self.title, "score_history": score_history}
        if self.dry_run:
            return
        upload_to_jeeves_s3(
            f"{_S3_PATH}/{self.title}/quality_score_{self.title}",
            json.dumps(score_data),
        )

    def get_past_quality_scores(self) -> Dict[str, List[Tuple[str, int]]]:
        """
        gets the past quality scores for each project and Overall

        returns:
            dictionary of the following structure (where score is an int and date is a str such as "2022-09-09"):
                "Overall": [(date str, score)...]
                "DLAA": [...]
                "DLAI": [...]
                "DLAA": [...]
        """
        s3_client, s3_bucket_name = get_s3_client_and_bucket()
        try:
            return json.loads(
                s3_client.download(
                    s3_bucket_name, f"{_S3_PATH}/{self.title}/quality_score_{self.title}"
                )
            )["score_history"]
        except:
            print(
                f"Could not find quality report scores for {self.title}",
            )
            return {"Overall": [], "DLAA": [], "DLAI": [], "DLAW": []}

    def upload_quality_issue_data_to_s3(self, issue_data: List[Dict[str, Any]]):
        """
        Uploads quality report issue data to s3

        Params:
            issue_data: dictionary of the following structure
            [{"date": "2021-09-09", "title": "Path", "issues": {"DLAA-1000":{"status":"Closed"}}}, ...]
        """
        if self.dry_run:
            return
        upload_to_jeeves_s3(
            f"{_S3_PATH}/{self.title}/quality_issue_data_{self.title}",
            json.dumps(issue_data),
        )

    def find_recent_changes(self, issue_data: List[Dict[str, Any]]) -> RecentChanges:
        """
        Finds issues that have been resolved or opened/updated since the last quality report
        This function simulates add/removing/resolving issues since the last quality report in order to
        determine the effect of recent changes on the quality score.
        Then we return a RecentChanges object storing the changed issues and impact on the quality score

        Returns:
            RecentChanges object
        """
        for i in range(len(issue_data) - 1, -1, -1):
            if str_to_date(issue_data[i]["date"]) <= self.end_date.date() - timedelta(days=6):
                previous_report_date = issue_data[i]["date"]
                previous_key_to_issue = {
                    key: QualityReportIssue.deserialize(issue)
                    for key, issue in issue_data[i]["issues"].items()
                }
                break
        else:
            return RecentChanges([], [], [], 0, 0, 0, "No previous quality report found")

        (
            previous_overall_score,
            previous_open_score,
            previous_closed_score,
            _,
        ) = self.calculate_scores(previous_key_to_issue.values())

        current_issues_keys = {issue.issue_key for issue in self.issues}
        newly_included_issues = current_issues_keys - previous_key_to_issue.keys()
        newly_removed_issues = previous_key_to_issue.keys() - current_issues_keys
        newly_resolved_issues = set()
        for issue in self.issues:
            if issue.score_params.is_done:
                if issue.issue_key in previous_key_to_issue:
                    if not previous_key_to_issue[issue.issue_key].is_done:
                        newly_resolved_issues.add(issue.issue_key)
                else:
                    newly_resolved_issues.add(issue.issue_key)
                    # only count issues in one set
                    newly_included_issues.remove(issue.issue_key)

        # calculate change in score due to newly resolved issues
        resolved_closed_score_delta = 0
        resolved_open_score_delta = 0
        for issue_key in newly_resolved_issues:
            resolved_closed_score_delta += self.key_to_issue[issue_key].score_params.score
            if issue_key in previous_key_to_issue:
                resolved_open_score_delta -= previous_key_to_issue[issue_key].score_params.score
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
            assert not self.key_to_issue[issue_key].score_params.is_done
            added_open_score_delta += self.key_to_issue[issue_key].score_params.score
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
            if previous_key_to_issue[issue_key].score_params.is_done:
                removed_closed_score_delta -= previous_key_to_issue[issue_key].score_params.score
            else:
                removed_open_score_delta -= previous_key_to_issue[issue_key].score_params.score
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
            previous_report_date,
        )

    def find_issues_with_closed_parents(self) -> List[QualityReportIssue]:
        """
        Returns a list of jira issues that have a closed parent
        """
        open_issues_with_closed_parent = []

        for issue in self.issues:
            if issue.is_parent and issue.score_params.is_done:
                open_issues_with_closed_parent.extend(
                    [
                        self.key_to_issue[key]
                        for key in issue.linked_duplicate_keys
                        if key in self.key_to_issue
                        and not self.key_to_issue[key].score_params.is_done
                    ]
                )
        return open_issues_with_closed_parent

    def compile_html(self) -> str:
        """
        Returns an html string of the report
        """
        self.project_sections.sort(key=lambda x: x.overall_score)
        template = self.environment.get_template("team.html")
        self.html = template.render(report=self)


class QualityReportTeam(QualityReport):
    def __init__(
        self,
        end_date: datetime,
        issues: List[QualityReportIssue],
        key_to_issue: Dict[str, QualityReportIssue],
        start_date: datetime,
        team: str,
        dry_run: bool = True,
    ) -> None:
        """
        See parent class
        team: string of team name
        """
        super().__init__(
            end_date,
            _TEAM_TO_FEATURES.get(team),
            issues,
            key_to_issue,
            start_date,
            team,
            monthly=False,
            dry_run=dry_run,
        )


class QualityReportArea(QualityReport):
    def __init__(
        self,
        end_date: datetime,
        issues: List[QualityReportIssue],
        key_to_issue: Dict[str, QualityReportIssue],
        start_date: datetime,
        area: str,
        sub_teams: Dict[str, QualityReportTeam],
        dry_run: bool = True,
    ) -> None:
        """
        See parent class
        area: string of area name
        sub_teams: mapping from team name to QualityReportTeam
        """
        self.sub_teams = sub_teams
        super().__init__(
            end_date,
            _AREA_TO_FEATURES.get(area),
            issues,
            key_to_issue,
            start_date,
            area,
            monthly=False,
            dry_run=dry_run,
        )
        self.max_priority_issues = [
            issue for team in self.sub_teams.values() for issue in team.max_priority_issues[:2]
        ]
        self.max_dupes_issues = [
            issue
            for team in self.sub_teams.values()
            for issue in team.max_dupes_issues[:2]
            if issue not in self.max_priority_issues
        ]

    def compile_html(self) -> str:
        """See parent class"""
        template = self.environment.get_template("area.html")
        self.html = template.render(report=self)

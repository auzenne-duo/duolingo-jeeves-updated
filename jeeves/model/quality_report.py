import abc
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Optional, Set, Tuple

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import seaborn as sns
from dateutil.relativedelta import relativedelta
from jinja2 import Environment, FileSystemLoader

from jeeves.config.config import JIRA_PROJECTS, QUALITY_REPORT_PLOTS_DIRECTORY
from jeeves.config.jira_features import JIRA_FEATURES
from jeeves.model.jira_document import JiraDocument
from jeeves.util.date_util import date_to_str, str_to_date
from jeeves.util.quality_report_priority import QualityReportPriority
from jeeves.util.quality_report_util import check_jira_issue_resolved
from jeeves.util.s3_client_and_bucket import get_s3_client_and_bucket, upload_to_s3

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
_MAX_BUG_SCREENS = 5
# The maximum number of issues shown per "worst issues" category
_MAX_NUMBER_WORST_ISSUES = 4
_PLOT_RANGE_MONTHS = 4
_QUOTE_ESCAPE_CHAR = "%22"
_SCREEN_BUG_NUMBER_THRESHOLD = 0
_TEMPLATE_DIRECTORY = "jeeves/util/quality_report_templates/"
_UNRESOLVED_STATUSES = [
    "Confirmed",
    "Considering",
    "In Design",
    "In Development",
    "In Progress",
    "In Code Review",
    "In Review",
    "In Testing",
    "Ready for Design",
    "To Do",
    "Unconfirmed",
]


class IssueStatus(Enum):
    OPEN = auto()
    CLOSED = auto()


@dataclass
class ScoreBreakdown:
    """Class for keeping track of quality score breakdown stats."""

    issueStatus: IssueStatus
    score: int
    sorted_priority_counts: List[Tuple[QualityReportPriority, int]]


class QualityReportBase:
    def __init__(
        self,
        end_date: datetime,
        project: Optional[str],
        features: Optional[List[str]],
        jira_issues: List[JiraDocument],
        key_to_issue: Dict[str, JiraDocument],
        title: str,
    ) -> None:
        """
        Base class for calculating quality scores. Initializes quality scores and stats

        Params:
            end_date: datetime for the end of the range of bugs (inclusive)
            project: string for project such as "DLAA" or None
            features: list of Jira features used for the quality report or None
            jira_issues: list of Jira documents to be used in making the report
            key_to_issue: mapping of Jira key to Jira document for all of jira_issues
            title: string for team/area such as "China"
        """
        self.end_date = end_date
        self.features = features
        self.jira_issues = jira_issues
        self.key_to_issue = key_to_issue
        self.project = project
        self.title = title

        self.create_status_priority_count()
        self.calculate_scores()
        self.num_closed = sum(self.status_priority_count[IssueStatus.CLOSED].values())
        self.num_open = sum(self.status_priority_count[IssueStatus.OPEN].values())
        self.create_open_issues_link()

    def create_status_priority_count(self) -> None:
        """
        Initializes a dictionary mapping an issue_status to mapping of QualityReportPriority to count of issues
        """
        status_priority_count = {IssueStatus.OPEN: Counter(), IssueStatus.CLOSED: Counter()}
        for issue in self.jira_issues:
            status = IssueStatus.CLOSED if issue.is_done else IssueStatus.OPEN
            status_priority_count[status][issue.priority] += 1
        self.status_priority_count = status_priority_count

    def calculate_scores(self) -> None:
        """
        Initializes a weighted scoring of closed and opened issues and an overall score as the fraction of closed score over total score
        """
        open_score = sum(
            [
                priority.score * count
                for priority, count in self.status_priority_count[IssueStatus.OPEN].items()
            ]
        )
        closed_score = sum(
            [
                priority.score * count
                for priority, count in self.status_priority_count[IssueStatus.CLOSED].items()
            ]
        )
        if open_score + closed_score == 0:
            overall_score = 100
        else:
            overall_score = round(closed_score / (open_score + closed_score) * 100)
        self.overall_score, self.open_score, self.closed_score = (
            overall_score,
            open_score,
            closed_score,
        )

    def create_open_issues_link(self) -> None:
        """Initialize a Jira link for open tickets"""
        statuses = [
            f"{_QUOTE_ESCAPE_CHAR}{status}{_QUOTE_ESCAPE_CHAR}" for status in _UNRESOLVED_STATUSES
        ]
        self.open_issues_link = (
            f'https://duolingo.atlassian.net/issues/?jql=status in ({", ".join(statuses)})'
        )
        if self.project:
            self.open_issues_link += f" AND project={self.project}"
        if self.features:
            features_string = {
                ", ".join(
                    f"{_QUOTE_ESCAPE_CHAR}{feature}{_QUOTE_ESCAPE_CHAR}"
                    for feature in self.features
                )
            }
            self.open_issues_link += f' AND Feature[Dropdown] in ({", ".join(features_string)})'
        self.open_issues_link += " ORDER BY updated DESC"

    def create_plot(
        self,
        project_to_scores: Dict[str, List[Tuple[datetime, int]]],
        plot_title: str,
        legend: bool = False,
    ) -> str:
        """
        Given a list of date/score tuples, creates a plot, saves it, and returns the filename

        params:
            project_to_scores: mapping from project str (eg "DLAA") to a list of date and score tuples
            plot_title: str to be used as the plot's title
            legend: flag to indicate whether a legend should be included

        returns: filename as a string
        """

        juicy_owl = "#58CC02"
        juicy_macaw = "#1CB0F6"
        juicy_beetle = "#CE82FF"
        juicy_narwhal = "#1453A3"
        juicy_butterfly = "#6F4EA1"
        juicy_gray = "#4B4B4B"
        color_list = [
            juicy_macaw,
            juicy_owl,
            juicy_butterfly,
            juicy_narwhal,
            juicy_beetle,
        ]
        plt.rcParams["axes.prop_cycle"] = plt.cycler(color=color_list)

        sns.set(
            rc={
                "axes.axisbelow": False,
                "axes.edgecolor": "lightgrey",
                "axes.facecolor": "None",
                "axes.grid": False,
                "axes.labelcolor": juicy_gray,
                "axes.spines.right": False,
                "axes.spines.top": False,
                "figure.facecolor": "white",
                "lines.solid_capstyle": "round",
                "patch.edgecolor": "w",
                "patch.force_edgecolor": True,
                "text.color": juicy_gray,
                "xtick.bottom": True,
                "xtick.color": juicy_gray,
                "xtick.direction": "out",
                "xtick.top": False,
                "ytick.color": juicy_gray,
                "ytick.direction": "out",
                "ytick.left": False,
                "ytick.right": False,
            },
        )
        sns.set_context(
            "notebook", rc={"font.size": 25, "axes.titlesize": 25, "axes.labelsize": 25}
        )

        plt.figure()
        plt.ylim([0, 105])
        plt.xlim(
            [
                self.end_date - relativedelta(months=_PLOT_RANGE_MONTHS),
                self.end_date + relativedelta(months=1),
            ]
        )

        # add gray horizontal lines at each 20 tick
        for y in range(20, 120, 20):
            plt.plot(
                [
                    self.end_date - relativedelta(months=x)
                    for x in range(-1, _PLOT_RANGE_MONTHS + 1)
                ],
                [y] * (_PLOT_RANGE_MONTHS + 2),
                "--",
                lw=0.5,
                color="black",
                alpha=0.3,
            )
        plt.gca().xaxis.set_major_formatter(mdates.DateFormatter("%b, '%y"))
        plt.gca().xaxis.set_major_locator(mdates.MonthLocator(interval=1))

        for title, scores in project_to_scores.items():
            y = [score for _, score in scores]
            days = [date for date, _ in scores]
            plt.plot(days, y, linestyle="--", marker="o", label=title)
        if legend:
            plt.legend(
                bbox_to_anchor=(1.02, 1),
                loc="upper left",
                borderaxespad=0,
                frameon=False,
                prop={"size": 12},
            )

        filename = f"{QUALITY_REPORT_PLOTS_DIRECTORY}/{self.title}_{plot_title}.png"
        plt.savefig(filename, bbox_inches="tight")
        plt.close()
        return filename


class QualityReportProjectSection(QualityReportBase):
    def __init__(
        self,
        end_date: datetime,
        project: str,
        features: List[str],
        jira_issues: List[JiraDocument],
        key_to_issue: Dict[str, JiraDocument],
        score_history: List[Tuple[datetime, int]],
        title: str,
    ) -> None:
        """
        Calculates and initializes quality scores for a specific project using given bugs

        Params
        See parent class
        score_history: a list of date and score tuples of previously computed quality scores
        """
        jira_issues = [issue for issue in jira_issues if issue.project == project]
        super().__init__(end_date, project, features, jira_issues, key_to_issue, title)
        if not self.jira_issues:
            return
        self.score_history = score_history

        self.max_issue_screens = self.calculate_screen_count()
        self.open_jira_issues = [issue for issue in self.jira_issues if not issue.is_done]
        if self.open_jira_issues:
            self.max_priority_issues = self.calculate_max_priority_issues()
            self.max_dupes_issues = self.calculate_max_dupes_issues()
        self.score_history.append((self.end_date, self.overall_score))
        self.plot_filename = self.create_plot({self.project: self.score_history}, self.project)
        self.score_breakdowns = self.create_score_breakdowns()

    def calculate_screen_count(self) -> List[Tuple[str, int]]:
        """
        Returns a list of screen strings and the number of issues per each
        """
        screen_count = Counter()
        for issue in self.jira_issues:
            if issue.project == "DLAA":
                screen = issue.screen_content.split(".")[-1]
            elif issue.project == "DLAW":
                screen = issue.screen_content.split(".com")[-1]
            else:
                screen = issue.screen_content
            screen_count[screen] += 1
        return sorted(
            [
                (screen, count)
                for screen, count in screen_count.items()
                if screen and count > _SCREEN_BUG_NUMBER_THRESHOLD
            ],
            key=lambda x: -x[1],
        )[:_MAX_BUG_SCREENS]

    def calculate_max_priority_issues(self) -> List[JiraDocument]:
        """
        Return the top _MAX_NUMBER_WORST_ISSUES maximum priority issues of the open issues as a list of issues with the highest priority
        (breaking ties by number of duplicates)
        """
        self.jira_issues.sort(key=lambda issue: -len(issue.linked_duplicate_keys))
        self.jira_issues.sort(key=lambda issue: issue.priority, reverse=True)
        return self.jira_issues[:_MAX_NUMBER_WORST_ISSUES]

    def calculate_max_dupes_issues(self) -> List[JiraDocument]:
        """
        Return the top _MAX_NUMBER_WORST_ISSUES issues of the open issues with the most duplicates as a list of issues
        with the highest priority (breaking ties by priority)
        """
        jira_issues_filtered = [issue for issue in self.jira_issues if issue.linked_duplicate_keys]
        jira_issues_filtered.sort(key=lambda issue: issue.priority, reverse=True)
        jira_issues_filtered.sort(key=lambda issue: -len(issue.linked_duplicate_keys))
        return jira_issues_filtered[:_MAX_NUMBER_WORST_ISSUES]

    def create_score_breakdowns(self) -> List[ScoreBreakdown]:
        """
        Returns a ScoreBreakdown for each issue status
        """
        return [
            ScoreBreakdown(
                issue_status,
                score,
                sorted(
                    [
                        (priority, count)
                        for priority, count in self.status_priority_count[issue_status].items()
                    ],
                    key=lambda x: x[0],
                    reverse=True,
                ),
            )
            for issue_status, score in [
                (IssueStatus.OPEN, self.open_score),
                (IssueStatus.CLOSED, self.closed_score),
            ]
        ]


class QualityReport(QualityReportBase, metaclass=abc.ABCMeta):
    def __init__(
        self,
        end_date: datetime,
        features: Optional[Set[str]],
        jira_issues: List[JiraDocument],
        key_to_issue: Dict[str, JiraDocument],
        start_date: datetime,
        title: str,
    ) -> None:
        """
        Calculates, initializes, and uploads quality scores for a specific area or team using given bugs
        Initializes a QualityReportProjectSection for each project

        Params:
            See parent class
            start_date: datetime for the beginning of the range of bugs (inclusive)
        """

        if not features is None:
            jira_issues = [issue for issue in jira_issues if issue.feature in features]
        super().__init__(end_date, None, features, jira_issues, key_to_issue, title)
        self.project_to_scores: Dict[str, List[Tuple[str, float]]]
        self.start_date = start_date

        project_to_scores = self.get_past_quality_scores()
        project_to_scores["Overall"].append((self.end_date, self.overall_score))
        project_scores = {"Overall": self.overall_score}
        self.project_sections = []
        for project in JIRA_PROJECTS:
            section = QualityReportProjectSection(
                self.end_date,
                project,
                self.features,
                self.jira_issues,
                self.key_to_issue,
                project_to_scores[project],
                self.title,
            )
            self.project_sections.append(section)
            project_to_scores[project].append((self.end_date, section.overall_score))
            project_scores[project] = section.overall_score

        self.upload_quality_scores_to_s3(project_scores)
        self.overall_plot_filename = self.create_plot(project_to_scores, "Overall", legend=True)

        self.issues_with_closed_parents = self.find_issues_with_closed_parents()
        self.environment = Environment(loader=FileSystemLoader(_TEMPLATE_DIRECTORY))
        self.compile_html()

    @abc.abstractmethod
    def compile_html(self):
        """
        Formats a quality report html string and stores in self.html
        """

    def upload_quality_scores_to_s3(self, scores: Dict[str, int]):
        """
        Uploads quality report scores to s3

        Params:
            scores: dictionary of the format {"DLAA": 56, ...} include Overall, DLAA, DLAI, DLAW
        """
        end_date_str = date_to_str(self.end_date)
        score_data = {"area or team": self.title, "end_date": end_date_str, "scores": scores}
        upload_to_s3(
            f"quality_report_scores/{self.title}/quality_score_{self.title}_{end_date_str}",
            json.dumps(score_data),
        )

    def get_past_quality_scores(self) -> Dict[str, List[Tuple[datetime, int]]]:
        """
        gets the past quality scores for each project and Overall

        returns:
            dictionary of the following structure (where score is an int and date is a str such as "2022-09-09"):
                "Overall": [(date, score)...]
                "DLAA": [...]
                "DLAI": [...]
                "DLAA": [...]
        """
        project_to_scores = defaultdict(list)
        s3_client, s3_bucket_name = get_s3_client_and_bucket()
        for s3_file in s3_client.yield_filenames(
            s3_bucket_name, path_prefix=f"quality_report_scores/{self.title}"
        ):
            data = json.loads(s3_client.download(s3_bucket_name, s3_file))
            for project, score in data["scores"].items():
                project_to_scores[project].append((str_to_date(data["end_date"]), score))
        return project_to_scores

    def find_issues_with_closed_parents(self) -> List[JiraDocument]:
        """
        Returns a list of jira issues that have a closed parent
        """
        open_issues_with_closed_parent = []

        for issue in self.jira_issues:
            if JiraDocument.is_group_parent(issue) and issue.is_done:
                open_issues_with_closed_parent.extend(
                    [
                        self.key_to_issue[key]
                        for key in issue.linked_duplicate_keys
                        if key in self.key_to_issue
                        and not check_jira_issue_resolved(self.key_to_issue[key])
                    ]
                )
        return open_issues_with_closed_parent


class QualityReportTeam(QualityReport):
    def __init__(
        self,
        end_date: datetime,
        jira_issues: List[JiraDocument],
        key_to_issue: Dict[str, JiraDocument],
        start_date: datetime,
        team: str,
    ) -> None:
        """
        See parent class
        team: string of team name
        """
        super().__init__(
            end_date, _TEAM_TO_FEATURES.get(team), jira_issues, key_to_issue, start_date, team
        )

    def compile_html(self):
        """See parent class"""
        self.project_sections.sort(key=lambda x: x.overall_score)
        template = self.environment.get_template("team.html")
        self.html = template.render(report=self)


class QualityReportArea(QualityReport):
    def __init__(
        self,
        end_date: datetime,
        jira_issues: List[JiraDocument],
        key_to_issue: Dict[str, JiraDocument],
        start_date: datetime,
        area: str,
        sub_teams: Dict[str, QualityReportTeam],
    ) -> None:
        """
        See parent class
        area: string of area name
        sub_teams: mapping from team name to QualityReportTeam
        """
        self.sub_teams = sub_teams
        super().__init__(
            end_date, _AREA_TO_FEATURES.get(area), jira_issues, key_to_issue, start_date, area
        )

    def compile_html(self):
        """See parent class"""
        template = self.environment.get_template("area.html")
        self.html = template.render(report=self)

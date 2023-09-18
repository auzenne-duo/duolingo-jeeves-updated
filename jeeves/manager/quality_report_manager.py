import os
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Dict, List

import pytz
from duolingo_base.util import registry

from jeeves.config.config import QUALITY_REPORT_PLOTS_DIRECTORY
from jeeves.config.jira_features import JIRA_FEATURES
from jeeves.dal.quality_report_dal import QualityReportDAL
from jeeves.lib.send_quality_report_emails import send_email
from jeeves.model.custom_types import JSON
from jeeves.model.jira_document import JiraDocument
from jeeves.model.quality_report import (
    QualityReport,
    QualityReportArea,
    QualityReportTeam,
    QualityScoreHistory,
    SerializedQualityReportData,
)
from jeeves.util.quality_report_util import QUALITY_REPORT_OVERALL_KEY, QUALITY_REPORT_WINDOW_DAYS

_AREAS_TO_EXCLUDE = ["Many", "New Initiatives", "None"]
_TEAMS_TO_EXCLUDE = ["None"]


@dataclass
class QualityReportOverview:
    """
    Dataclass for a quality report's overall score and score history by project
    """

    overall_score: int
    scores: Dict[str, QualityScoreHistory]
    title: str


@registry.bind(
    quality_report_dal=registry.reference(QualityReportDAL),
)
class QualityReportManager:
    def __init__(
        self,
        quality_report_dal: QualityReportDAL,
    ) -> None:
        self.quality_report_dal = quality_report_dal

    def get_area_quality_overviews(self) -> List[QualityReportOverview]:
        """
        Returns a list of QualityReportOverview for each area. This will
        allow for generating overview graphs for all areas
        """
        area_overviews = []
        for area in JIRA_FEATURES:
            if area in _AREAS_TO_EXCLUDE:
                continue
            # get the latest quality scores from s3
            past_project_to_scores = self.quality_report_dal.get_past_quality_scores(area)
            # to help frontend display the current overall score, we will isolate it from the score history
            overall_score = past_project_to_scores.get(QUALITY_REPORT_OVERALL_KEY, [None])[-1][1]
            area_overviews.append(
                QualityReportOverview(
                    scores=past_project_to_scores, title=area, overall_score=overall_score
                )
            )
        return area_overviews

    def get_team_quality_report(
        self,
        area: str,
        end_date: datetime,
        jira_issues: List[JiraDocument],
        start_date: datetime,
        team: str,
    ) -> QualityReportTeam:
        """
        Returns a QualityReportTeam object for a given team. Past scores and issues are
        retrieved to be passed as inputs.

        Params
            area: string name such as "Growth"
            end_date: final day of the quality report period
            jira_issues: list of jira documents that were updated in the report period
            start_date: first day of the quality report period
            team: string name such as "Onboarding"

        Returns
            QualityReportTeam object with score data for the given team

        """
        jira_issues = [issue for issue in jira_issues if issue.team == team]
        past_project_to_scores = self.quality_report_dal.get_past_quality_scores(team)
        past_issue_datasets = self.quality_report_dal.get_past_quality_issue_datasets(team)

        return QualityReportTeam(
            end_date,
            jira_issues,
            past_issue_datasets,
            past_project_to_scores,
            start_date,
            team,
            area,
        )

    def get_area_quality_report(
        self,
        area: str,
        end_date: datetime,
        jira_issues: List[JiraDocument],
        start_date: datetime,
        team_data: List[SerializedQualityReportData],
    ) -> QualityReportArea:
        """
        Returns a QualityReportArea object for a given area. Past scores and issues are
        retrieved to be passed as inputs.

        Params
            area: string name such as "Growth"
            end_date: final day of the quality report period
            jira_issues: list of jira documents that were updated in the report period
            start_date: first day of the quality report period
            team_data: list of serialized quality reports for teams of the area

        Returns
            QualityReportArea object with score data for that area
        """
        jira_issues = [issue for issue in jira_issues if issue.area == area]
        past_project_to_scores = self.quality_report_dal.get_past_quality_scores(area)
        past_issue_datasets = self.quality_report_dal.get_past_quality_issue_datasets(area)

        return QualityReportArea(
            end_date,
            jira_issues,
            past_issue_datasets,
            past_project_to_scores,
            start_date,
            area,
            team_data,
        )

    def get_serialized_quality_report(self, title: str) -> JSON:
        """
        Returns serialized version for the latest quality report for the area or team
        of the given title

        Params
            title: string name of area or team such as "Growth"
        """
        return self.quality_report_dal.get_latest_serialized_quality_report(title)

    def generate_reports(self, save_snapshots=False) -> None:
        """
        Fetches Jira issues from the past QUALITY_REPORT_WINDOW_DAYS and creates
        quality reports.  Serialized reports are uploaded to s3 daily. If save_snapshots
        is set to true, issue data and scores are saved to s3 and emails are sent out.
        """
        end_date = datetime.now(tz=pytz.utc)
        start_date = end_date - timedelta(days=QUALITY_REPORT_WINDOW_DAYS)
        # Ensure directory for graphs exists
        if not os.path.exists(QUALITY_REPORT_PLOTS_DIRECTORY):
            os.mkdir(QUALITY_REPORT_PLOTS_DIRECTORY)

        jira_docs = self.quality_report_dal.get_quality_report_issues(start_date)

        quality_reports = []
        for area, team_to_features in JIRA_FEATURES.items():
            if area in _AREAS_TO_EXCLUDE:
                continue
            team_data = []
            for team in team_to_features:
                if team in _TEAMS_TO_EXCLUDE:
                    continue
                quality_report = self.get_team_quality_report(
                    area, end_date, jira_docs, start_date, team
                )
                # upload latest quality report data
                quality_report_data = quality_report.serialize()
                self.quality_report_dal.upload_serialized_quality_report(quality_report)
                team_data.append(quality_report_data)
                quality_reports.append(quality_report)

            area_quality_report = self.get_area_quality_report(
                area, end_date, jira_docs, start_date, team_data
            )
            quality_reports.append(area_quality_report)
            self.quality_report_dal.upload_serialized_quality_report(area_quality_report)
        # if it's the right day of the week, we will send emails and save report data
        if save_snapshots:
            self.save_report_data(quality_reports, end_date)
        # clean up plots directory
        shutil.rmtree(QUALITY_REPORT_PLOTS_DIRECTORY)

    def save_report_data(self, quality_reports: List[QualityReport], end_date: datetime) -> None:
        """
        Saves quality reports data for weekly snapshots and sends emails. Area emails
        are sent on the first week of the month.

        Params:
            quality_reports: list of quality reports to save snapshots for
        """
        for quality_report in quality_reports:
            # issue_datasets will be used to create score breakdowns and determine recent changes
            self.quality_report_dal.upload_quality_issue_datasets(quality_report)
            # quality score history will be used to generate plots
            self.quality_report_dal.upload_quality_scores_to_s3(quality_report)

            # send area and team report emails
            send_email(quality_report)

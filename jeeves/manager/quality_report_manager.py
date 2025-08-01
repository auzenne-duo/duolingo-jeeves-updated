import json
import logging
import os
import shutil
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Dict, List, Optional

import pytz
from duolingo_base.util import registry
from prometheus_client import Gauge, push_to_gateway

from jeeves.config.config import QUALITY_REPORT_PLOTS_DIRECTORY, get_config
from jeeves.config.jira_features import JIRA_FEATURES
from jeeves.dal.quality_report_dal import QualityReportDAL
from jeeves.lib.send_quality_report_emails import send_email
from jeeves.model.custom_types import JSON
from jeeves.model.jira_document import JiraDocument
from jeeves.model.quality_report import (
    QualityReport,
    QualityReportArea,
    QualityReportPillar,
    QualityReportTeam,
    QualityScoreHistory,
    SerializedQualityReportData,
)
from jeeves.util.date_util import date_to_str, str_to_date
from jeeves.util.quality_report_util import QUALITY_REPORT_OVERALL_KEY, QUALITY_REPORT_WINDOW_DAYS

_PILLAR_TO_EXCLUDE = []
_AREAS_TO_EXCLUDE = ["Many", "New Initiatives", "None"]
_TEAMS_TO_EXCLUDE = ["None"]
LOG = logging.getLogger(__name__)

# Prometheus metric for quality report scores
quality_report_score_gauge = Gauge(
    "quality_report_score", "Quality report score by organization", ["org", "name", "environment"]
)


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
    def __init__(self, quality_report_dal: QualityReportDAL) -> None:
        self.quality_report_dal = quality_report_dal

    def _push_quality_score_to_prometheus(
        self,
        quality_report: QualityReport,
        org_type: str,
        gateway_url: str = "https://prometheus-pushgateway.duolingo.com",
    ) -> None:
        """
        Push quality report score to Prometheus using push_to_gateway.

        Params:
            quality_report: The quality report object containing the score
            org_type: Type of organization ("pillar", "area", or "team")
            gateway_url: Prometheus push gateway URL
        """
        try:
            # Get the overall score from the serialized quality report data
            serialized_data = quality_report.serialize()
            overall_score = serialized_data.overall_score

            # Get environment from config
            environment = get_config().get_nested(["environment"])

            if overall_score is not None:
                # Set the gauge value with labels including environment
                quality_report_score_gauge.labels(
                    org=org_type, name=quality_report.title, environment=environment
                ).set(overall_score)

                # Push to gateway
                push_to_gateway(gateway_url, job="service-quality-report", registry=None)

                LOG.info(
                    f"Successfully pushed quality score {overall_score} for {org_type} '{quality_report.title}' to Prometheus gateway at {gateway_url}"
                )
            else:
                LOG.warning(f"Could not get overall score for {org_type} '{quality_report.title}'")
        except Exception as e:
            LOG.error(
                f"Failed to push quality score to Prometheus for {org_type} '{quality_report.title}': {e}"
            )

    def _post_process_quality_scores(
        self, score_history: List[List[Any]], start_date: date
    ) -> List[List[Any]]:
        """Given a list of quality scores, remove duplicates and sort by date, filter by start_date"""
        score_history_as_dates = [(str_to_date(item[0]), item) for item in score_history]
        # Filter based on start_date
        filtered_scores = [item for item in score_history_as_dates if item[0] >= start_date]
        # Remove duplicates
        unique_scores = {item[0]: item for item in filtered_scores}.values()
        # Sort by date
        sorted_items = sorted(unique_scores, key=lambda x: x[0])

        return [[date_to_str(item[0])] + item[1][1:] for item in sorted_items]

    def get_pillar_quality_overviews(self) -> List[QualityReportOverview]:
        """
        Returns a list of QualityReportOverview for each pillar. This will
        allow for generating overview graphs for all pillars
        """
        pillar_overviews = []
        for pillar in JIRA_FEATURES:
            if pillar in _PILLAR_TO_EXCLUDE:
                continue
            # get the latest quality scores from s3
            past_project_to_scores = self.quality_report_dal.get_past_quality_scores(pillar)

            # to help frontend display the current overall score, we will isolate it from the score history
            overall_score_history: QualityScoreHistory = past_project_to_scores.get(
                QUALITY_REPORT_OVERALL_KEY, None
            )
            if not overall_score_history or not overall_score_history[-1]:
                LOG.warning(f"Could not find overall score for pillar: {pillar}")
                continue

            overall_score = overall_score_history[-1][1]
            pillar_overviews.append(
                QualityReportOverview(
                    scores=past_project_to_scores, title=pillar, overall_score=overall_score
                )
            )

        return pillar_overviews

    def get_area_quality_overviews(self, pillar) -> List[QualityReportOverview]:
        """
        Returns a list of QualityReportOverview for each area. This will
        allow for generating overview graphs for all areas
        """
        area_overviews = []

        for area in JIRA_FEATURES[pillar]:
            if area in _AREAS_TO_EXCLUDE:
                continue
            # get the latest quality scores from s3
            past_project_to_scores = self.quality_report_dal.get_past_quality_scores(area)

            # to help frontend display the current overall score, we will isolate it from the score history
            overall_score_history: QualityScoreHistory = past_project_to_scores.get(
                QUALITY_REPORT_OVERALL_KEY, None
            )
            if not overall_score_history or not overall_score_history[-1]:
                LOG.warning(f"Could not find overall score for area: {area}")
                continue

            overall_score = overall_score_history[-1][1]
            area_overviews.append(
                QualityReportOverview(
                    scores=past_project_to_scores, title=area, overall_score=overall_score
                )
            )

        return area_overviews

    def get_team_quality_overviews(self, pillar, area) -> List[QualityReportOverview]:
        """
        Returns a list of QualityReportOverview for each team in an area. This will
        allow for generating overview graphs for all teams.
        """
        team_overviews = []

        for team in JIRA_FEATURES[pillar][area]:
            if team in _TEAMS_TO_EXCLUDE:
                continue

            # get the latest quality scores from s3
            past_project_to_scores = self.quality_report_dal.get_past_quality_scores(team)

            # to help frontend display the current overall score, we will isolate it from the score history
            overall_score_history: QualityScoreHistory = past_project_to_scores.get(
                QUALITY_REPORT_OVERALL_KEY, None
            )
            if not overall_score_history or not overall_score_history[-1]:
                LOG.warning(f"Could not find overall score for team: {team}")
                continue

            overall_score = overall_score_history[-1][1]
            team_overviews.append(
                QualityReportOverview(
                    scores=past_project_to_scores, title=team, overall_score=overall_score
                )
            )

        return team_overviews

    def get_team_quality_report(
        self,
        area: str,
        end_date: datetime,
        jira_issues: List[JiraDocument],
        start_date: datetime,
        team: str,
        pillar: str,
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
            pillar,
        )

    def get_area_quality_report(
        self,
        area: str,
        end_date: datetime,
        jira_issues: List[JiraDocument],
        start_date: datetime,
        team_data: List[SerializedQualityReportData],
        pillar: str,
    ) -> QualityReportArea:
        """
        Returns a QualityReportArea object for a given area. Past scores and issues are
        retrieved to be passed as inputs.

        Params
            area: string name such a "International Growth"
            end_date: final day of the quality report period
            jira_issues: list of jira documents that were updated in the report period
            start_date: first day of the quality report period
            team_data: list of serialized quality reports for teams of the area
            pillar: pillar name for the area such as "Growth"

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
            pillar,
            team_data,
        )

    def get_pillar_quality_report(
        self,
        pillar: str,
        end_date: datetime,
        jira_issues: List[JiraDocument],
        start_date: datetime,
        area_data: List[SerializedQualityReportData],
    ) -> QualityReportPillar:
        """
        Returns a QualityReportPillar object for a given pillar. Past scores and issues are
        retrieved to be passed as inputs.

        Params
            pillar: string name such as "Growth"
            end_date: final day of the quality report period
            jira_issues: list of jira documents that were updated in the report period
            start_date: first day of the quality report period
            area_data: list of serialized quality reports for areas of the pillar

        Returns
            QualityReportPillar object with score data for that pillar
        """
        jira_issues = [issue for issue in jira_issues if issue.pillar == pillar]
        past_project_to_scores = self.quality_report_dal.get_past_quality_scores(pillar)
        past_issue_datasets = self.quality_report_dal.get_past_quality_issue_datasets(pillar)

        return QualityReportPillar(
            end_date,
            jira_issues,
            past_issue_datasets,
            past_project_to_scores,
            start_date,
            pillar,
            area_data,
        )

    def get_serialized_quality_report(self, title: str) -> JSON:
        """
        Returns serialized version for the latest quality report for the area or team
        of the given title

        Params
            title: string name of area or team such as "Growth"
        """
        return self.quality_report_dal.get_latest_serialized_quality_report(title)

    def get_quality_scores(self, title: str, start_date: date, end_date: date) -> JSON:
        """
        Returns quality scores for a specific area and date range

        Params
            title: string title of the area or team
            start_date: first day of the quality score period
            end_date: final day of the quality score period
        """
        if start_date > end_date:
            raise ValueError("Start date must be before end date")
        if end_date > datetime.now(tz=pytz.utc).date():
            raise ValueError("End date must be before the current date")

        android_score_history = []
        ios_score_history = []
        web_score_history = []
        overall_score_history = []

        quality_report_date = end_date

        while True:
            try:
                quality_report_serialized = (
                    self.quality_report_dal.get_latest_serialized_quality_report(
                        title, date_to_str(quality_report_date)
                    )
                )
            except:
                # it is expected for this to fail if the start date is before the first quality report
                LOG.info(
                    f"Could not find quality report scores for title: {title} with date: {quality_report_date}"
                )
                break

            quality_report = json.loads(quality_report_serialized)
            scores = quality_report.get("scores")
            if scores is None:
                raise ValueError("Quality report does not contain scores")

            # accumulate scores from all quality reports
            android_score_history += scores.get("DLAA", [])
            ios_score_history += scores.get("DLAI", [])
            web_score_history += scores.get("DLAW", [])
            overall_score_history += scores.get(QUALITY_REPORT_OVERALL_KEY, [])

            # setup for next iteration
            start_date_in_quality_report = quality_report.get("start_date")
            quality_report_date = str_to_date(start_date_in_quality_report)

            if quality_report_date <= start_date:
                break

        # post processing to filter, remove duplicates, and sort
        android_score_history = self._post_process_quality_scores(android_score_history, start_date)
        ios_score_history = self._post_process_quality_scores(ios_score_history, start_date)
        web_score_history = self._post_process_quality_scores(web_score_history, start_date)
        overall_score_history = self._post_process_quality_scores(overall_score_history, start_date)

        return {
            "scores": {
                "DLAA": android_score_history,
                "DLAI": ios_score_history,
                "DLAW": web_score_history,
                QUALITY_REPORT_OVERALL_KEY: overall_score_history,
            }
        }

    def generate_reports(
        self,
        save_snapshots: bool = False,
        is_dry_run: bool = False,
        dry_run_recipient: Optional[str] = None,
        window_size: int = QUALITY_REPORT_WINDOW_DAYS,
    ) -> None:
        """
        Fetches Jira issues from the past `window_size` days and creates
        quality reports. Serialized reports are uploaded to s3 daily.

        Params:
            save_snapshots: if true, quality report data is saved to s3 and emails are sent out.
            is_dry_run: if true, perform all tasks, but do not send emails to the normal recipient list, and do not upload results.
            dry_run_recipient: if set, send emails to this recipient instead of the normal recipient list during a dry run.
            window_size: number of days to look back for issues.
        """
        if dry_run_recipient is not None and not is_dry_run:
            raise ValueError("dry_run_recipient should only be set with is_dry_run=True")
        if is_dry_run:
            LOG.warning("Running in dry run mode. Reports will not be uploaded.")
            if dry_run_recipient is not None:
                LOG.warning(
                    f"Sending emails to {dry_run_recipient} instead of the normal recipient list."
                )

        end_date = datetime.now(tz=pytz.utc)
        start_date = end_date - timedelta(days=window_size)
        # Ensure directory for graphs exists
        if not os.path.exists(QUALITY_REPORT_PLOTS_DIRECTORY):
            os.mkdir(QUALITY_REPORT_PLOTS_DIRECTORY)

        jira_docs = self.quality_report_dal.get_quality_report_issues(start_date)

        quality_reports = []
        for pillar in JIRA_FEATURES:
            if pillar in _PILLAR_TO_EXCLUDE:
                continue
            area_data = []
            for area, team_to_features in JIRA_FEATURES[pillar].items():
                if area in _AREAS_TO_EXCLUDE:
                    continue
                team_data = []
                for team in team_to_features:
                    if team in _TEAMS_TO_EXCLUDE:
                        continue
                    quality_report = self.get_team_quality_report(
                        area, end_date, jira_docs, start_date, team, pillar
                    )
                    # upload latest quality report data
                    quality_report_data = quality_report.serialize()
                    if not is_dry_run:
                        self.quality_report_dal.upload_serialized_quality_report(quality_report)
                        # Push team quality score to Prometheus
                        self._push_quality_score_to_prometheus(quality_report, "team")
                    team_data.append(quality_report_data)
                    quality_reports.append(quality_report)

                area_quality_report = self.get_area_quality_report(
                    area, end_date, jira_docs, start_date, team_data, pillar
                )
                area_quality_report_data = area_quality_report.serialize()
                if not is_dry_run:
                    self.quality_report_dal.upload_serialized_quality_report(area_quality_report)
                    # Push area quality score to Prometheus
                    self._push_quality_score_to_prometheus(area_quality_report, "area")
                area_data.append(area_quality_report_data)
                quality_reports.append(area_quality_report)
            pillar_quality_report = self.get_pillar_quality_report(
                pillar, end_date, jira_docs, start_date, area_data
            )
            if not is_dry_run:
                self.quality_report_dal.upload_serialized_quality_report(pillar_quality_report)
                # Push pillar quality score to Prometheus
                self._push_quality_score_to_prometheus(pillar_quality_report, "pillar")
            quality_reports.append(pillar_quality_report)

        # if it's the right day of the week, we will send emails and save report data
        if save_snapshots and not is_dry_run:
            self.save_report_data(quality_reports, end_date)
        elif is_dry_run and dry_run_recipient is not None:
            LOG.warning(f"Dry run report assembly complete. Sending email to {dry_run_recipient}.")
            for quality_report in quality_reports:
                send_email(quality_report, dry_run_recipient)
        else:
            LOG.warning("Dry run report assembly complete. No emails sent.")
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

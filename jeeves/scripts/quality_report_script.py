import os
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

from pydyf import PDF
from weasyprint import CSS, HTML
from weasyprint.text.fonts import FontConfiguration

from jeeves import registry as app_registry
from jeeves.config.config import JIRA_ISSUE_TYPE_BUG, JIRA_PROJECTS, QUALITY_REPORT_PLOTS_DIRECTORY
from jeeves.config.jira_features import JIRA_FEATURES
from jeeves.dal.jira_dal import JiraDAL
from jeeves.lib.identifier_manager_mapping import IDManagerMap
from jeeves.manager.duplicate_graph_resolver import DuplicateGraphResolver
from jeeves.manager.jira_manager import JiraManager
from jeeves.model.jira_document import JiraDocument
from jeeves.model.quality_report import QualityReport, QualityReportArea, QualityReportTeam
from jeeves.util.date_util import date_to_str
from jeeves.util.quality_report_priority import QualityReportPriority, get_quality_report_priority
from jeeves.util.quality_report_util import check_jira_issue_resolved
from jeeves.util.s3_client_and_bucket import upload_to_s3

_CSS_FILENAME = "templates/quality_report/quality_report.css"
_DEFAULT_REPORT_WINDOW_DAYS = 90


def populate_priority_and_is_done(jira_doc: JiraDocument) -> None:
    """
    Populates the priority and is_done fields
    """
    if not isinstance(jira_doc.priority, QualityReportPriority):
        jira_doc.priority = get_quality_report_priority(jira_doc.priority, jira_doc.labels)
    jira_doc.is_done = check_jira_issue_resolved(jira_doc)


def search_for_issues(start_date: datetime, end_date: datetime) -> List[JiraDocument]:
    """
    Yields issues for the specific area within start_date to end_date inclusively

    Params:
        start_date (datetime): only consider issues with updated after this datetime
        end_date (datetime): only consider issues with updated before this datetime

    Returns:
        List of JiraDocuments
    """
    # Need to get the feature field key so that field is set in Jira documents
    JiraManager.get_feature_field()

    max_results_per_page = 100
    start_timestamp = date_to_str(start_date)
    end_timestamp = date_to_str(end_date)
    projects_fetch_string = (
        f"project IN ({','.join(JIRA_PROJECTS)}) "
        + f"AND updated >= {start_timestamp} "
        + f"AND updated <= {end_timestamp} "
        + f"AND issueType = {JIRA_ISSUE_TYPE_BUG} "
        + f"ORDER BY updated asc"
    )

    url_params = {
        "fields": "*all",
        "maxResults": max_results_per_page,
        "startAt": 0,
        "jql": projects_fetch_string,
    }

    issues = []
    for i, issue in enumerate(JiraDAL.paginate_search_issues(url_params)):
        jira_doc = JiraDocument.deserialize_from_external_json(issue)
        # convert priority to a QualityReportPriority object for ease of score calculation
        populate_priority_and_is_done(jira_doc)
        issues.append(jira_doc)
        if i % 500 == 0:
            print(f"Paginating jira issues; at {i}")
    return issues


def format_issue_text(jira_issues: List[JiraDocument]) -> None:
    """
    Replaces characters in jira text that aren't properly handled by html, such as <
    """

    def format_str(text: str) -> str:
        return text.replace("<", "&lt;").replace(">", "&gt;")

    for issue in jira_issues:
        issue.body_text = format_str(issue.body_text)
        issue.header_text = format_str(issue.header_text)


def resolve_duplicate_graphs(
    jira_issues: List[JiraDocument],
) -> Tuple[List[JiraDocument], Dict[str, JiraDocument]]:
    """
    Params:
        jira_issues: list of JiraDocuments

    Returns:
        a list of jira issues with only one representative issue from each duplicate graph.
        a mapping from issue key to Jira document

    For each jira issue we resolve the duplicate graph and determine a representative of each dupe graph
    The rep will be the parent of the graph if it exists. If there is only one issue, then that issue is
    the rep. Otherwise, if there is at least one open issue, some open issue is used as the rep. Finally
    if all issues are done, then any issue that was not closed as a Duplicate is used.
    """

    # Fetch all directly linked duplicates in batch and compile a mapping from issue key to issue
    key_to_issue = {issue.issue_key: issue for issue in jira_issues}
    issues_to_fetch = {
        key
        for issue in jira_issues
        for key in issue.linked_duplicate_keys
        if not key in key_to_issue
    }

    downloaded_issues = IDManagerMap.get_manager_for_identifier(
        "JIRA"
    ).download_bulk_issues_with_features(list(issues_to_fetch))
    key_to_issue.update({issue.issue_key: issue for issue in downloaded_issues})

    # For each issue determine the duplicate graph and choose a representative.
    parent_representatives = set()
    visited_issues = set()
    for issue in jira_issues:
        if issue.issue_key in visited_issues:
            continue
        duplicate_graph = app_registry(DuplicateGraphResolver).get_duplicate_graph(
            [issue.issue_key], key_to_doc=key_to_issue
        )
        duplicate_graph_issues = list(duplicate_graph.issue_keys_to_documents.values())
        for issue in duplicate_graph_issues:
            populate_priority_and_is_done(issue)
        visited_issues.update(duplicate_graph.issue_keys_to_documents.keys())
        parent_issues = [
            issue for issue in duplicate_graph_issues if JiraDocument.is_group_parent(issue)
        ]

        if len(parent_issues) == 1:
            parent_issue_key = parent_issues[0].issue_key
        elif len(parent_issues) > 1:
            # if multiple parents, resolve
            parent_issue_key, _ = app_registry(
                DuplicateGraphResolver
            ).resolve_multiple_parent_issues(parent_issues)
        elif len(duplicate_graph_issues) == 1:
            parent_issue_key = issue.issue_key
        else:
            open_issues = [issue for issue in duplicate_graph_issues if not issue.is_done]
            if len(open_issues) > 0:
                parent_issue_key = open_issues[0].issue_key
            else:
                non_dupes = [
                    issue for issue in duplicate_graph_issues if issue.resolution != "Duplicate"
                ]
                parent_issue_key = (
                    duplicate_graph_issues[0].issue_key
                    if non_dupes == []
                    else non_dupes[0].issue_key
                )

        parent_representatives.add(parent_issue_key)

    return [key_to_issue[key] for key in parent_representatives], key_to_issue


def makepdf(html: str) -> PDF:
    """Generate a PDF file from a string of HTML."""
    font_config = FontConfiguration()
    htmldoc = HTML(string=html, base_url="")
    css = CSS(_CSS_FILENAME, font_config=font_config)

    return htmldoc.write_pdf(stylesheets=[css], font_config=font_config)


def generate_and_save_pdf(
    report: QualityReport,
) -> None:
    """
    Generates a pdf using html of quality report and saves as a pdf in s3
    """
    filename_pdf = (
        f"quality_report_{report.title.lower()}_{report.end_date.strftime('%Y_%m_%d')}.pdf"
    )
    pdf = makepdf(report.html)
    s3_path = f"quality_reports/{report.title}/{filename_pdf}"
    upload_to_s3(s3_path, pdf)
    return report


def generate_all_reports(start_date: datetime = None):
    """
    Generates quality reports for all areas and teams with bugs updated since start_date
    """
    date_now = datetime.now()
    if start_date is None:
        start_date = date_now - timedelta(days=_DEFAULT_REPORT_WINDOW_DAYS)

    # Ensure directory for graphs exists
    if not os.path.exists(QUALITY_REPORT_PLOTS_DIRECTORY):
        os.mkdir(QUALITY_REPORT_PLOTS_DIRECTORY)

    # Scans for issues updates since start_date and filters for parents of each duplicate graph
    jira_issues = search_for_issues(start_date, date_now)
    format_issue_text(jira_issues)
    parent_issues, key_to_issue = resolve_duplicate_graphs(jira_issues)

    for area, TEAM_TO_FEATURES in JIRA_FEATURES.items():
        if area in ["None"]:
            continue

        team_reports = {}
        for team, features in TEAM_TO_FEATURES.items():
            if team in ["Many", "None"]:
                continue
            if len(features) == 0:
                continue
            report = QualityReportTeam(date_now, parent_issues, key_to_issue, start_date, team)
            generate_and_save_pdf(report)
            team_reports[team] = report

        area_report = QualityReportArea(
            date_now, parent_issues, key_to_issue, start_date, area, team_reports
        )
        generate_and_save_pdf(area_report)
    shutil.rmtree(QUALITY_REPORT_PLOTS_DIRECTORY)

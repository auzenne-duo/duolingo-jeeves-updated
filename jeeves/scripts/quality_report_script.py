import os
import shutil
from datetime import datetime, timedelta
from typing import Dict, List, Set, Tuple

from pydyf import PDF
from weasyprint import CSS, HTML
from weasyprint.text.fonts import FontConfiguration

from jeeves import registry as app_registry
from jeeves.config.config import JIRA_ISSUE_TYPE_BUG, JIRA_PROJECTS, QUALITY_REPORT_PLOTS_DIRECTORY
from jeeves.config.jira_features import JIRA_FEATURES
from jeeves.dal.jira_dal import JiraDAL
from jeeves.lib.identifier_manager_mapping import IDManagerMap
from jeeves.lib.send_quality_report_emails import send_email
from jeeves.manager.duplicate_graph_resolver import DuplicateGraphResolver
from jeeves.manager.jira_manager import JiraManager
from jeeves.model.jira_document import JiraDocument
from jeeves.model.quality_report import QualityReport, QualityReportArea, QualityReportTeam
from jeeves.model.quality_report_issue import QualityReportIssue
from jeeves.util.date_util import date_to_str
from jeeves.util.quality_report_util import is_jira_issue_resolved
from jeeves.util.s3_client_and_bucket import upload_to_internal_static, upload_to_jeeves_s3

_CSS_FILENAME = "templates/quality_report/quality_report.css"
_DEFAULT_REPORT_WINDOW_DAYS = 90

_INTERNAL_STATIC_PREFIX = "https://internal-static.duolingo.com"
_MIN_BUGS_THRESHOLD = 20
_TEAMS_TO_EXCLUDE = ["Grading", "Speaking", "Speech Lab"]


def search_for_issues(start_date: datetime) -> List[JiraDocument]:
    """
    Yields bugs that have been updated since the start date

    Params:
        start_date (datetime): only consider issues with updated after this datetime

    Returns:
        List of JiraDocuments
    """
    # Need to get the feature field key so that field is set in Jira documents
    JiraManager.get_feature_field()

    max_results_per_page = 100
    start_timestamp = date_to_str(start_date)
    projects_fetch_string = (
        f"project IN ({','.join(JIRA_PROJECTS)}) "
        + f"AND updated >= {start_timestamp} "
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
        issues.append(JiraDocument.deserialize_from_external_json(issue))
        if i % 500 == 0:
            print(f"Paginating jira issues; at {i}")
    return issues


def resolve_duplicate_graphs(
    jira_issues: List[JiraDocument],
) -> Tuple[Set[str], Dict[str, JiraDocument]]:
    """
    Params:
        jira_issues: list of JiraDocuments

    Returns:
        A tuple of
            a set of jira issue keys with only one representative issue from each duplicate graph.
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
        visited_issues.update(duplicate_graph.issue_keys_to_documents.keys())
        parent_issues = [
            issue for issue in duplicate_graph_issues if JiraDocument.is_group_parent(issue)
        ]

        if len(parent_issues) == 1:
            parent_issue_key = parent_issues[0].issue_key
        elif len(parent_issues) > 1:
            # Originally we would call resolve_multiple_parent_issues(parent_issues), but that would close
            # issues that people were actively working on.
            for parent_issue in parent_issues:
                if not is_jira_issue_resolved(issue):
                    parent_issue_key = parent_issue.issue_key
                    break
            else:
                parent_issue_key = parent_issues[0].issue_key
        elif len(duplicate_graph_issues) == 1:
            parent_issue_key = issue.issue_key
        else:
            open_issues = [
                issue for issue in duplicate_graph_issues if not is_jira_issue_resolved(issue)
            ]
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

    return parent_representatives, key_to_issue


def filter_dev_issues(
    issue_keys: List[str], key_to_issue: Dict[str, JiraDocument]
) -> List[JiraDocument]:
    """
    Filters out issues that are related to a development ticket, where a dev ticket
    is a non-bug ticket.

    Params:
        issue_keys: list of issue keys
        key_to_issue: mapping from issue key to JiraDocument

    Returns:
        list of JiraDocuments that are NOT related to a development ticket
    """
    issues_to_fetch = set()
    for issue_key in issue_keys:
        jira_doc = key_to_issue[issue_key]
        for link in jira_doc.issue_links:
            if "Relates" in link["type"]["name"]:
                if "inwardIssue" in link:
                    issues_to_fetch.add(link["inwardIssue"]["key"])
                if "outwardIssue" in link:
                    issues_to_fetch.add(link["outwardIssue"]["key"])

    downloaded_issues = IDManagerMap.get_manager_for_identifier(
        "JIRA"
    ).download_bulk_issues_with_features(list(issues_to_fetch))
    key_to_issue.update({issue.issue_key: issue for issue in downloaded_issues})

    filtered_jira_docs = []
    for issue_key in issue_keys:
        jira_doc = key_to_issue[issue_key]
        is_dev_issue = False
        for link in jira_doc.issue_links:
            if "Relates" in link["type"]["name"]:
                if "inwardIssue" in link:
                    issue = key_to_issue.get(link["inwardIssue"]["key"], None)
                if "outwardIssue" in link:
                    issue = key_to_issue.get(link["outwardIssue"]["key"], None)
                if issue is None:
                    print("missing linked issue", link)
                    continue
                if issue.issue_type != "Bug":
                    is_dev_issue = True
                    break
        if not is_dev_issue:
            filtered_jira_docs.append(jira_doc)
    return filtered_jira_docs


def makepdf(html: str) -> PDF:
    """Generate a PDF file from a string of HTML."""
    font_config = FontConfiguration()
    htmldoc = HTML(string=html, base_url="")
    css = CSS(_CSS_FILENAME, font_config=font_config)

    return htmldoc.write_pdf(stylesheets=[css], font_config=font_config)


def generate_and_save_pdf(
    report: QualityReport,
    dry_run: bool = True,
    send_emails: bool = False,
) -> None:
    """
    Generates a pdf using html of quality report and saves as a pdf in s3
    """
    filename_pdf = (
        f"quality_report_{report.title.lower()}_{report.end_date.strftime('%Y_%m_%d')}.pdf"
    )
    pdf = makepdf(report.html)

    s3_path = f"quality_reports/{report.title}/{filename_pdf}"
    internal_static_s3_path = f"delight/{s3_path}"
    report.internal_static_link = f"{_INTERNAL_STATIC_PREFIX}/{internal_static_s3_path}"

    if send_emails:
        send_email(report)
    if dry_run:
        print(report.title, report.overall_score)
        return report
    upload_to_internal_static(internal_static_s3_path, pdf)
    upload_to_jeeves_s3(s3_path, pdf)

    return report


def generate_all_reports(
    start_date: datetime = None,
    dry_run: bool = True,
    send_emails: bool = False,
    send_area_emails: bool = False,
):
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
    jira_issues = search_for_issues(start_date)
    parent_keys, key_to_issue = resolve_duplicate_graphs(jira_issues)
    parent_representatives = filter_dev_issues(parent_keys, key_to_issue)
    # convert issues to quality report issues for ease of serialization and calculation of priority score
    key_to_issue = {issue.issue_key: QualityReportIssue(issue) for issue in key_to_issue.values()}
    parent_issues = [key_to_issue[jira_doc.issue_key] for jira_doc in parent_representatives]

    for area, TEAM_TO_FEATURES in JIRA_FEATURES.items():
        if area in ["Many", "None"]:
            continue
        team_reports = {}
        for team, features in TEAM_TO_FEATURES.items():
            if team in ["Many", "None"] + _TEAMS_TO_EXCLUDE:
                continue
            if len(features) == 0:
                continue
            report = QualityReportTeam(
                date_now, parent_issues, key_to_issue, start_date, team, dry_run=dry_run
            )
            # Don't create reports for teams with too few bugs
            if len(report.issues) < _MIN_BUGS_THRESHOLD:
                continue
            generate_and_save_pdf(report, dry_run=dry_run, send_emails=send_emails)
            team_reports[team] = report

        area_report = QualityReportArea(
            date_now, parent_issues, key_to_issue, start_date, area, team_reports, dry_run=dry_run
        )
        generate_and_save_pdf(area_report, dry_run=dry_run, send_emails=send_area_emails)

    # Create overall report with all issues
    overall_report = QualityReport(
        date_now,
        None,
        parent_issues,
        key_to_issue,
        start_date,
        "All Issues",
        monthly=False,
        dry_run=dry_run,
    )
    generate_and_save_pdf(overall_report, dry_run=dry_run, send_emails=send_emails)
    # clean up plots directory
    shutil.rmtree(QUALITY_REPORT_PLOTS_DIRECTORY)

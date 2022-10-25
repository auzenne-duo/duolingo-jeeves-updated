import json
import os
from collections import Counter, defaultdict
from datetime import datetime
from enum import Enum, auto
from typing import Dict, List, Optional, Tuple

import markdown
import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import seaborn as sns
from duolingo_base.config import Config
from duolingo_base.dal import s3
from weasyprint import CSS, HTML
from weasyprint.text.fonts import FontConfiguration

from jeeves.config.config import JIRA_ISSUE_TYPE_BUG, JIRA_PROJECTS
from jeeves.config.jira_features import JIRA_FEATURES
from jeeves.dal.jira_dal import JiraDAL
from jeeves.manager.jira_manager import JiraManager
from jeeves.model.jira_document import JiraDocument
from jeeves.util.date_util import date_to_str, str_to_date
from jeeves.util.quality_report_priority import QualityReportPriority, get_quality_report_priority

_config = Config.load_config()

AREA_TO_FEATURES = {
    area: {feature for _, features in teams.items() for feature in features}
    for area, teams in JIRA_FEATURES.items()
}
DONE_STATUSES = ["Closed", "Merged", "Done"]
INVALID_SCREENS = [None, "", "none"]
MAX_BUG_SCREENS = 5
SCREEN_BUG_NUMBER_THRESHOLD = 0
CSS_FILENAME = "templates/quality_report/quality_report.css"


class IssueStatus(Enum):
    OPEN = auto()
    CLOSED = auto()


def populate_priority_and_is_done(jira_doc: JiraDocument) -> None:
    """
    Populates the priority and is_done fields
    """
    jira_doc.priority = get_quality_report_priority(jira_doc.priority, jira_doc.labels)
    jira_doc.is_done = jira_doc.status in DONE_STATUSES


def search_for_area_issues(
    area: str, start_date: datetime, end_date: datetime
) -> List[JiraDocument]:
    """
    Yields issues for the specific area within start_date to end_date inclusively

    Params:
        area (str): area such as "Growth", see JIRA_FEATURES for area names
        start_date (datetime): only consider issues with updated after this datetime
        end_date (datetime): only consider issues with updated before this datetime

    Returns:
        List of JiraDocuments
    """
    feature_field = JiraManager.get_feature_field()
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
        if area == "All Issues" or (
            issue["fields"][feature_field]
            and issue["fields"][feature_field]["value"] in AREA_TO_FEATURES[area]
        ):
            jira_doc = JiraDocument.deserialize_from_external_json(issue)
            # convert priority to a QualityReportPriority object for ease of score calculation
            populate_priority_and_is_done(jira_doc)
            issues.append(jira_doc)
        if i % 500 == 0:
            print(f"Paginating jira issues; at {i}")
    return issues


def fetch_duplicate_jira_issues(jira_issues: List[JiraDocument]) -> Dict[str, JiraDocument]:
    """
    Gets jira document for any duplicates of the jira issues, including those outside of the time frame.
    """
    seen_issues = {issue.issue_key for issue in jira_issues}
    issues_to_fetch = set()
    for issue in jira_issues:
        for dupe_key in issue.linked_duplicate_keys:
            if not dupe_key in seen_issues:
                issues_to_fetch.add(dupe_key)
    fetched_issues = {}
    for jira_doc in JiraDAL.get_bulk_issues(list(issues_to_fetch)):
        populate_priority_and_is_done(jira_doc)
        fetched_issues[jira_doc.issue_key] = jira_doc
    return fetched_issues


def filter_for_unique_project_issues(
    jira_issues: List[JiraDocument], duplicate_issues: Dict[str, JiraDocument], project: str = None
) -> Tuple[List[JiraDocument], Dict[str, JiraDocument]]:
    """
    Filters jira issues for only unique issues and one representative of any group of duplicates.
    Only includes issues that are of the specified project (e.g. DLAA)
    If an issue has duplicates, we consider it done if any duplicate is done and take the highest priority of any duplicate

    Params:
        jira_issues: list of jira documents
        project: string such as DLAI
        duplicate_issues: mapping of jira key to jira document for duplicates of any jira doc in jire_issues

    Reutrns:
        list of jira documents
        dict mapping of jira issue keys where issue is open but has a closed duplicate
            Note: this can lead to unexpected behavior because duplicate graphs are not fully connected
                  therefore an issue could be marked as open because it's indirect duplicates are not seen.
                  However, this leads to an issue getting more attention than it deserves, which is fine.
    """
    if project:
        project_jira_issues = [issue for issue in jira_issues if issue.project == project]
    else:
        project_jira_issues = jira_issues
    keys_in_time_frame = {issue.issue_key for issue in jira_issues}
    key_to_issue = {issue.issue_key: issue for issue in jira_issues}
    key_to_issue.update(duplicate_issues)
    seen_issues = set()
    filtered_issues = []
    open_issues_with_closed_dupes = {}
    for issue in project_jira_issues:
        if issue.issue_key in seen_issues:
            continue
        open_dupes = {}
        if not issue.is_done:
            open_dupes[issue.issue_key] = issue
        for dupe_key in issue.linked_duplicate_keys:
            if not dupe_key in key_to_issue:
                continue
            dupe_issue = key_to_issue[dupe_key]
            seen_issues.add(dupe_key)
            if not dupe_issue.is_done and dupe_issue.issue_key in keys_in_time_frame:
                open_dupes[dupe_issue.issue_key] = dupe_issue
            issue.is_done = issue.is_done or dupe_issue.is_done
            issue.priority = max(issue.priority, dupe_issue.priority)
        filtered_issues.append(issue)
        if issue.is_done:
            open_issues_with_closed_dupes.update(open_dupes)
    return filtered_issues, open_issues_with_closed_dupes


def calculate_max_priority_issues(
    open_jira_issues: List[JiraDocument],
) -> List[JiraDocument]:
    """
    Return the maximum priority issues of the open issues as a list of issues with the highest priority (multiple if tied)

    Params:
        open_jira_issues: list of jira documents with the priority replaced by a QualityReportPriority object all of which have is_done attr as False
    """
    max_priority = max([issue.priority for issue in open_jira_issues])
    max_priority_issues = [issue for issue in open_jira_issues if issue.priority == max_priority]
    return max_priority_issues


def create_status_priority_count(
    jira_issues: List[JiraDocument],
) -> Dict[IssueStatus, Dict[QualityReportPriority, int]]:
    """
    Creates a dictionary mapping a issue_status to mapping of QualityReportPriority to count of issues

    Params:
        jira_issues: list of jira documents with the priority replaced by a QualityReportPriority object
    """
    status_priority_count = {IssueStatus.OPEN: Counter(), IssueStatus.CLOSED: Counter()}
    for issue in jira_issues:
        status = IssueStatus.CLOSED if issue.is_done else IssueStatus.OPEN
        status_priority_count[status][issue.priority] += 1
    return status_priority_count


def calculate_scores(priority_count: Dict[QualityReportPriority, int]) -> Tuple[float, int, int]:
    """
    Creates a score as weighted percentage of closed issues

    Params
        status_priority_count: dictionary mapping a priority to count of issues

    Returns a score as percentage of closed issues, the weighted score of open issues, and the weighted score of closed issues
    """
    open_score = sum(
        [priority.score * count for priority, count in priority_count[IssueStatus.OPEN].items()]
    )
    closed_score = sum(
        [priority.score * count for priority, count in priority_count[IssueStatus.CLOSED].items()]
    )
    if open_score + closed_score == 0:
        return None, open_score, closed_score
    else:
        score = round(closed_score / (open_score + closed_score) * 100)
    return score, open_score, closed_score


def create_priority_group_text(priority_count: Dict[QualityReportPriority, int]) -> str:
    """
    Returns formatted text about the worst issues in terms of most duplicates and highest priority

    Params
        priority_count: dictionary mapping priority to count of issues

    Returns str detailing the how many issues are of status for different priorities
    """
    sorted_priority_counts = sorted(
        [(priority, count) for priority, count in priority_count.items()],
        key=lambda x: x[0],
        reverse=True,
    )
    return "\n".join(
        [
            f"    - {priority.text}: {count} issues * {priority.score} points => {count*priority.score}"
            for priority, count in sorted_priority_counts
        ]
    )


def create_worst_issues_text(
    max_priority_issues: List[JiraDocument],
    max_dupes_issue: JiraDocument,
) -> str:
    """
    Returns formatted text about the worst issues in terms of most duplicates and highest priority

    Params
        max_priority_issues: list of JiraDocuments with the max_priority
        max_dupes_issue: JiraDocument with the most duplicates

    Returns str detailing the issues with most reports and the highest priority issues
    """
    max_priority_issues = "\n".join(
        [
            f"    - [{issue.issue_key}](https://duolingo.atlassian.net/browse/{issue.issue_key}): {issue.header_text} - {issue.priority}"
            for issue in max_priority_issues
        ]
    )
    num_dupes = len(max_dupes_issue.linked_duplicate_keys)
    if num_dupes == 0:
        max_dupes_text = ""
    else:
        max_dupes_text = f"* <span class='bold'>Most reports:</span>\n    - [{max_dupes_issue.issue_key}](https://duolingo.atlassian.net/browse/{max_dupes_issue.issue_key}): {max_dupes_issue.header_text} - {max_dupes_issue.priority} with {num_dupes} duplicate report{'s' if num_dupes>1 else ''}"

    return f"""

{max_dupes_text}
* <span class="bold">Most likely to block learners:</span>
{max_priority_issues}
"""


def get_s3_bucket_and_client():
    """
    Returns the s3 bucket and s3 client
    """
    if _config.get_nested(["s3_document_cache", "endpoint_url"]):
        s3_client = s3.S3Client(_config.get_nested(["s3_document_cache", "endpoint_url"]))
    else:
        s3_client = s3.S3Client()
    s3_bucket_name = _config.get_nested(["s3_document_cache", "bucket_name"])
    return s3_bucket_name, s3_client


def upload_to_s3(filename, data):
    """
    Uploads data to s3 under filename
    """
    s3_bucket_name, s3_client = get_s3_bucket_and_client()
    s3_client.upload(s3_bucket_name, filename, data)


def upload_quality_scores_to_s3(
    area: str,
    end_date_str: str,
    scores: Dict[str, int],
):
    """
    Uploads quality report scores to s3

    Params:
        area: str such as "Growth"
        end_date_str: str such as "2022-09-01"
        scores: dictionary of the format {"DLAA": 56, ...} include Overall, DLAA, DLAI, DLAW
    """
    score_data = {"area": area, "end_date": end_date_str, "scores": scores}
    upload_to_s3(
        f"quality_report_scores/{area}/quality_score_{area}_{end_date_str}", json.dumps(score_data)
    )


def get_past_quality_scores(area: str) -> Dict[str, List[Tuple[datetime, int]]]:
    """
    gets the past quality scores for each project and Overall

    params:
        area: str such as "Growth"

    returns:
        dictionary of the following structure (where score is an int and date is a str such as "2022-09-09"):
            "Overall": [(date, score)...]
            "DLAA": [...]
            "DLAI": [...]
            "DLAA": [...]
    """
    scores = defaultdict(list)
    s3_bucket_name, s3_client = get_s3_bucket_and_client()
    for s3_file in s3_client.yield_filenames(
        s3_bucket_name, path_prefix=f"quality_report_scores/{area}"
    ):
        data = json.loads(s3_client.download(s3_bucket_name, s3_file))
        for project, score in data["scores"].items():
            scores[project].append((str_to_date(data["end_date"]), score))
    return scores


def create_plot(
    project_to_scores: Dict[str, List[Tuple[datetime, int]]], title: str, legend: bool = False
) -> str:
    """
    Given a list of date/score tuples, creates a plot, saves it, and returns the filename

    params:
        scores: list of date/score tuples

    returns: filename as a string
    """

    juicy_owl = "#58CC02"
    juicy_macaw = "#1CB0F6"
    juicy_beetle = "#CE82FF"
    juicy_narwhal = "#1453A3"
    juicy_butterfly = "#6F4EA1"
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
            "axes.labelcolor": "#4B4B4B",
            "axes.spines.right": False,
            "axes.spines.top": False,
            "figure.facecolor": "white",
            "lines.solid_capstyle": "round",
            "patch.edgecolor": "w",
            "patch.force_edgecolor": True,
            "text.color": "#4B4B4B",
            "xtick.bottom": True,
            "xtick.color": "#4B4B4B",
            "xtick.direction": "out",
            "xtick.top": False,
            "ytick.color": "#4B4B4B",
            "ytick.direction": "out",
            "ytick.left": False,
            "ytick.right": False,
        },
    )
    sns.set_context("notebook", rc={"font.size": 25, "axes.titlesize": 25, "axes.labelsize": 25})

    plt.figure()

    plt.ylim([0, 105])
    plt.xlim([datetime(2022, 9, 1), datetime(2022, 12, 1)])
    for y in range(20, 120, 20):
        plt.plot(
            [datetime(2022, x, 1) for x in range(9, 13)],
            [y] * 4,
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

    filename = f"{title}.png"
    plt.savefig(filename, bbox_inches="tight")
    return filename


def makepdf(html):
    """Generate a PDF file from a string of HTML."""
    font_config = FontConfiguration()
    htmldoc = HTML(string=html, base_url="")
    css = CSS(CSS_FILENAME, font_config=font_config)

    return htmldoc.write_pdf(stylesheets=[css], font_config=font_config)


def create_project_text(
    project: str,
    project_quality_plot: str,
    score: int,
    open_score: int,
    closed_score: int,
    status_priority_count: Dict[QualityReportPriority, Dict],
    worst_issues_text: str,
    issue_screens: str,
) -> str:
    return f"""
<div style="page-break-after: always;"></div>

## Project: {project}
<h4 style='text-align: center;'>{project} Quality Scores</h4>
![plot]({project_quality_plot})

### Quality score: {score}

* <span class="bold">Open issues: {open_score} points</span>
{create_priority_group_text(status_priority_count[IssueStatus.OPEN])}
* <span class="bold">Closed issues: {closed_score} points</span>
{create_priority_group_text(status_priority_count[IssueStatus.CLOSED])}

### Worst open issues:

{worst_issues_text if worst_issues_text else "No open issues"}

### Screens with the most issues (open or closed):
{issue_screens if issue_screens else "No screen data available"}
"""


def create_open_issues_with_closed_dupes_text(
    project_issues: Dict[str, Dict[str, JiraDocument]]
) -> str:
    text = """<div style='page-break-after: always;'></div>
## Open Issues with Closed Duplicates
These are issues that have at least one duplicate marked as 'Fixed' or 'Done'. They are considered a closed issue for this report, but we encourage you to close out all duplicates if that issue has been resolved."""
    for project, issues in project_issues.items():
        issue_text = "\n".join(
            [
                f"- [{issue.issue_key}](https://duolingo.atlassian.net/browse/{issue.issue_key}): {issue.header_text}"
                for _, issue in issues.items()
            ]
        )
        if issue_text:
            text += f"\n### {project}\n{issue_text}"
    return text


def create_appendix_text(features: List[str]) -> str:
    return f"""

<div style="page-break-after: always;"></div>

## Appendix

### Features

This report was compiled using issues with features:

{', '.join(sorted(features))}
"""


def generate_report(area: Optional[str], start_date: datetime) -> str:
    """
    Generates a quality report for a specific area using qualitys from start_date to end_date

    Params:
        area: str of an area such as "Growth", or None if should use all issues
        start_date: datetime for the beginning of the range of qualitys (inclusive)
        end_date: datetime for the end of the range of qualitys (inclusive)

    Returns a filename to an html file with the quality report
    """
    date_now = datetime.now()
    if area is None:
        area = "All Issues"
    jira_issues = search_for_area_issues(area, start_date, date_now)
    duplicate_keys_to_issues = fetch_duplicate_jira_issues(jira_issues)
    unique_jira_issues, _ = filter_for_unique_project_issues(jira_issues, duplicate_keys_to_issues)

    priority_count = create_status_priority_count(unique_jira_issues)
    overall_score, _, _ = calculate_scores(priority_count)
    features = AREA_TO_FEATURES.get(area, ["No specific features used"])
    report = f"""
# {area} Quality Report <br/> {date_now.strftime("%b %d, %Y")}
### Summary
* Overall Quality Score = 100*closed score / total score: <span class="highlight-owl">{overall_score}</span>
* Scores calculated from issues updated between: {start_date.strftime("%b %d, %Y")} - {date_now.strftime("%b %d, %Y")}

"""
    project_scores = {}
    project_data = defaultdict()
    project_open_issues_with_closed_dupes = {}
    for project in JIRA_PROJECTS:
        project_jira_issues, open_issues_with_closed_dupes = filter_for_unique_project_issues(
            jira_issues, duplicate_keys_to_issues, project
        )
        project_open_issues_with_closed_dupes[project] = open_issues_with_closed_dupes
        status_priority_count = create_status_priority_count(project_jira_issues)
        score, open_score, closed_score = calculate_scores(status_priority_count)
        project_data[project] = [project_jira_issues, status_priority_count]
        if not score is None:
            project_scores[project] = score
    project_scores.update({"Overall": overall_score})
    upload_quality_scores_to_s3(area, date_to_str(date_now), project_scores)
    scores = get_past_quality_scores(area)
    quality_plot = create_plot(scores, "Overall", legend=True)
    plot_filenames = [quality_plot]
    report += (
        f"<h4 style='text-align: center;'>Overall Quality Scores</h4>\n![plot]({quality_plot})"
    )

    project_reports = []
    for project in JIRA_PROJECTS:
        project_jira_issues, status_priority_count = project_data[project]
        score, open_score, closed_score = calculate_scores(status_priority_count)
        project_scores[project] = score

        if not project_jira_issues:
            project_reports.append(
                (
                    100,
                    f"\n<div style='page-break-after: always;'></div>\n##Project: {project}\n\n### No issues",
                )
            )
            continue

        screen_count = Counter()
        for issue in project_jira_issues:
            if issue.project == "DLAA":
                screen = issue.screen_content.split(".")[-1]
            elif issue.project == "DLAW":
                screen = issue.screen_content.split(".com")[-1]
            else:
                screen = issue.screen_content
            screen_count[screen] += 1
        screen_count = sorted(
            [(screen, count) for screen, count in screen_count.items() if screen],
            key=lambda x: -x[1],
        )
        issue_screens = "\n".join(
            [
                f"- {screen}: {count}"
                for screen, count in screen_count[:MAX_BUG_SCREENS]
                if count > SCREEN_BUG_NUMBER_THRESHOLD
            ]
        )

        open_jira_issues = [issue for issue in project_jira_issues if not issue.is_done]
        if open_jira_issues:
            max_priority_issues = calculate_max_priority_issues(open_jira_issues)
            # break max dupe ties using priority rank
            max_dupes_issue = max(
                open_jira_issues,
                key=lambda issue: len(issue.linked_duplicate_keys) + 0.01 * issue.priority.rank,
            )

            worst_issues_text = create_worst_issues_text(max_priority_issues, max_dupes_issue)
        else:
            worst_issues_text = "No open issues."
        project_quality_plot = create_plot({project: scores[project]}, project)
        plot_filenames.append(project_quality_plot)
        project_reports.append(
            (
                score,
                create_project_text(
                    project,
                    project_quality_plot,
                    score,
                    open_score,
                    closed_score,
                    status_priority_count,
                    worst_issues_text,
                    issue_screens,
                ),
            )
        )
    project_reports.sort(key=lambda x: x[0])
    if project_reports:
        report += "\n".join([project_report for _, project_report in project_reports])
    report += create_open_issues_with_closed_dupes_text(project_open_issues_with_closed_dupes)
    report += create_appendix_text(features)
    html = markdown.markdown(report, extensions=["footnotes"])
    filename_pdf = f"quality_report_{area.lower()}_{date_now.strftime('%Y_%m_%d')}.pdf"
    pdf = makepdf(html)
    s3_path = f"quality_reports/{area}/{filename_pdf}"
    upload_to_s3(s3_path, pdf)
    # clean up by deleting png files for plots
    for filename in plot_filenames:
        os.remove(filename)
    return s3_path

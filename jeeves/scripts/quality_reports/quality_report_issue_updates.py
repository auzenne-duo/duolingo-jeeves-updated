import json
from datetime import datetime, timedelta
from typing import List

import pytz

from jeeves import registry as app_registry
from jeeves.config.jira_features import JIRA_FEATURES
from jeeves.dal.jira_dal import JiraDAL
from jeeves.dal.quality_report_dal import QualityReportDAL
from jeeves.model.jira_document import JiraDocument
from jeeves.util.date_util import date_to_str, parse_external_datetime
from jeeves.util.s3_client_and_bucket import upload_to_jeeves_s3


def check_issue_updates(jira_keys: List[str], since_date: datetime = None):
    """
    Check if jira issues surfaced in the previous week have been updated

    Params:
        jira_keys: list of jira keys to check for updates
    """
    # fetch the issues from jira including the changelog and then check if updates have been made within the last week
    max_results_per_page = 100
    projects_fetch_string = f"key IN ({','.join(jira_keys)})"

    url_params = {
        "fields": "*all",
        "maxResults": max_results_per_page,
        "startAt": 0,
        "jql": projects_fetch_string,
        "expand": "changelog",
    }

    if since_date is None:
        since_date = datetime.now(pytz.utc) - timedelta(days=7)
    updated_issues = set()
    update_actions = {}
    jira_docs = []
    for issue in JiraDAL.paginate_search_issues(url_params):
        jira_doc = JiraDocument.deserialize_from_external_json(issue)
        jira_docs.append(jira_doc)
        issue_key = issue["key"]
        update_actions[issue_key] = []
        for history in issue["changelog"]["histories"]:
            if parse_external_datetime(history["created"]) > since_date:
                updated_issues.add(issue_key)
                for item in history["items"]:
                    update_actions[issue_key].append(item["field"])
            else:
                break

    return updated_issues, update_actions


def check_quality_report_updates(since_date: datetime = None):
    """
    Calculates the number of issues updated since the last quality report.
    Then uploads the results to s3 in the following format:
    {
        "date": "2021-09-09",
        "since_date": "2021-09-02",
        "stats": {
            "Path": {
                "score": 0.5,
                "num_issues": 2,
                "update_actions": {
                }
            }
        }
    }

    Params:
        since_date: date to check for updates since. If None, defaults to 7 days ago
                    the earliest report from before then will be used to check for updates

    """
    team_to_stats = {}
    for _, TEAM_TO_FEATURES in JIRA_FEATURES.items():
        for team in TEAM_TO_FEATURES:
            issue_datasets = app_registry(QualityReportDAL).get_past_quality_issue_datasets(team)
            if issue_datasets == []:
                print(team, "no data")
                continue
            index = -1
            if since_date:
                for i in range(len(issue_datasets) - 1, -1, -1):
                    report_date = issue_datasets[i].date
                    if report_date <= since_date:
                        index = i
                        break
            issue_data = issue_datasets[index]
            issue_keys = issue_data.max_priority_issue_keys + issue_data.max_dupes_issue_keys
            if issue_keys:
                updated_issues, update_actions = check_issue_updates(issue_keys, issue_data.date)
                score = len(updated_issues) / len(issue_keys)
                team_to_stats[team] = {
                    "score": score,
                    "num_issues": len(issue_keys),
                    "update_actions": update_actions,
                }

    date_now = date_to_str(datetime.now())
    upload_to_jeeves_s3(
        f"quality_report_metrics/quality_report_updates_{date_now}",
        json.dumps(
            {"stats": team_to_stats, "date": date_now, "since_date": date_to_str(since_date)}
        ),
    )

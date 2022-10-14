import json
import sys
from datetime import datetime, timedelta
from typing import Dict

import rollbar

from jeeves import apply_registry, close_registry
from jeeves.dal.jira_dal import JiraDAL
from jeeves.manager.jira_manager import JIRA_ISSUE_TYPE_BUG, JIRA_PROJECTS, JiraManager
from jeeves.model.jira_document import JiraDocument
from jeeves.util.date_util import date_to_str
from jeeves.util.priority_estimator import PRIORITY_STR_TO_INT, PriorityEstimator
from jeeves.util.s3_client_and_bucket import get_s3_client_and_bucket

OVERRIDDEN_PRIORITIES_FILENAME = "overridden_priorities"
PRIORITY_ESTIMATOR_START_DATE = "2022-09-22"
s3_client, s3_bucket_name = get_s3_client_and_bucket()


def get_s3_overridden_priorities():
    """
    Loads in a dictionary of stored manually overridden priorities

    returns dictionary of the format {
        issue_key: {
            summary: str
            feature: str
            reporter: str
            priority: str
            date_stored: str
        }
    }
    """
    return json.loads(s3_client.download(s3_bucket_name, OVERRIDDEN_PRIORITIES_FILENAME))


def upload_s3_overridden_priorities(overridden_priorities: Dict[str, Dict[str, str]]):
    """
    Uploads a dictionary of stored manually overridden priorities
    """
    s3_client.upload(
        s3_bucket_name, OVERRIDDEN_PRIORITIES_FILENAME, json.dumps(overridden_priorities)
    )


def get_updated_jira_priorities(
    earliest_date: datetime,
    current_date: datetime,
    overridden_priorities: Dict[str, Dict[str, str]],
) -> Dict[str, Dict[str, str]]:
    """
    Paginates through Jira tickets updated since earliest_date
        checks history to see if a user has changed the priority
        filters for issues not already in the overridden priorities dictionary (overwr)

    Params:
        earliest_date: filter for issues updated after this date
        current_date: the current date when this issues are being checked (used to annotate)
        overridden_priorities: priorities already stored in s3
    """
    max_results_per_page = 100
    projects_fetch_string = (
        f"project IN ({','.join(JIRA_PROJECTS)}) "
        + f"AND updated >= {date_to_str(earliest_date)} "
        + f"AND created >= {PRIORITY_ESTIMATOR_START_DATE} "
        + f"AND issueType = {JIRA_ISSUE_TYPE_BUG} "
        + f"ORDER BY updated desc"
    )

    url_params = {
        "fields": "*all",
        "maxResults": max_results_per_page,
        "startAt": 0,
        "jql": projects_fetch_string,
        "expand": "changelog",
    }

    updated_priorities = {}
    JiraManager.get_feature_field()
    for i, issue in enumerate(JiraDAL.paginate_search_issues(url_params)):
        issue_key = issue["key"]
        skip = False
        for history in issue["changelog"]["histories"]:
            for item in history["items"]:
                if item["field"] == "priority" and item["fromString"] != item["toString"]:
                    skip = True
                    if (
                        issue_key in overridden_priorities
                        and overridden_priorities[issue_key]["priority"] == item["toString"]
                    ):
                        break
                    if history["author"]["displayName"] in [
                        "Automation for Jira",
                        "Jira Automation",
                    ]:
                        break
                    if not item["toString"] in PRIORITY_STR_TO_INT:
                        print(f"issue {issue_key} has priority {item['toString']}")
                        break
                    jira_doc = JiraDocument.deserialize_from_external_json(issue)
                    if "jira-automation" in jira_doc.reporter_email:
                        break

                    updated_priorities[issue_key] = {
                        "summary": jira_doc.header_text,
                        "feature": jira_doc.feature,
                        "reporter_email": PriorityEstimator.parse_reporter_email(
                            jira_doc.reporter_email
                        ),
                        "priority": item["toString"],
                        "date_stored": date_to_str(current_date),
                    }
                    break
            if skip:
                break
        if i % 100 == 0:
            print("at issue", i)
    return updated_priorities


def update_priority_model():
    """
    Finds overridden priorities, re-fits the priority estimator model, and uploads changes to s3
    """
    current_date = datetime.now()
    earliest_date = current_date - timedelta(weeks=2)
    overridden_priorities = get_s3_overridden_priorities()
    updated_priorities = get_updated_jira_priorities(
        earliest_date, current_date, overridden_priorities
    )
    # train model
    print(f"updating priority estimator with {len(updated_priorities)} overridden priorities")
    print(updated_priorities.keys())
    if len(updated_priorities) == 0:
        rollbar.report_message("No new overridden priorities found", "warning")
        return
    data, labels = zip(
        *[
            (
                f"{sample['summary']}; {sample['feature']}; {sample['reporter_email']}",
                PRIORITY_STR_TO_INT[sample["priority"]],
            )
            for sample in updated_priorities.values()
        ]
    )
    PriorityEstimator.fit_to_data(data, labels)
    overridden_priorities.update(updated_priorities)
    upload_s3_overridden_priorities(overridden_priorities)
    rollbar.report_message(
        f"priority model fit using {len(updated_priorities)} data points", "info"
    )


if __name__ == "__main__":
    try:
        apply_registry()
        print("running priority updater")
        update_priority_model()
    except:
        rollbar.report_exc_info(sys.exc_info())
    finally:
        close_registry()

import json
import os
import sys
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Optional

import rollbar
from duolingo_base.dal import s3

from jeeves import apply_registry, close_registry
from jeeves.config.config import (
    JIRA_ISSUE_TYPE_BUG,
    JIRA_PRIORITY_STR_TO_INT,
    JIRA_PROJECTS,
    PRIORITY_ESTIMATOR_S3_PATH,
)
from jeeves.dal.jira_dal import JiraDAL
from jeeves.manager.jira_manager import JiraManager
from jeeves.model.jira_document import JiraDocument
from jeeves.util.date_util import date_to_str
from jeeves.util.priority_estimator import PriorityEstimator
from jeeves.util.s3_client_and_bucket import get_s3_client_and_bucket

_AUTOMATION_DISPLAY_NAMES = [
    "Automation for Jira",
    "Jira Automation",
    "Android Shake Feedback",
    "iOS Shake Feedback",
]
_HOLDOUT_SET_THRESHOLD = 0.5
_HOLDOUT_SET_FILENAME = "holdout_set"
_OVERRIDDEN_PRIORITIES_FILENAME = "overridden_priorities"
_PRIORITY_ESTIMATOR_START_DATE = "2022-09-22"
_PRIORITY_ESTIMATOR_MODEL_PATH = os.environ.get("PRIORITY_ESTIMATOR_MODEL")
s3_client, s3_bucket_name = get_s3_client_and_bucket()


@dataclass
class OverriddenPriorityIssue:
    """
    Data about a Jira issue with manually overridden priority
    """

    issue_key: str
    summary: str
    feature: str
    reporter: str
    priority: str
    old_priority: Optional[str] = None
    date_stored: Optional[str] = None
    used_in_training: bool = True

    def serialize(self):
        return {""}


def get_s3_overridden_priorities() -> Dict[str, OverriddenPriorityIssue]:
    """
    Loads in and returns a mapping of Jira issue keys to manually overridden priorities stored in s3
    """
    return {
        key: OverriddenPriorityIssue(**value)
        for key, value in json.loads(
            s3_client.download(s3_bucket_name, _OVERRIDDEN_PRIORITIES_FILENAME)
        ).items()
    }


def upload_s3_overridden_priorities(overridden_priorities: Dict[str, OverriddenPriorityIssue]):
    """
    Uploads a mapping of Jira key to manually overridden priorities
    """
    s3_client.upload(
        s3_bucket_name,
        _OVERRIDDEN_PRIORITIES_FILENAME,
        json.dumps({key: asdict(item) for key, item in overridden_priorities.items()}),
    )


def get_updated_jira_priorities(
    earliest_date: datetime,
    current_date: datetime,
    overridden_priorities: Dict[str, OverriddenPriorityIssue],
) -> Dict[str, OverriddenPriorityIssue]:
    """
    Paginates through Jira tickets updated since earliest_date
        checks history to see if a user has changed the priority
        filters for issues not already in the overridden priorities dictionary

    Params:
        earliest_date: filter for issues updated after this date
        current_date: the current date when this issues are being checked (used to annotate)
        overridden_priorities: mapping of Jira key to already seen overridden priorities

    Returns a mapping of Jira key to newly overridden priorities as OverriddenPriorityIssue objects
    """
    max_results_per_page = 100
    projects_fetch_string = (
        f"project IN ({','.join(JIRA_PROJECTS)}) "
        + f"AND updated >= {date_to_str(earliest_date)} "
        + f"AND created >= {_PRIORITY_ESTIMATOR_START_DATE} "
        + f"AND issueType = {JIRA_ISSUE_TYPE_BUG} "
        + 'AND text ~ "shake-to-report"'
        + "ORDER BY updated desc"
    )

    url_params = {
        "fields": "*all",
        "maxResults": max_results_per_page,
        "startAt": 0,
        "jql": projects_fetch_string,
        "expand": "changelog",
    }

    new_overridden_priorities = {}
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
                        and overridden_priorities[issue_key].priority == item["toString"]
                    ):
                        break
                    if history["author"]["displayName"] in _AUTOMATION_DISPLAY_NAMES:
                        break
                    if item["toString"] not in JIRA_PRIORITY_STR_TO_INT:
                        print(f"issue {issue_key} has priority {item['toString']}")
                        break
                    jira_doc = JiraDocument.deserialize_from_external_json(issue)

                    new_overridden_priorities[issue_key] = OverriddenPriorityIssue(
                        issue_key,
                        jira_doc.header_text,
                        jira_doc.feature,
                        PriorityEstimator.parse_reporter_email(jira_doc.reporter_email),
                        item["toString"],
                        item["fromString"],
                        date_to_str(current_date),
                        used_in_training=False,
                    )
                    break
            if skip:
                break
        if i % 100 == 0:
            print("at issue", i)
    return new_overridden_priorities


def get_training_priorities(
    overridden_priorities: Dict[str, OverriddenPriorityIssue]
) -> Dict[str, OverriddenPriorityIssue]:
    """
    Finds new overridden priorities and combines them with old data that hasn't been trained on. Newest data is used in the even
    that a ticket has been updated more recently.
    """
    current_date = datetime.now()
    earliest_date = current_date - timedelta(weeks=2)
    training_data = {
        key: priority
        for key, priority in overridden_priorities.items()
        if not priority.used_in_training
    }
    new_overridden_priorities = get_updated_jira_priorities(
        earliest_date, current_date, overridden_priorities
    )
    training_data.update(new_overridden_priorities)
    return training_data


def update_priority_model(overridden_priorities) -> Dict[str, OverriddenPriorityIssue]:
    """
    Finds overridden priorities, re-fits the priority estimator model, and uploads changes to s3

    Returns mapping of Jira key to all overridden priorities including those already stored and those newly seen.
    The most recent override of a Jira issue takes precedence.
    """
    # train model
    training_priorities = get_training_priorities(overridden_priorities)
    print(f"updating priority estimator with {len(training_priorities)} overridden priorities")
    print(training_priorities.keys())
    if len(training_priorities) == 0:
        rollbar.report_message("No new overridden priorities found", "warning")
        return
    data, labels = zip(
        *[
            (
                f"{issue.summary}; {issue.feature}; {issue.reporter}",
                JIRA_PRIORITY_STR_TO_INT[issue.priority],
            )
            for issue in training_priorities.values()
        ]
    )
    PriorityEstimator.initialize_priority_estimator(force_init=True)
    PriorityEstimator.fit_to_data(data, labels)
    all_overridden_priorities = overridden_priorities.copy()
    all_overridden_priorities.update(training_priorities)
    return all_overridden_priorities


def upload_priority_model_and_data(
    overridden_priorities: Dict[str, OverriddenPriorityIssue]
) -> None:
    """
    Uploads overridden priorities and the updated model to s3

    Params:
        overridden_priorities: mapping of Jira issue key to OverriddenPriorityIssue object
    """
    print("uploading priority model")
    # mark the data as having been used in training
    for overridden_priority in overridden_priorities.values():
        overridden_priority.used_in_training = True
    upload_s3_overridden_priorities(overridden_priorities)
    for filepath in Path(_PRIORITY_ESTIMATOR_MODEL_PATH).iterdir():
        with filepath.open("rb") as f:
            s3_client.upload(
                s3_bucket_name, str(Path(PRIORITY_ESTIMATOR_S3_PATH) / filepath.name), f.read()
            )


def calculate_manual_override_score(
    end_date: Optional[datetime] = None, start_date: Optional[datetime] = None
) -> None:
    """
    Scores priority model based on how many priority ranks were changed between the predicted priority and the latest
    manually overridden priority and uploads score to s3
    Low to Medium counts as one rank, Low to High counts as two, etc.
    Only onsiders Jira tickets created between start and end date.

    Params
        end_date (datetime): end of the range of jira tickets to consider
        start_date (datetime): beginning of the range of jira tickets to consider
    """
    if end_date is None:
        end_date = datetime.now()
    if start_date is None:
        start_date = end_date - timedelta(days=14)

    max_results_per_page = 100
    projects_fetch_string = (
        f"project IN ({','.join(JIRA_PROJECTS)}) "
        + f"AND created >= {date_to_str(start_date)} "
        + f"AND created <= {date_to_str(end_date)} "
        + f"AND issueType = {JIRA_ISSUE_TYPE_BUG} "
        + 'AND text ~ "shake-to-report"'
        + "ORDER BY updated desc"
    )

    url_params = {
        "fields": "*all",
        "maxResults": max_results_per_page,
        "startAt": 0,
        "jql": projects_fetch_string,
        "expand": "changelog",
    }

    JiraManager.get_feature_field()
    rank_score = 0
    i = 0
    overridden_priorities = []
    for i, issue in enumerate(JiraDAL.paginate_search_issues(url_params)):
        issue_key = issue["key"]
        first_priority_change = None
        last_priority_change = None
        for history in issue["changelog"]["histories"]:
            for item in history["items"]:
                if item["field"] == "priority" and item["fromString"] != item["toString"]:
                    if history["author"]["displayName"] not in _AUTOMATION_DISPLAY_NAMES:
                        if last_priority_change is None:
                            last_priority_change = item
                        first_priority_change = item
                        break

        if first_priority_change is not None:
            new_priority = JIRA_PRIORITY_STR_TO_INT.get(last_priority_change["toString"])
            old_priority = JIRA_PRIORITY_STR_TO_INT.get(first_priority_change["fromString"])
            if (new_priority is not None) and (old_priority is not None):
                jira_doc = JiraDocument.deserialize_from_external_json(issue)
                overridden_priorities.append(
                    OverriddenPriorityIssue(
                        issue_key,
                        jira_doc.header_text,
                        jira_doc.feature,
                        PriorityEstimator.parse_reporter_email(jira_doc.reporter_email),
                        last_priority_change["toString"],
                        first_priority_change["fromString"],
                    )
                )
                rank_score += abs(old_priority - new_priority)
        if i % 100 == 0:
            print("at issue", i)

    output = {
        "score": rank_score / i,
        "total_issues": i,
        "overridden_priorities": {
            issue.issue_key: asdict(issue) for issue in overridden_priorities
        },
    }
    s3_client.upload(
        s3_bucket_name,
        f"priority_estimator_scores/score_{date_to_str(start_date)}_{date_to_str(end_date)}",
        json.dumps(output),
    )


def run_priority_model_holdout_set() -> float:
    """
    Evaluates the priority model on the holdout set stored in s3 and returns the percentage of correct predictions.
    Returns the ratio of correct predictions
    """
    holdout_set = json.loads(s3_client.download(s3_bucket_name, _HOLDOUT_SET_FILENAME))
    data, labels = zip(
        *[
            (
                f"{issue['summary']}; {issue['feature']}; {issue.get('reporter', '')}",
                int(issue["priority"]),
            )
            for issue in holdout_set.values()
        ]
    )
    return PriorityEstimator.evaluate(data, labels)


def check_if_update_necessary() -> bool:
    """
    Returns true if the last priority estimator update was at least a week ago
    or if the _OVERRIDDEN_PRIORITIES_FILENAME doesn't exist in the s3 bucket
    """
    try:
        overridden_priorities_metadata = s3_client.get_object_summary(
            s3_bucket_name, _OVERRIDDEN_PRIORITIES_FILENAME
        )
        return overridden_priorities_metadata.last_modified + timedelta(days=1) < datetime.now(
            timezone.utc
        )
    except s3.S3Exception:
        return True


if __name__ == "__main__":
    try:
        apply_registry()
        print("running priority updater")
        update_necessary = check_if_update_necessary()
        print("update necessary?", update_necessary)
        if update_necessary:
            prev_overridden_priorities = get_s3_overridden_priorities()
            print("got overridden priorities", len(prev_overridden_priorities))
            overridden_priorities = update_priority_model(prev_overridden_priorities)
            print("calculating priority model score")
            calculate_manual_override_score()
            performance = run_priority_model_holdout_set()
            print(f"updated model performance on holdout set: {performance}")

            if performance > _HOLDOUT_SET_THRESHOLD:
                upload_priority_model_and_data(overridden_priorities)
            else:
                # upload the overridden priorities to reset the modified timestamp
                # those not used in training are flagged for future use
                upload_s3_overridden_priorities(overridden_priorities)
                rollbar.report_message(
                    f"Model was not updated due to poor performance ({performance})", "warning"
                )
    except:
        rollbar.report_exc_info(sys.exc_info())
    finally:
        close_registry()

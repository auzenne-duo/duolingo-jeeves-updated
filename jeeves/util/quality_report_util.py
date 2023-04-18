import json
from typing import Any, Dict, List

from jeeves.model.jira_document import JiraDocument
from jeeves.util.s3_client_and_bucket import get_s3_client_and_bucket

PROJECT_TO_CLIENT = {
    "DLAA": "Android",
    "DLAI": "iOS",
    "DLAW": "Web",
}

FIXED_RESOLUTIONS = ["Fixed", "Done"]
_S3_PATH = "quality_report_scores"


def is_jira_issue_resolved(issue: JiraDocument) -> bool:
    """
    Returns True if the Jira issue has been marked as resolved
    """
    return not issue.resolution in ["Unresolved", ""]


def get_past_quality_issue_data(title: str) -> List[Dict[str, Any]]:
    """
    gets the past issues used in quality report

    returns:
        list of the following structure
        [{"date": "2021-09-09", "title": "Path", "issues": {"DLAA-1000":{"status":"Closed"}}}, ...]
    """
    s3_client, s3_bucket_name = get_s3_client_and_bucket()
    try:
        return json.loads(
            s3_client.download(s3_bucket_name, f"{_S3_PATH}/{title}/quality_issue_data_{title}")
        )
    except:
        print(f"Could not find quality report issue data for {title}")
        return []

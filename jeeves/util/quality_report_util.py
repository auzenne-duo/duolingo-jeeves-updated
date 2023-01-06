from jeeves.model.jira_document import JiraDocument

_DONE_STATUSES = ["Closed", "Merged", "Done", "Launched"]


def check_jira_issue_resolved(issue: JiraDocument) -> bool:
    """
    Returns True if the Jira issue has been marked as resolved
    """
    return issue.status in _DONE_STATUSES

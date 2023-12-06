TEMPLATE_DIRECTORY = "templates/quality_report/"
PROJECT_TO_PLATFORM = {
    "DLAA": "Android",
    "DLAI": "iOS",
    "DLAW": "Web",
}
CODEBASE_TO_PLATFORM = {
    "duolingo-android": "Android",
    "duolingo-ios": "iOS",
    "duolingo-web": "Web",
}
QUALITY_REPORT_OVERALL_KEY = "Overall"

QUALITY_REPORT_WINDOW_DAYS = 90


def is_jira_issue_resolved(resolution: str) -> bool:
    """
    Returns True if the Jira issue has been marked as resolved
    """
    return resolution not in ["Unresolved", ""]

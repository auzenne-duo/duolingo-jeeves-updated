TEMPLATE_DIRECTORY = "templates/quality_report/"
PROJECT_TO_PLATFORM = {
    "DLAA": "Android",
    "DLAI": "iOS",
    "DLAW": "Web",
    # Video Call technically isn't a platform, but we'll add these here
    # in case we need to show them as a category with the other platforms
    "VCCF": "Video Call",
    "VCBF": "Video Call",
    "EXAI": "Video Call",
    "VCS": "Video Call",
    "VCG": "Video Call",
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

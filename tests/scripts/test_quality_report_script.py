import unittest
from datetime import datetime
from unittest.mock import patch

from jeeves.model.jira_document import JiraDocument
from jeeves.model.shake_to_report_category import ShakeToReportCategory
from jeeves.scripts.quality_report_script import (
    IssueStatus,
    calculate_max_priority_issues,
    calculate_scores,
    create_appendix_text,
    create_priority_group_text,
    create_status_priority_count,
    create_worst_issues_text,
    filter_for_unique_project_issues,
    search_for_area_issues,
)
from jeeves.util.date_util import parse_external_datetime
from jeeves.util.quality_report_priority import get_quality_report_priority

JiraDocument.set_feature_field_key("feature_field")

JIRA_EXTERNAL_JSON_1 = {
    "id": "",
    "key": "DLAI-2000",
    "fields": {
        "description": {
            "type": "text",
            "text": "Reported with shake-to-report \n View Controller Name: \n VCActivity\nSystem Information:\nplatform:iOS",
        },
        "summary": "",
        "course": "",
        "fullstory_url": "",
        "os_version": "",
        "ui_language": "",
        "username": "",
        "key": "",
        "project": {"key": "DLAI-2000"},
        "created": "2022-09-09",
        "updated": "2022-09-09",
        "status": {"statusCategory": {"name": "Done"}},
        "components": [],
        "feature_field": {"value": "Onboarding", "self": "Onboarding"},
        "priority": {"name": "Medium"},
        "reporter": {"displayName": ""},
        "labels": [],
        "resolutiondate": "",
        "resolution": "",
        "assignee": "",
    },
}

JIRA_EXTERNAL_JSON_2 = {
    "id": "",
    "key": "DLAI-1998",
    "fields": {
        "id": "",
        "description": "",
        "summary": "",
        "course": "",
        "fullstory_url": "",
        "os_version": "",
        "platform": "",
        "screen_size": "",
        "screen_content": "VCActivity",
        "ui_language": "",
        "username": "",
        "project": {"key": "DLAA"},
        "created": "2022-09-09",
        "updated": "2022-09-09",
        "status": {"statusCategory": {"name": "To Do"}},
        "components": [],
        "feature_field": {"value": "DarkMode", "self": "DarkMode"},
        "priority": {"name": "Low"},
        "reporter": {"displayName": ""},
        "labels": [],
        "resolutiondate": "",
        "resolution": "",
        "assignee": "",
    },
}

DATETIME = parse_external_datetime("2022-09-09")
JIRA_DOCUMENT_1 = JiraDocument(
    issue_key="DLAI-2000",
    project="DLAI-2000",
    linked_duplicate_keys=[],
    creation_date=DATETIME,
    updated_date=DATETIME,
    resolution_date=None,
    status="Done",
    feature="Onboarding",
    priority=get_quality_report_priority("Medium"),
    reporter="",
    reporter_email="",
    assignee="UNASSIGNED",
    comments=[],
    labels=[],
    embedding_vector=[],
    data_source="JIRA",
    document_id="",
    jeeves_uid="JIRA_",
    date_time=DATETIME,
    body_text="\n",
    language="en",
    shake_to_report_category=ShakeToReportCategory.INTERNAL,
    attachments=[],
    duolingo_metadata={
        "view_controller_name": "VCActivity",
        "system_information": {"platform": "iOS"},
        "raw": "platform:iOS",
    },
    app_version="",
    course="",
    fullstory_url="",
    os_version="",
    platform="iOS",
    screen_size="",
    screen_content="VCActivity",
    ui_language="",
    username="",
    issue_links=[],
    issue_type="",
    resolution="",
    components=[],
    feature_url="Onboarding",
)
JIRA_DOCUMENT_1.is_done = True

JIRA_DOCUMENT_2 = JiraDocument(
    issue_key="DLAI-1998",
    project="DLAI",
    linked_duplicate_keys=["DLAI-2003", "DLAA-2004"],
    creation_date=DATETIME,
    updated_date=DATETIME,
    resolution_date="",
    status="To Do",
    feature="DarkMode",
    priority=get_quality_report_priority("Low"),
    reporter="",
    reporter_email="",
    assignee="",
    comments=[],
    labels=[],
    embedding_vector=[],
    data_source="JIRA",
    document_id="",
    jeeves_uid="JIRA_",
    date_time=DATETIME,
    body_text="",
    language="xx",
    shake_to_report_category=ShakeToReportCategory.INTERNAL,
    attachments=[],
    duolingo_metadata={},
    app_version="",
    course="",
    fullstory_url="",
    os_version="",
    platform="",
    screen_size="",
    screen_content="",
    ui_language="en",
    username="",
    issue_links="",
    issue_type="",
    resolution="",
    components=[],
    feature_url="",
)
JIRA_DOCUMENT_2.is_done = False

JIRA_DOCUMENT_3 = JiraDocument(
    issue_key="DLAI-2003",
    project="DLAI",
    linked_duplicate_keys=["DLAI-1998"],
    creation_date=DATETIME,
    updated_date=DATETIME,
    resolution_date="",
    status="Done",
    feature="DarkMode",
    priority=get_quality_report_priority("Medium"),
    reporter="",
    reporter_email="",
    assignee="",
    comments=[],
    labels=[],
    embedding_vector=[],
    data_source="JIRA",
    document_id="",
    jeeves_uid="JIRA_",
    date_time=DATETIME,
    body_text="View Controller Name:VCActivity",
    language="xx",
    shake_to_report_category=ShakeToReportCategory.NON_STR_INTERNAL,
    attachments=[],
    duolingo_metadata={},
    app_version="",
    course="",
    fullstory_url="",
    os_version="",
    platform="",
    screen_size="",
    screen_content="",
    ui_language="en",
    username="",
    issue_links="",
    issue_type="",
    resolution="",
    components=[],
    feature_url="",
)
JIRA_DOCUMENT_3.is_done = True

JIRA_DOCUMENT_4 = JiraDocument(
    issue_key="DLAA-2004",
    project="DLAA",
    linked_duplicate_keys=[],
    creation_date=DATETIME,
    updated_date=DATETIME,
    resolution_date="",
    status="Done",
    feature="DarkMode",
    priority=get_quality_report_priority("High"),
    reporter="",
    reporter_email="",
    assignee="",
    comments=[],
    labels=[],
    embedding_vector=[],
    data_source="JIRA",
    document_id="",
    jeeves_uid="JIRA_",
    date_time=DATETIME,
    body_text="View Controller Name:VCActivity",
    language="xx",
    shake_to_report_category=ShakeToReportCategory.NON_STR_INTERNAL,
    attachments=[],
    duolingo_metadata={},
    app_version="",
    course="",
    fullstory_url="",
    os_version="",
    platform="",
    screen_size="",
    screen_content="",
    ui_language="en",
    username="",
    issue_links="",
    issue_type="",
    resolution="",
    components=[],
    feature_url="",
)
JIRA_DOCUMENT_4.is_done = True


class TestQualityReportScript(unittest.TestCase):
    @patch("jeeves.scripts.quality_report_script.JiraDAL")
    @patch("jeeves.scripts.quality_report_script.JiraManager")
    def test_search_for_area_issuess(self, MockJiraManager, MockJiraDAL):
        MockJiraDAL.paginate_search_issues.return_value = (
            issue for issue in [JIRA_EXTERNAL_JSON_1, JIRA_EXTERNAL_JSON_2]
        )
        MockJiraManager.get_feature_field.return_value = "feature_field"

        result = search_for_area_issues("Growth", datetime(2000, 1, 1), datetime(2000, 2, 1))
        expected = [JIRA_DOCUMENT_1]
        self.assertEqual(result, expected)

    def test_filter_for_unique_project_issues(self):
        JIRA_DOCUMENT_2.is_done = False
        result = filter_for_unique_project_issues(
            [JIRA_DOCUMENT_1, JIRA_DOCUMENT_2, JIRA_DOCUMENT_3], {"DLAA-2004": JIRA_DOCUMENT_4}
        )
        JIRA_DOCUMENT_2.is_done = True
        JIRA_DOCUMENT_2.priority = get_quality_report_priority("High")
        expected = [JIRA_DOCUMENT_1, JIRA_DOCUMENT_2], {"DLAI-1998": JIRA_DOCUMENT_2}
        self.assertEqual(result, expected)
        JIRA_DOCUMENT_2.is_done = False
        JIRA_DOCUMENT_2.priority = get_quality_report_priority("Low")

    def test_calculate_max_priority_issues(self):
        result = calculate_max_priority_issues([JIRA_DOCUMENT_1, JIRA_DOCUMENT_2])
        expected = [JIRA_DOCUMENT_1]
        self.assertEqual(result, expected)

    def test_calculate_max_priority_issues_tied(self):
        JIRA_DOCUMENT_1.priority = get_quality_report_priority("High")
        JIRA_DOCUMENT_2.priority = get_quality_report_priority("High")
        result = calculate_max_priority_issues([JIRA_DOCUMENT_1, JIRA_DOCUMENT_2, JIRA_DOCUMENT_3])
        expected = [JIRA_DOCUMENT_1, JIRA_DOCUMENT_2]
        self.assertEqual(result, expected)
        JIRA_DOCUMENT_2.priority = get_quality_report_priority("Low")

    def test_create_status_priority_count(self):
        JIRA_DOCUMENT_1.priority = get_quality_report_priority("Medium")
        JIRA_DOCUMENT_2.is_done = False
        result = create_status_priority_count([JIRA_DOCUMENT_1, JIRA_DOCUMENT_2, JIRA_DOCUMENT_3])
        expected = {
            IssueStatus.OPEN: {get_quality_report_priority("Low"): 1},
            IssueStatus.CLOSED: {get_quality_report_priority("Medium"): 2},
        }
        self.assertEqual(result, expected)

    def test_calculate_scores(self):
        priority_count = {
            IssueStatus.OPEN: {get_quality_report_priority("High"): 1},
            IssueStatus.CLOSED: {
                get_quality_report_priority("Medium"): 5,
                get_quality_report_priority("High"): 2,
            },
        }
        result = calculate_scores(priority_count)
        expected = (75, 10, 30)
        self.assertEqual(result, expected)

    def test_create_priority_group_text(self):
        group_count = {
            IssueStatus.OPEN: {get_quality_report_priority("High"): 3},
            IssueStatus.CLOSED: {
                get_quality_report_priority("Medium"): 5,
                get_quality_report_priority("High"): 2,
            },
        }
        result = create_priority_group_text(group_count[IssueStatus.CLOSED])
        print("result", result)
        expected = """    - High/Highest: 2 issues * 10 points => 20
    - Medium: 5 issues * 2 points => 10"""
        self.assertEqual(result, expected)

    def test_create_worst_issues_text(self):
        max_priority_issues = [JIRA_DOCUMENT_1, JIRA_DOCUMENT_2]
        max_dupes_issue = JIRA_DOCUMENT_2
        result = create_worst_issues_text(max_priority_issues, max_dupes_issue)
        expected = """

* <span class='bold'>Most reports:</span>
    - [DLAI-1998](https://duolingo.atlassian.net/browse/DLAI-1998):  - Low/Lowest with 2 duplicate reports
* <span class="bold">Most likely to block learners:</span>
    - [DLAI-2000](https://duolingo.atlassian.net/browse/DLAI-2000):  - Medium
    - [DLAI-1998](https://duolingo.atlassian.net/browse/DLAI-1998):  - Low/Lowest
"""
        self.assertEqual(result, expected)

    def test_create_worst_issues_text_one_duplicate(self):
        max_priority_issues = [JIRA_DOCUMENT_1, JIRA_DOCUMENT_2]
        max_dupes_issue = JIRA_DOCUMENT_3
        result = create_worst_issues_text(max_priority_issues, max_dupes_issue)
        expected = """

* <span class='bold'>Most reports:</span>
    - [DLAI-2003](https://duolingo.atlassian.net/browse/DLAI-2003):  - Medium with 1 duplicate report
* <span class="bold">Most likely to block learners:</span>
    - [DLAI-2000](https://duolingo.atlassian.net/browse/DLAI-2000):  - Medium
    - [DLAI-1998](https://duolingo.atlassian.net/browse/DLAI-1998):  - Low/Lowest
"""
        self.assertEqual(result, expected)

    def test_create_appendix_text(self):
        result = create_appendix_text(["feature1", "feature2"])
        expected = f"""

<div style="page-break-after: always;"></div>

## Appendix

### Features

This report was compiled using issues with features:

feature1, feature2
"""
        self.assertEqual(result, expected)

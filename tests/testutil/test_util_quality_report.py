from datetime import timedelta

from jeeves.model.jira_document import JiraDocument
from jeeves.model.quality_report_issue import QualityReportIssue
from jeeves.model.shake_to_report_category import ShakeToReportCategory
from jeeves.util.date_util import parse_external_datetime


def create_jira_doc(
    issue_key,
    feature,
    resolution,
    priority,
    linked_duplicate_keys,
    duolingo_metadata=None,
    labels=None,
    body_text="",
    str_category=ShakeToReportCategory.INTERNAL,
    status="",
    is_done=False,
    is_fixed=False,
    fixed_within_one_week=False,
    issue_links=None,
    issue_type="",
    screen_content="VCActivity",
):
    if labels is None:
        labels = []
    if duolingo_metadata is None:
        duolingo_metadata = {}
    if issue_links is None:
        issue_links = []

    datetime = parse_external_datetime("2022-09-09")
    resolution_date = None
    if fixed_within_one_week:
        resolution_date = datetime + timedelta(days=4)
    doc = JiraDocument(
        issue_key=issue_key,
        project=issue_key[:4],
        linked_duplicate_keys=linked_duplicate_keys,
        creation_date=datetime,
        updated_date=datetime,
        resolution_date=resolution_date,
        status=status,
        feature=feature,
        priority=priority,
        reporter="",
        reporter_email="",
        assignee="UNASSIGNED",
        comments=[],
        labels=labels,
        embedding_vector=[],
        data_source="JIRA",
        document_id="",
        jeeves_uid="JIRA_",
        date_time=datetime,
        body_text=body_text,
        language="en",
        shake_to_report_category=str_category,
        attachments=[],
        duolingo_metadata=duolingo_metadata,
        app_version="",
        course="",
        fullstory_url="",
        os_version="",
        platform="iOS",
        screen_size="",
        screen_content=screen_content,
        ui_language="",
        username="",
        issue_links=issue_links,
        issue_type=issue_type,
        resolution=resolution,
        components=[],
        feature_url="Onboarding",
        experiment_conditions={},
        jira_attachments=[],
    )
    return doc


def create_quality_report_issue(doc: JiraDocument):
    return QualityReportIssue(doc)


REPORT_ISSUE_1 = create_quality_report_issue(
    create_jira_doc("DLAI-2001", "Onboarding", "Unresolved", "Medium", ["DLAI-2002", "DLAI-2003"])
)

REPORT_ISSUE_2 = create_quality_report_issue(
    create_jira_doc(
        "DLAI-2002",
        "Onboarding",
        "Not a bug",
        "High",
        ["DLAI-2001"],
        labels=["parent_bug"],
        is_done=True,
    )
)

REPORT_ISSUE_3 = create_quality_report_issue(
    create_jira_doc(
        "DLAI-2003", "Onboarding", "Unresolved", "High", [], screen_content="VCScreenName"
    )
)

REPORT_ISSUE_4 = create_quality_report_issue(
    create_jira_doc(
        "DLAI-2004",
        "Onboarding",
        "Done",
        "High",
        [],
        is_done=True,
        is_fixed=True,
        fixed_within_one_week=True,
    )
)

REPORT_ISSUE_5 = create_quality_report_issue(
    create_jira_doc(
        "DLAI-2005",
        "Onboarding",
        "Fixed",
        "Medium",
        [],
        is_done=True,
        is_fixed=True,
        fixed_within_one_week=False,
    )
)

REPORT_ISSUE_6 = create_quality_report_issue(
    create_jira_doc(
        "DLAI-2006",
        "Onboarding",
        "Fixed",
        "Medium",
        [],
        is_done=True,
        is_fixed=True,
        fixed_within_one_week=False,
    )
)

REPORT_ISSUE_8 = create_quality_report_issue(
    create_jira_doc(
        "DLAA-2008",
        "Onboarding",
        "Fixed",
        "Medium",
        [],
        screen_content="test.screen_name",
    )
)

REPORT_ISSUE_9 = create_quality_report_issue(
    create_jira_doc(
        "DLAW-2009",
        "Onboarding",
        "Fixed",
        "Medium",
        [],
        screen_content="test.com/learn",
    )
)

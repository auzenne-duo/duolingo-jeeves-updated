import unittest
from datetime import datetime

from jeeves.model.jira_document import JiraDocument
from jeeves.model.quality_report_issue import QualityReportIssue
from jeeves.model.shake_to_report_category import ShakeToReportCategory


def create_jira_doc(
    issue_key,
    feature,
    status,
    priority,
    linked_duplicate_keys,
    duolingo_metadata=None,
    labels=None,
    body_text="",
    str_category=ShakeToReportCategory.INTERNAL,
    resolution="",
):
    if labels is None:
        labels = []
    if duolingo_metadata is None:
        duolingo_metadata = {}
    date = datetime(2020, 1, 1)
    doc = JiraDocument(
        issue_key=issue_key,
        project=issue_key[:4],
        linked_duplicate_keys=linked_duplicate_keys,
        creation_date=date,
        updated_date=date,
        resolution_date=None,
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
        date_time=date,
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
        screen_content="VCActivity",
        ui_language="",
        username="",
        issue_links=[],
        issue_type="",
        resolution=resolution,
        components=[],
        feature_url="Onboarding",
        experiment_conditions={},
        jira_attachments=[],
    )
    return doc


JIRA_DOCUMENT_1 = create_jira_doc(
    "DLAI-2001", "Onboarding", "To Do", "Medium", ["DLAI-2002", "DLAI-2003"]
)


class TestQualityReportBase(unittest.TestCase):
    def test_serialize(self):
        issue = QualityReportIssue(JIRA_DOCUMENT_1)
        result = issue.serialize()
        expected = {
            "body_text": "",
            "client": "iOS",
            "creation_date": "2020-01-01",
            "feature": "Onboarding",
            "header_text": "",
            "issue_key": "DLAI-2001",
            "is_parent": False,
            "labels": [],
            "linked_duplicate_keys": ["DLAI-2002", "DLAI-2003"],
            "score_params": {
                "is_done": False,
                "priority": "Medium",
                "score": 10,
                "group": "MEDIUM",
                "resolution": "OPEN",
                "time_to_fix": "NOT_WITHIN_ONE_WEEK",
            },
            "project": "DLAI",
            "resolution": "",
            "resolution_date": None,
            "screen_content": "VCActivity",
            "team": "Onboarding",
        }
        self.assertEqual(result, expected)

    def test_deserialize(self):
        priority = QualityReportIssue(JIRA_DOCUMENT_1)
        result = QualityReportIssue.deserialize(priority.serialize())
        print(result.creation_date, priority.creation_date)
        self.assertEqual(result.__dict__, priority.__dict__)

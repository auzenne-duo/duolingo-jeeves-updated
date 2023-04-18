from jeeves.config.jira_features import JIRA_FEATURES
from jeeves.model.issue_score_parameters import IssueScoreParameters
from jeeves.model.jira_document import JiraDocument
from jeeves.util.date_util import date_to_str, time_series_str_to_datetime
from jeeves.util.quality_report_util import (
    FIXED_RESOLUTIONS,
    PROJECT_TO_CLIENT,
    is_jira_issue_resolved,
)

_FEATURE_TO_TEAM = {
    feature: team
    for _, team_features in JIRA_FEATURES.items()
    for team, feature_map in team_features.items()
    for feature in feature_map.keys()
}

# Replaces characters in jira text that aren't properly handled by html, such as <
def format_str(text: str) -> str:
    return text.replace("<", "&lt;").replace(">", "&gt;")


class QualityReportIssue:
    """
    Simplified Jira issue object for use in quality reports

    Most attributes are same as JiraDocument, but some extras:
        - is_done: True if issue is resolved
        - team: team that owns the issue
        - client: ios, android, etc.
        - is_fixed: True if issue is resolved and resolution is one of FIXED_RESOLUTIONS
        - fixed_within_one_week: True if issue is resolved and fixed within one week of creation
    """

    data_source = JiraDocument.get_data_source_identifier()

    def __init__(self, jira_doc: JiraDocument):
        self.issue_key = jira_doc.issue_key
        self.team = _FEATURE_TO_TEAM.get(jira_doc.feature, "Unknown team")
        self.client = PROJECT_TO_CLIENT.get(jira_doc.project)
        is_fixed = jira_doc.resolution in FIXED_RESOLUTIONS
        fixed_within_one_week = False
        if is_fixed and jira_doc.resolution_date and jira_doc.creation_date:
            fixed_within_one_week = (jira_doc.resolution_date - jira_doc.creation_date).days <= 7

        self.score_params = IssueScoreParameters(
            jira_doc.priority,
            jira_doc.labels,
            is_jira_issue_resolved(jira_doc),
            jira_doc.resolution in FIXED_RESOLUTIONS,
            fixed_within_one_week,
        )
        self.feature = jira_doc.feature
        self.is_parent = "parent_bug" in jira_doc.labels
        self.body_text = format_str(jira_doc.body_text)
        self.creation_date = jira_doc.creation_date
        self.header_text = format_str(jira_doc.header_text)
        self.linked_duplicate_keys = jira_doc.linked_duplicate_keys
        self.project = jira_doc.project
        self.resolution = jira_doc.resolution
        self.resolution_date = jira_doc.resolution_date
        self.labels = jira_doc.labels
        self.screen_content = jira_doc.screen_content

    def serialize(self) -> dict:
        return {
            "body_text": self.body_text,
            "client": self.client,
            "creation_date": date_to_str(self.creation_date) if self.creation_date else None,
            "feature": self.feature,
            "header_text": self.header_text,
            "issue_key": self.issue_key,
            "is_parent": self.is_parent,
            "linked_duplicate_keys": self.linked_duplicate_keys,
            "score_params": self.score_params.serialize(),
            "project": self.project,
            "resolution": self.resolution,
            "resolution_date": date_to_str(self.resolution_date) if self.resolution_date else None,
            "team": self.team,
            "labels": self.labels,
            "screen_content": self.screen_content,
        }

    @classmethod
    def deserialize(cls, data: dict) -> "QualityReportIssue":
        data["score_params"] = IssueScoreParameters.deserialize(data["score_params"])
        issue = cls.__new__(cls)
        for key, value in data.items():
            setattr(issue, key, value)
        issue.creation_date = (
            time_series_str_to_datetime(data["creation_date"]) if "creation_date" in data else None
        )
        issue.resolution_date = (
            time_series_str_to_datetime(data["resolution_date"])
            if "resolution_date" in data
            else None
        )
        return issue

import json
import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytz

from jeeves.scripts.quality_report_issue_updates import (
    check_issue_updates,
    check_quality_report_updates,
)

JIRA_EXTERNAL_JSON_1 = {
    "key": "DLAI-2001",
    "changelog": {
        "histories": [
            {
                "created": "2021-10-01T00:00:00.000-0700",
                "items": [{"field": "priority", "fromString": "Medium", "toString": "High"}],
                "author": {"displayName": "duo"},
            }
        ]
    },
}

JIRA_EXTERNAL_JSON_2 = {
    "key": "DLAI-2002",
    "changelog": {
        "histories": [
            {
                "created": "2022-01-04T00:00:00.000-0700",
                "items": [{"field": "priority", "fromString": "Medium", "toString": "High"}],
                "author": {"displayName": "duo"},
            }
        ]
    },
}

mockJiraDocument = MagicMock()
mockJiraDocument.deserialize_from_external_json.side_effect = lambda x: MagicMock(
    issue_key=x["key"], priority="", feature="", reporter_email="", header_text=""
)


class TestQualityReportUtil(unittest.TestCase):
    @patch("jeeves.scripts.quality_report_issue_updates.JiraDAL")
    @patch("jeeves.scripts.quality_report_issue_updates.JiraDocument", mockJiraDocument)
    def test_check_issue_updates(self, mockJiraDAL):

        mockJiraDAL.paginate_search_issues.return_value = [
            JIRA_EXTERNAL_JSON_1,
            JIRA_EXTERNAL_JSON_2,
        ]

        updated_issues, update_actions = check_issue_updates(
            ["DLAI-2001", "DLAI-2002"], since_date=datetime(2022, 1, 1).replace(tzinfo=pytz.utc)
        )
        print("updated_issues", updated_issues, "update_actions", update_actions)
        expected_updated_issues = set(["DLAI-2002"])
        expected_update_actions = {"DLAI-2001": [], "DLAI-2002": ["priority"]}
        self.assertEqual(updated_issues, expected_updated_issues)
        self.assertEqual(update_actions, expected_update_actions)

    @patch(
        "jeeves.scripts.quality_report_issue_updates.JIRA_FEATURES",
        {"area": {"team": [], "team2": []}},
    )
    @patch(
        "jeeves.scripts.quality_report_issue_updates.datetime",
        MagicMock(now=MagicMock(return_value=datetime(2021, 9, 10).replace(tzinfo=pytz.utc))),
    )
    @patch("jeeves.scripts.quality_report_issue_updates.upload_to_jeeves_s3")
    @patch("jeeves.scripts.quality_report_issue_updates.check_issue_updates")
    @patch("jeeves.scripts.quality_report_issue_updates.get_past_quality_issue_data")
    def test_check_quality_report_updates(
        self, mock_get_past_quality_issue_data, mock_check_issue_updates, mock_upload
    ):
        mock_get_past_quality_issue_data.side_effect = [
            [],
            [
                {
                    "date": "2021-09-09",
                    "title": "team2",
                    "max_priority_issues": ["DLAA-1000"],
                    "max_dupes_issues": ["DLAA-1001"],
                }
            ],
        ]
        mock_check_issue_updates.return_value = (
            set(["DLAA-1000"]),
            {"DLAA-1000": ["priority"], "DLAA-1001": []},
        )
        check_quality_report_updates(datetime(2021, 9, 8).replace(tzinfo=pytz.utc))
        mock_upload.assert_called_once_with(
            "quality_report_metrics/quality_report_updates_2021-09-10",
            json.dumps(
                {
                    "stats": {
                        "team2": {
                            "score": 0.5,
                            "num_issues": 2,
                            "update_actions": {"DLAA-1000": ["priority"], "DLAA-1001": []},
                        }
                    },
                    "date": "2021-09-10",
                    "since_date": "2021-09-08",
                }
            ),
        )

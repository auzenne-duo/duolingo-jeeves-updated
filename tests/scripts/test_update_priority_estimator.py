import json
import unittest
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

from duolingo_base.dal import s3

from jeeves.scripts.update_priority_estimator import (
    OverriddenPriorityIssue,
    calculate_manual_override_score,
    check_if_update_necessary,
    get_s3_overridden_priorities,
    get_updated_jira_priorities,
    run_priority_model_holdout_set,
)

# invalid because already in overridden_priorities
JIRA_EXTERNAL_JSON_1 = {
    "key": "DLAI-2001",
    "changelog": {
        "histories": [
            {
                "items": [{"field": "priority", "fromString": "Medium", "toString": "High"}],
                "author": {"displayName": "duo"},
            }
        ]
    },
}

# valid priority update
JIRA_EXTERNAL_JSON_2 = {
    "key": "DLAI-2002",
    "changelog": {
        "histories": [
            {
                "items": [{"field": "priority", "fromString": "High", "toString": "Medium"}],
                "author": {"displayName": "duo"},
            }
        ]
    },
}

# invalid because not a priority
JIRA_EXTERNAL_JSON_3 = {
    "key": "DLAI-2003",
    "changelog": {
        "histories": [
            {
                "items": [{"field": "something", "fromString": "Medium", "toString": "High"}],
                "author": {"displayName": "duo"},
            }
        ]
    },
}

# invalid because from Jira Automation
JIRA_EXTERNAL_JSON_4 = {
    "key": "DLAI-2004",
    "changelog": {
        "histories": [
            {
                "items": [{"field": "priority", "fromString": "Medium", "toString": "High"}],
                "author": {"displayName": "Jira Automation"},
            }
        ]
    },
}

# valid priority update
JIRA_EXTERNAL_JSON_5 = {
    "key": "DLAI-2005",
    "changelog": {
        "histories": [
            {
                "items": [{"field": "something"}],
                "author": {"displayName": "duo"},
            },
            {
                "items": [
                    {"field": "something"},
                    {"field": "priority", "fromString": "Medium", "toString": "High"},
                ],
                "author": {"displayName": "duo"},
            },
            {
                "items": [
                    {"field": "something"},
                    {"field": "priority", "fromString": "Low", "toString": "Medium"},
                ],
                "author": {"displayName": "duo"},
            },
        ]
    },
}

mockJiraDocument = MagicMock()
mockJiraDocument.deserialize_from_external_json.side_effect = lambda x: MagicMock(
    issue_key=x["key"], priority="", feature="", reporter_email="", header_text=""
)

mockJiraDAL = MagicMock()
mockJiraDAL.paginate_search_issues.return_value = [
    JIRA_EXTERNAL_JSON_1,
    JIRA_EXTERNAL_JSON_2,
    JIRA_EXTERNAL_JSON_3,
    JIRA_EXTERNAL_JSON_4,
    JIRA_EXTERNAL_JSON_5,
]

mock_estimate_priority = MagicMock()
mockS3 = MagicMock()


@patch("jeeves.scripts.update_priority_estimator.JiraDocument", mockJiraDocument)
@patch("jeeves.scripts.update_priority_estimator.JiraDAL", mockJiraDAL)
@patch("jeeves.scripts.update_priority_estimator.s3_client", mockS3)
@patch("jeeves.scripts.update_priority_estimator.s3_bucket_name", "s3_bucket")
class TestUpdatePriorityEstimator(unittest.TestCase):
    def test_get_updated_jira_priorities(self):
        result = get_updated_jira_priorities(
            datetime(2022, 9, 20),
            datetime(2022, 9, 22),
            {
                "DLAI-2001": OverriddenPriorityIssue("DLAI-2001", "", "", "", "Medium"),
                "DLAI-2002": OverriddenPriorityIssue("DLAI-2002", "", "", "", "Medium"),
            },
        )
        expected = {
            "DLAI-2001": OverriddenPriorityIssue(
                "DLAI-2001", "", "", "", "High", "Medium", "2022-09-22"
            ),
            "DLAI-2005": OverriddenPriorityIssue(
                "DLAI-2005", "", "", "", "High", "Medium", "2022-09-22"
            ),
        }
        self.assertEqual(result, expected)

    def test_calculate_manual_override_score(self):
        calculate_manual_override_score(datetime(2022, 9, 22), datetime(2022, 9, 20))
        mockS3.upload.assert_called_with(
            "s3_bucket",
            f"priority_estimator_scores/score_2022-09-20_2022-09-22",
            json.dumps(
                {
                    "score": 1.0,
                    "total_issues": 4,
                    "overridden_priorities": {
                        "DLAI-2001": {
                            "issue_key": "DLAI-2001",
                            "summary": "",
                            "feature": "",
                            "reporter": "",
                            "priority": "High",
                            "old_priority": "Medium",
                            "date_stored": None,
                        },
                        "DLAI-2002": {
                            "issue_key": "DLAI-2002",
                            "summary": "",
                            "feature": "",
                            "reporter": "",
                            "priority": "Medium",
                            "old_priority": "High",
                            "date_stored": None,
                        },
                        "DLAI-2005": {
                            "issue_key": "DLAI-2005",
                            "summary": "",
                            "feature": "",
                            "reporter": "",
                            "priority": "High",
                            "old_priority": "Low",
                            "date_stored": None,
                        },
                    },
                }
            ),
        )

    @patch("jeeves.scripts.update_priority_estimator.PriorityEstimator.evaluate")
    def test_run_priority_model_holdout_set(self, mock_evaluate):
        mock_evaluate.return_value = 0.5
        mockS3.download.return_value = '{"DLAA-1":{"priority":0, "summary":"", "feature":""}, "DLAA-2":{"priority":2, "summary":"", "feature":"", "reporter":"biglou"}}'
        result = run_priority_model_holdout_set()
        expected = 0.5
        self.assertEqual(result, expected)
        mock_evaluate.assert_called_with(("; ; ", "; ; biglou"), (0, 2))

    def test_get_s3_overridden_priorities(self):
        mockS3.download.return_value = '{"DLAA-1":{"issue_key":"DLAA-1", "priority":"Low", "summary":"", "feature":"", "reporter":"duo", "old_priority":"High", "date_stored":"2022-09-01"}, \
            "DLAA-2":{"issue_key":"DLAA-2", "priority":"High", "summary":"test", "feature":"test feature", "reporter":"biglou"}}'
        result = get_s3_overridden_priorities()
        expected = {
            "DLAA-1": OverriddenPriorityIssue("DLAA-1", "", "", "duo", "Low", "High", "2022-09-01"),
            "DLAA-2": OverriddenPriorityIssue("DLAA-2", "test", "test feature", "biglou", "High"),
        }
        self.assertEqual(result, expected)

    def test_check_if_update_necessary(self):
        mockS3.get_object_summary.return_value.last_modified = datetime.now(timezone.utc)
        self.assertFalse(check_if_update_necessary())

        mockS3.get_object_summary.return_value.last_modified = datetime.now(
            timezone.utc
        ) - timedelta(weeks=4)
        self.assertTrue(check_if_update_necessary())

        mockS3.get_object_summary.side_effect = s3.S3DownloadException("No such file")
        self.assertTrue(check_if_update_necessary())

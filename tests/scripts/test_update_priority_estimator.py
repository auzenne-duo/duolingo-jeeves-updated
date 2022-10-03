import unittest
from datetime import datetime
from unittest.mock import MagicMock, patch

from jeeves.scripts.update_priority_estimator import get_updated_jira_priorities

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
                "items": [{"field": "priority", "fromString": "Medium", "toString": "High"}],
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
        ]
    },
}


class TestUpdatePriorityEstimator(unittest.TestCase):
    @patch("jeeves.scripts.update_priority_estimator.JiraDAL")
    @patch("jeeves.scripts.update_priority_estimator.JiraDocument")
    def test_get_updated_jira_priorities(self, mockJiraDocument, mockJiraDAL):
        mockJiraDocument.deserialize_from_external_json.side_effect = lambda x: MagicMock(
            issue_key=x["key"], priority="", feature="", reporter_email="", header_text=""
        )
        mockJiraDAL.paginate_search_issues.return_value = (
            issue
            for issue in [
                JIRA_EXTERNAL_JSON_1,
                JIRA_EXTERNAL_JSON_2,
                JIRA_EXTERNAL_JSON_3,
                JIRA_EXTERNAL_JSON_4,
                JIRA_EXTERNAL_JSON_5,
            ]
        )
        result = get_updated_jira_priorities(
            datetime(2022, 9, 20),
            datetime(2022, 9, 22),
            {"DLAI-2001": {"priority": "Medium"}, "DLAI-2002": {"priority": "High"}},
        )
        expected = {
            "DLAI-2001": {
                "summary": "",
                "feature": "",
                "reporter_email": "",
                "priority": "High",
                "date_stored": "2022-09-22",
            },
            "DLAI-2005": {
                "summary": "",
                "feature": "",
                "reporter_email": "",
                "priority": "High",
                "date_stored": "2022-09-22",
            },
        }
        self.assertEqual(result, expected)

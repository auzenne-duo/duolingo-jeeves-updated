import timeit
import unittest
from datetime import datetime

import responses

from jeeves.dal.jira_dal import JiraApiDAL
from jeeves.model.jira_document import JiraDocument
from jeeves.model.shake_to_report_category import ShakeToReportCategory


class TestJiraApiDAL(unittest.TestCase):
    @responses.activate
    def test_get_issuetype_metadata_with_retry(self):
        responses.add(
            responses.GET,
            "https://duolingo.atlassian.net/rest/api/2/issue/createmeta?expand=projects.issuetypes.fields&projectKeys=DLAA&issuetypeNames=Bug",
            json={},
            status=429,
            headers={"Retry-After": "5"},
        )
        responses.add(
            responses.GET,
            "https://duolingo.atlassian.net/rest/api/2/issue/createmeta?expand=projects.issuetypes.fields&projectKeys=DLAA&issuetypeNames=Bug",
            json={
                "projects": [
                    {
                        "issuetypes": [
                            {
                                "id": "issue_type_id",
                                "name": "issue_type_name",
                                "fields": {
                                    "field_key": {
                                        "key": "field_key",
                                        "name": "field_name",
                                    }
                                },
                            }
                        ]
                    }
                ]
            },
            status=200,
        )

        start_time = timeit.default_timer()
        result = JiraApiDAL().get_issuetype_metadata("DLAA", "Bug")
        end_time = timeit.default_timer()
        assert result[0].id == "issue_type_id"
        assert (
            responses.assert_call_count(
                "https://duolingo.atlassian.net/rest/api/2/issue/createmeta?expand=projects.issuetypes.fields&projectKeys=DLAA&issuetypeNames=Bug",
                2,
            )
            is True
        )
        assert end_time - start_time > 5

    @responses.activate
    def test_get_feature_for_jira_document_with_retry(self):
        responses.add(
            responses.GET,
            "https://duolingo.atlassian.net/rest/api/3/customFieldOption/1",
            json={},
            status=429,
            headers={"Retry-After": "5"},
        )
        responses.add(
            responses.GET,
            "https://duolingo.atlassian.net/rest/api/3/customFieldOption/1",
            json={"value": "Feature name"},
            status=200,
        )

        now_datetime = datetime.now()
        doc = JiraDocument(
            data_source="JIRA",
            document_id="doc1",
            jeeves_uid="uid1",
            date_time=now_datetime,
            header_text="header",
            body_text="I am body text",
            language="en",
            links=[],
            shake_to_report_category=ShakeToReportCategory.EXTERNAL,
            attachments=[],
            duolingo_metadata={},
            app_version="",
            course="",
            fullstory_url="",
            os_version="",
            platform="",
            screen_size="",
            screen_content="",
            ui_language="",
            username="",
            issue_key=f"DLAA-1",
            issue_links=[],
            issue_type="Bug",
            project="DLAA",
            linked_duplicate_keys=[],
            creation_date=now_datetime,
            updated_date=now_datetime,
            resolution_date=None,
            status="To Do",
            resolution="",
            components=[],
            feature_url="https://duolingo.atlassian.net/rest/api/3/customFieldOption/1",
            feature="feature",
            priority="High",
            reporter="",
            reporter_email="",
            assignee="",
            comments=[],
            labels=[],
            embedding_vector=[],
            experiment_conditions={},
            jira_attachments=[],
        )

        start_time = timeit.default_timer()
        result = JiraApiDAL().get_feature_for_jira_document(doc)
        end_time = timeit.default_timer()
        assert result == "Feature name"
        assert (
            responses.assert_call_count(
                "https://duolingo.atlassian.net/rest/api/3/customFieldOption/1", 2
            )
            is True
        )
        assert end_time - start_time > 5


if __name__ == "__main__":
    unittest.main()

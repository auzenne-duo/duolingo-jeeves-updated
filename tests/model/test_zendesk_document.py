import unittest
from unittest.mock import Mock, patch

from jeeves.model.zendesk_document import ZendeskDocument


class Test(unittest.TestCase):
    def test_deserialize_from_internal(self):
        real_json = {
            "data_source": "Zendesk",
            "document_id": "2605487",
            "jeeves_uid": "Zendesk_2605487",
            "date_time": "2021-02-18T21:46:30+00:00",
            "header_text": "Feedback",
            "body_text": "During this session since updating Duolingo the lessons for audio will not work\n\nRegards\n\n-------------------\nApp information:\n\nApp version: 1.246.5\nApp version hash: 7ab8eaa265d7f89f204c3b465460e592a18c8e57\nBrowser: Samsung Internet for Android 27.0\nOS: Android 10\nPlatform: mobile\nScreen: 360x706, DPR 3\nLanguages: undefined<-undefined\nUsername: undefined\nUser ID: undefined\nCourse: undefined\n\n-------------------\nSession information:\n\nFullStory session: unavailable\nURL: https://www.duolingo.com/help/support-request\nPreview URL: unavailable",
            "language": "en",
            "links": [
                "https://duolingotest.zendesk.com/agent/tickets/2605487",
                "https://duolingotest.zendesk.com/agent/users/396886715512",
            ],
            "shake_to_report_category": "NON_STR_EXTERNAL",
            "attachments": [],
            "duolingo_metadata": {},
            "app_version": "",
            "course": "",
            "fullstory_url": "",
            "os_version": "",
            "platform": "",
            "screen_size": "",
            "screen_content": "",
            "ui_language": "",
            "username": "",
            "email": "",
            "product": "LA",
            "priority": None,
            "via": {
                "channel": "email",
                "source": {
                    "from": {"address": "chrisdelsm@hotmail.com", "name": "Christine692827"},
                    "to": {"name": "Duolingo", "address": "iphone@duolingo.com"},
                    "rel": None,
                },
            },
            "tags": ["closed_by_merge", "iphoneapp"],
            "requester_id": "396886715512",
            "metadata": {},
        }
        doc_base = ZendeskDocument.deserialize_from_internal_json(real_json)

        hash_base = ZendeskDocument.generate_opensearch_internal_id(doc_base)

        # Change jeeves_uid
        uid_json = {k: ("Zendesk_00000" if k == "jeeves_uid" else real_json[k]) for k in real_json}
        doc_uid_diff = ZendeskDocument.deserialize_from_internal_json(uid_json)
        hash_uid_diff = ZendeskDocument.generate_opensearch_internal_id(doc_uid_diff)

        # Change requester_id
        user_json = {k: ("some_user" if k == "requester_id" else real_json[k]) for k in real_json}
        doc_user_diff = ZendeskDocument.deserialize_from_internal_json(user_json)
        hash_user_diff = ZendeskDocument.generate_opensearch_internal_id(doc_user_diff)

        # Change body_text
        body_json = {
            k: ("The quick brown fox" if k == "body_text" else real_json[k]) for k in real_json
        }
        doc_body_diff = ZendeskDocument.deserialize_from_internal_json(body_json)
        hash_body_diff = ZendeskDocument.generate_opensearch_internal_id(doc_body_diff)

        # All of the above hashes should be different, except the base hash
        # should be identical to the hash that differs by jeeves_uid:
        self.assertEqual(hash_base, hash_uid_diff)
        self.assertNotEqual(hash_base, hash_user_diff)
        self.assertNotEqual(hash_base, hash_body_diff)
        self.assertNotEqual(hash_uid_diff, hash_user_diff)
        self.assertNotEqual(hash_uid_diff, hash_body_diff)
        self.assertNotEqual(hash_user_diff, hash_body_diff)

    @patch(
        "jeeves.model.zendesk_document.ZendeskDocument._get_channel_and_email",
        Mock(return_value=("somerandomperson@hotmail.com", "email")),
    )
    @patch(
        "jeeves.model.zendesk_document.ZendeskDocument._get_experiment_conditions",
        Mock(return_value={}),
    )
    def test_deserialize_document_from_external(self):
        real_json = {
            "url": "https://duolingotest.zendesk.com/api/v2/tickets/10379697.json",
            "id": 10379697,
            "external_id": None,
            "via": {"channel": "api", "source": {"from": {}, "to": {}, "rel": None}},
            "created_at": "2024-12-15T14:44:40Z",
            "updated_at": "2024-12-15T15:10:06Z",
            "generated_timestamp": 1734275407,
            "type": None,
            "subject": "Cancel Super Duolingo",
            "raw_subject": "Cancel Super Duolingo",
            "description": "I am trying to cancel a free trial of Super Duolingo but each time I click through to Google Play it is saying that it does not recognise my account. I do not want to be charged money to my account when my free trial ends on Monday. Thanks.\n\n-------------------\r\nApp information:\r\n\r\nApp version: 1.246.5\r\nApp version hash: 7ab8eaa265d7f89f204c3b465460e592a18c8e57\r\nBrowser: Samsung Internet for Android 27.0\r\nOS: Android 10\r\nPlatform: mobile\r\nScreen: 360x706, DPR 3\r\nLanguages: undefined<-undefined\r\nUsername: undefined\r\nUser ID: undefined\r\nCourse: undefined\r\n\r\n-------------------\r\nSession information:\r\n\r\nFullStory session: unavailable\r\nURL: https://www.duolingo.com/help/support-request\r\nPreview URL: unavailable\r\n\r\n",
            "priority": None,
            "status": "open",
            "recipient": "somerandomperson@hotmail.com",
            "requester_id": 32731705654029,
            "submitter_id": 32731705654029,
            "assignee_id": 420183991792,
            "organization_id": None,
            "group_id": 28162243,
            "collaborator_ids": [],
            "follower_ids": [],
            "email_cc_ids": [],
            "forum_topic_id": None,
            "problem_id": None,
            "has_incidents": False,
            "is_public": True,
            "due_at": None,
            "tags": [
                "decagon",
                "decagon_escalation",
                "device_type__android",
                "duolingo_diagnostics_processed",
                "purchase_issue",
                "super_subscription_cancellation_request",
            ],
            "custom_fields": [
                {"id": 24948326, "value": "MUSIC_MT"},
                {"id": 22786014, "value": "purchase_issue"},
                {"id": 360004381071, "value": "device_type__android"},
                {"id": 360000031963, "value": "super_subscription_cancellation_request"},
                {"id": 27158958044557, "value": False},
                {"id": 27158916626573, "value": False},
                {"id": 27880257195277, "value": False},
                {"id": 27880273765517, "value": False},
                {"id": 29458785008525, "value": True},
                {"id": 29458826283661, "value": "Annual Super Individual"},
                {"id": 29458857716365, "value": "Google"},
                {"id": 29464304148365, "value": "Simon910104"},
                {"id": 29697488891661, "value": False},
                {"id": 360005994332, "value": False},
                {"id": 360013072272, "value": "MUSIC_MT"},
                {"id": 360013072292, "value": "en"},
                {"id": 360013111891, "value": "MUSIC_MT"},
            ],
            "satisfaction_rating": {"score": "unoffered"},
            "sharing_agreement_ids": [],
            "custom_status_id": 5577691,
            "encoded_id": "L2JD34-69J3Y",
            "followup_ids": [],
            "ticket_form_id": 360000075891,
            "brand_id": 360001086811,
            "allow_channelback": False,
            "allow_attachments": True,
            "from_messaging_channel": False,
            # Attachments are not actually included in Zendesk response, they are added in zendesk_manager.py
            "attachments": [],
        }
        doc_base = ZendeskDocument.deserialize_from_external_json(real_json)

        self.assertEqual(doc_base.duolingo_metadata["app_information"]["app_version"], "1.246.5")  # type: ignore

    @patch(
        "jeeves.model.zendesk_document.ZendeskDocument._get_channel_and_email",
        Mock(return_value=("somerandomperson@hotmail.com", "email")),
    )
    @patch(
        "jeeves.model.zendesk_document.ZendeskDocument._get_experiment_conditions",
        Mock(return_value={}),
    )
    def test_deserialize_document_from_external_with_metadata_field(self):
        real_json = {
            "url": "https://duolingotest.zendesk.com/api/v2/tickets/10379697.json",
            "id": 10379697,
            "external_id": None,
            "via": {"channel": "api", "source": {"from": {}, "to": {}, "rel": None}},
            "created_at": "2024-12-15T14:44:40Z",
            "updated_at": "2024-12-15T15:10:06Z",
            "generated_timestamp": 1734275407,
            "type": None,
            "subject": "Cancel Super Duolingo",
            "raw_subject": "Cancel Super Duolingo",
            "description": "I am trying to cancel a free trial of Super Duolingo but each time I click through to Google Play it is saying that it does not recognise my account. I do not want to be charged money to my account when my free trial ends on Monday. Thanks.",
            "priority": None,
            "status": "open",
            "recipient": "somerandomperson@hotmail.com",
            "requester_id": 32731705654029,
            "submitter_id": 32731705654029,
            "assignee_id": 420183991792,
            "organization_id": None,
            "group_id": 28162243,
            "collaborator_ids": [],
            "follower_ids": [],
            "email_cc_ids": [],
            "forum_topic_id": None,
            "problem_id": None,
            "has_incidents": False,
            "is_public": True,
            "due_at": None,
            "tags": [
                "decagon",
                "decagon_escalation",
                "device_type__android",
                "duolingo_diagnostics_processed",
                "purchase_issue",
                "super_subscription_cancellation_request",
            ],
            "custom_fields": [
                {
                    "id": 32069071921677,
                    "value": "-------------------\r\nApp information:\r\n\r\nApp version: 1.246.5\r\nApp version hash: 7ab8eaa265d7f89f204c3b465460e592a18c8e57\r\nBrowser: Samsung Internet for Android 27.0\r\nOS: Android 10\r\nPlatform: mobile\r\nScreen: 360x706, DPR 3\r\nLanguages: undefined<-undefined\r\nUsername: undefined\r\nUser ID: undefined\r\nCourse: undefined\r\n\r\n-------------------\r\nSession information:\r\n\r\nFullStory session: unavailable\r\nURL: https://www.duolingo.com/help/support-request\r\nPreview URL: unavailable\r\n\r\n",
                }
            ],
            "satisfaction_rating": {"score": "unoffered"},
            "sharing_agreement_ids": [],
            "custom_status_id": 5577691,
            "encoded_id": "L2JD34-69J3Y",
            "followup_ids": [],
            "ticket_form_id": 360000075891,
            "brand_id": 360001086811,
            "allow_channelback": False,
            "allow_attachments": True,
            "from_messaging_channel": False,
            # Attachments are not actually included in Zendesk response, they are added in zendesk_manager.py
            "attachments": [],
        }
        doc_base = ZendeskDocument.deserialize_from_external_json(real_json)

        self.assertEqual(doc_base.duolingo_metadata["app_information"]["app_version"], "1.246.5")  # type: ignore

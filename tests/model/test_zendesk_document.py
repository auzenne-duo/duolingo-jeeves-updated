import unittest


from jeeves.model.zendesk_document import ZendeskDocument


class Test(unittest.TestCase):
    def test_generate_elasticsearch_internal_id(self):

        real_json = {
            "data_source": "Zendesk",
            "document_id": "2605487",
            "jeeves_uid": "Zendesk_2605487",
            "date_time": "2021-02-18T21:46:30+00:00",
            "header_text": "Feedback",
            "body_text": "During this session since updating Duolingo the lessons for audio will not work\n\nRegards\n\n\n\nUsername: Christine692827\nLearning language: es\nCourse: DUOLINGO_ES_EN\nuFlags:\nApp version: 6.104.0.5\nDevice model: iPad\nRaw Platform: iPad11,1\nPlatform: iPad mini 5th Gen (WiFi)\nOS version: 14.4\nUI language: en-gb\n\n\n\n\nSent from my iPad\nlogs.txt",
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
        hash_base = ZendeskDocument.generate_elasticsearch_internal_id(doc_base)

        # Change jeeves_uid
        uid_json = {k: ("Zendesk_00000" if k == "jeeves_uid" else real_json[k]) for k in real_json}
        doc_uid_diff = ZendeskDocument.deserialize_from_internal_json(uid_json)
        hash_uid_diff = ZendeskDocument.generate_elasticsearch_internal_id(doc_uid_diff)

        # Change requester_id
        user_json = {k: ("some_user" if k == "requester_id" else real_json[k]) for k in real_json}
        doc_user_diff = ZendeskDocument.deserialize_from_internal_json(user_json)
        hash_user_diff = ZendeskDocument.generate_elasticsearch_internal_id(doc_user_diff)

        # Change body_text
        body_json = {
            k: ("The quick brown fox" if k == "body_text" else real_json[k]) for k in real_json
        }
        doc_body_diff = ZendeskDocument.deserialize_from_internal_json(body_json)
        hash_body_diff = ZendeskDocument.generate_elasticsearch_internal_id(doc_body_diff)

        # All of the above hashes should be different, except the base hash
        # should be identical to the hash that differs by jeeves_uid:
        self.assertEqual(hash_base, hash_uid_diff)
        self.assertNotEqual(hash_base, hash_user_diff)
        self.assertNotEqual(hash_base, hash_body_diff)
        self.assertNotEqual(hash_uid_diff, hash_user_diff)
        self.assertNotEqual(hash_uid_diff, hash_body_diff)
        self.assertNotEqual(hash_user_diff, hash_body_diff)

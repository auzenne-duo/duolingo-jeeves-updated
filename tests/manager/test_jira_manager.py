import unittest


from jeeves.manager.jira_manager import JiraManager
from jeeves.model.jira_document import JiraDocument


class Test(unittest.TestCase):
    def test_parse_parent_description(self):
        body_text_in = "APP VERSIONS:\nNOT PRESENT: 2\n6.117.0.1: 1\n\n\nPLATFORMS:\nNOT PRESENT: 2\niOS: 1\n\n\nCOURSES:\nNOT PRESENT: 2\nDUOLINGO_FR_EN: 1\n\n\nINTERFACE LANGUAGES:\nNOT PRESENT: 2\nen: 1\n\n\nOPERATING SYSTEMS:\nNOT PRESENT: 2\niOS 14.4.1: 1\n\n\nAREAS:\n\n"
        desired_output = {
            "app_version": {"NOT PRESENT": 2, "6.117.0.1": 1},
            "platform": {"NOT PRESENT": 2, "iOS": 1},
            "course": {"NOT PRESENT": 2, "DUOLINGO_FR_EN": 1},
            "ui_language": {"NOT PRESENT": 2, "en": 1},
            "os_version": {"NOT PRESENT": 2, "iOS 14.4.1": 1},
            "components": {},
        }
        actual_output = JiraManager.parse_parent_description(body_text_in)
        self.assertEqual(actual_output, desired_output)

    def test_generate_parent_body_text_from_data(self):
        # Basically the reverse of parse_parent_description
        data_in = {
            "app_version": {"NOT PRESENT": 2, "6.117.0.1": 1},
            "platform": {"NOT PRESENT": 2, "iOS": 1},
            "course": {"NOT PRESENT": 2, "DUOLINGO_FR_EN": 1},
            "ui_language": {"NOT PRESENT": 2, "en": 1},
            "os_version": {"NOT PRESENT": 2, "iOS 14.4.1": 1},
            "components": {},
        }
        desired_output = {
            "type": "doc",
            "version": 1,
            "content": [
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "APP VERSIONS:\nNOT PRESENT: 2\n6.117.0.1: 1\n"}
                    ],
                },
                {
                    "type": "paragraph",
                    "content": [{"type": "text", "text": "PLATFORMS:\nNOT PRESENT: 2\niOS: 1\n"}],
                },
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "COURSES:\nNOT PRESENT: 2\nDUOLINGO_FR_EN: 1\n"}
                    ],
                },
                {
                    "type": "paragraph",
                    "content": [
                        {"type": "text", "text": "INTERFACE LANGUAGES:\nNOT PRESENT: 2\nen: 1\n"}
                    ],
                },
                {
                    "type": "paragraph",
                    "content": [
                        {
                            "type": "text",
                            "text": "OPERATING SYSTEMS:\nNOT PRESENT: 2\niOS 14.4.1: 1\n",
                        }
                    ],
                },
                {"type": "paragraph", "content": [{"type": "text", "text": "AREAS:\n"}]},
            ],
        }
        actual_output = JiraManager.generate_parent_body_text_from_data(data_in)
        self.assertEqual(actual_output, desired_output)

    def test_update_parent_from_child(self):
        parent_data = {
            "app_version": {"NOT PRESENT": 2},
            "platform": {"NOT PRESENT": 2},
            "course": {"NOT PRESENT": 2},
            "ui_language": {"NOT PRESENT": 2},
            "os_version": {"NOT PRESENT": 2},
            "components": {},
        }
        child_issue_json = {
            "data_source": "JIRA",
            "document_id": "121715",
            "jeeves_uid": "JIRA_121715",
            "date_time": "2021-05-21T22:33:08+00:00",
            "header_text": "Copy of a real issue",
            "body_text": "See screenshot\nReported with shake-to-report",
            "language": "en",
            "links": [],
            "shake_to_report_category": "INTERNAL",
            "attachments": [],
            "duolingo_metadata": {
                "system_information": {
                    "app_version": "6.117.0.1",
                    "ios_version": "14.4.1",
                    "device_model": "iPhone",
                    "platform": "iPhone 7 Plus (Model A1784)",
                    "raw_platform": "iPhone9,4",
                    "ui_language": "en-us",
                    "screen": "414 W x 736 H",
                    "environment": "Test Flight (com.duolingo.DuolingoMobile)",
                    "jail_broken": "false",
                },
                "user_information": {
                    "id": "5335127",
                    "email": "maggie@duolingo.com",
                    "username": "DarthDuo",
                    "current_course": "DUOLINGO_FR_EN (French <- English)",
                    "time_zone": "America/New_York",
                    "session_information": "",
                    "session_id": "ApLfoR9gpazimM8r",
                    "session_type": "global_practice",
                    "session_bundle_id": "en_fr_(null)_practice",
                    "skill_tree_id": "9802c10e6de5be98af969b9578768f56",
                    "level_number": "0",
                    "lesson_number": "0",
                    "skill_id": "none",
                    "challenge_id": "none",
                    "challenge_type": "none",
                },
                "report_method": "screenshot",
                "view_controller_name": "UIAlertController",
                "fullstory": {
                    "session_url": "https://app.fullstory.com/ui/QZHJ3/session/5627933872365568:5680006861037568:1620937663685"
                },
                "raw": "—\n\nSystem Information:\n\n- app version: 6.117.0.1\n- iOS version: 14.4.1\n- device model: iPhone\n- platform: iPhone 7 Plus (Model A1784)\n- raw platform: iPhone9,4\n- ui language: en-us\n- screen: 414 W x 736 H\n- environment: Test Flight (com.duolingo.DuolingoMobile)\n- jail broken: false\n\nUser Information:\n\n- id: 5335127\n- email: maggie@duolingo.com\n- username: DarthDuo\n- current course: DUOLINGO_FR_EN (French <- English)\n- time zone: America/New_York\n\nSession Information:\n\n- session id: ApLfoR9gpazimM8r\n- session type: global_practice\n- session bundle id: en_fr_(null)_practice\n- skill tree id: 9802c10e6de5be98af969b9578768f56\n- level number: 0\n- lesson number: 0\n- skill id: none\n- challenge id: none\n- challenge type: none\n\nReport method:\nscreenshot\n\nView Controller Name:\nUIAlertController\n\nFullStory:\n\n- session url: https://app.fullstory.com/ui/QZHJ3/session/5627933872365568:5680006861037568:1620937663685\n\n—",
            },
            "app_version": "6.117.0.1",
            "course": "DUOLINGO_FR_EN",
            "fullstory_url": "https://app.fullstory.com/ui/QZHJ3/session/5627933872365568:5680006861037568:1620937663685",
            "os_version": "iOS 14.4.1",
            "platform": "iOS",
            "screen_size": "414x736",
            "screen_content": "UIAlertController",
            "ui_language": "en",
            "username": "DarthDuo",
            "issue_key": "BUGZ-7",
            "issue_links": [
                {
                    "id": "112719",
                    "self": "https://duolingo.atlassian.net/rest/api/3/issueLink/112719",
                    "type": {
                        "id": "10002",
                        "name": "Duplicate",
                        "inward": "is duplicated by",
                        "outward": "duplicates",
                        "self": "https://duolingo.atlassian.net/rest/api/3/issueLinkType/10002",
                    },
                    "outwardIssue": {
                        "id": "121635",
                        "key": "BUGZ-3",
                        "self": "https://duolingo.atlassian.net/rest/api/3/issue/121635",
                        "fields": {
                            "summary": "Bug 2?",
                            "status": {
                                "self": "https://duolingo.atlassian.net/rest/api/3/status/10400",
                                "description": "This issue needs more information before work can continue.",
                                "iconUrl": "https://duolingo.atlassian.net/images/icons/statuses/generic.png",
                                "name": "Unconfirmed",
                                "id": "10400",
                                "statusCategory": {
                                    "self": "https://duolingo.atlassian.net/rest/api/3/statuscategory/2",
                                    "id": 2,
                                    "key": "new",
                                    "colorName": "blue-gray",
                                    "name": "To Do",
                                },
                            },
                            "priority": {
                                "self": "https://duolingo.atlassian.net/rest/api/3/priority/10000",
                                "iconUrl": "https://files.slack.com/files-pri/T0299K8L0-F44H8HJG4/noun_670399_cc.svg?pub_secret=e26951db42",
                                "name": "Unprioritized",
                                "id": "10000",
                            },
                            "issuetype": {
                                "self": "https://duolingo.atlassian.net/rest/api/3/issuetype/10003",
                                "id": "10003",
                                "description": "",
                                "iconUrl": "https://duolingo.atlassian.net/secure/viewavatar?size=medium&avatarId=10303&avatarType=issuetype",
                                "name": "Bug",
                                "subtask": False,
                                "avatarId": 10303,
                                "hierarchyLevel": 0,
                            },
                        },
                    },
                },
                {
                    "id": "112720",
                    "self": "https://duolingo.atlassian.net/rest/api/3/issueLink/112720",
                    "type": {
                        "id": "10002",
                        "name": "Duplicate",
                        "inward": "is duplicated by",
                        "outward": "duplicates",
                        "self": "https://duolingo.atlassian.net/rest/api/3/issueLinkType/10002",
                    },
                    "outwardIssue": {
                        "id": "121636",
                        "key": "BUGZ-4",
                        "self": "https://duolingo.atlassian.net/rest/api/3/issue/121636",
                        "fields": {
                            "summary": "Bug 3??",
                            "status": {
                                "self": "https://duolingo.atlassian.net/rest/api/3/status/10400",
                                "description": "This issue needs more information before work can continue.",
                                "iconUrl": "https://duolingo.atlassian.net/images/icons/statuses/generic.png",
                                "name": "Unconfirmed",
                                "id": "10400",
                                "statusCategory": {
                                    "self": "https://duolingo.atlassian.net/rest/api/3/statuscategory/2",
                                    "id": 2,
                                    "key": "new",
                                    "colorName": "blue-gray",
                                    "name": "To Do",
                                },
                            },
                            "priority": {
                                "self": "https://duolingo.atlassian.net/rest/api/3/priority/10000",
                                "iconUrl": "https://files.slack.com/files-pri/T0299K8L0-F44H8HJG4/noun_670399_cc.svg?pub_secret=e26951db42",
                                "name": "Unprioritized",
                                "id": "10000",
                            },
                            "issuetype": {
                                "self": "https://duolingo.atlassian.net/rest/api/3/issuetype/10003",
                                "id": "10003",
                                "description": "",
                                "iconUrl": "https://duolingo.atlassian.net/secure/viewavatar?size=medium&avatarId=10303&avatarType=issuetype",
                                "name": "Bug",
                                "subtask": False,
                                "avatarId": 10303,
                                "hierarchyLevel": 0,
                            },
                        },
                    },
                },
                {
                    "id": "112718",
                    "self": "https://duolingo.atlassian.net/rest/api/3/issueLink/112718",
                    "type": {
                        "id": "10002",
                        "name": "Duplicate",
                        "inward": "is duplicated by",
                        "outward": "duplicates",
                        "self": "https://duolingo.atlassian.net/rest/api/3/issueLinkType/10002",
                    },
                    "outwardIssue": {
                        "id": "121729",
                        "key": "BUGZ-16",
                        "self": "https://duolingo.atlassian.net/rest/api/3/issue/121729",
                        "fields": {
                            "summary": "PARENT FOR [Bug 2?|Bug 3??]",
                            "status": {
                                "self": "https://duolingo.atlassian.net/rest/api/3/status/10400",
                                "description": "This issue needs more information before work can continue.",
                                "iconUrl": "https://duolingo.atlassian.net/images/icons/statuses/generic.png",
                                "name": "Unconfirmed",
                                "id": "10400",
                                "statusCategory": {
                                    "self": "https://duolingo.atlassian.net/rest/api/3/statuscategory/2",
                                    "id": 2,
                                    "key": "new",
                                    "colorName": "blue-gray",
                                    "name": "To Do",
                                },
                            },
                            "priority": {
                                "self": "https://duolingo.atlassian.net/rest/api/3/priority/10000",
                                "iconUrl": "https://files.slack.com/files-pri/T0299K8L0-F44H8HJG4/noun_670399_cc.svg?pub_secret=e26951db42",
                                "name": "Unprioritized",
                                "id": "10000",
                            },
                            "issuetype": {
                                "self": "https://duolingo.atlassian.net/rest/api/3/issuetype/10003",
                                "id": "10003",
                                "description": "",
                                "iconUrl": "https://duolingo.atlassian.net/secure/viewavatar?size=medium&avatarId=10303&avatarType=issuetype",
                                "name": "Bug",
                                "subtask": False,
                                "avatarId": 10303,
                                "hierarchyLevel": 0,
                            },
                        },
                    },
                },
            ],
            "issue_type": "Bug",
            "project": "BUGZ",
            "linked_duplicate_keys": ["BUGZ-3", "BUGZ-4", "BUGZ-16"],
            "creation_date": "2021-05-21T22:33:08+00:00",
            "updated_date": "2021-05-22T16:13:01+00:00",
            "resolution_date": None,
            "status": "To Do",
            "resolution": "",
            "components": ["Circle Area", "Circle Perimeter"],
            "features": [],
            "priority": "Unprioritized",
            "reporter": "Peter Pearson",
            "assignee": "UNASSIGNED",
            "comments": [],
            "labels": [],
            "embedding_vector": [],
        }
        child_document = JiraDocument.deserialize_from_internal_json(child_issue_json)
        desired_output = {
            "app_version": {"NOT PRESENT": 2, "6.117.0.1": 1},
            "platform": {"NOT PRESENT": 2, "iOS": 1},
            "course": {"NOT PRESENT": 2, "DUOLINGO_FR_EN": 1},
            "ui_language": {"NOT PRESENT": 2, "en": 1},
            "os_version": {"NOT PRESENT": 2, "iOS 14.4.1": 1},
            "components": {"Circle Area": 1},
        }
        actual_output = JiraManager.update_parent_data_from_child(parent_data, child_document)
        self.assertEqual(actual_output, desired_output)
